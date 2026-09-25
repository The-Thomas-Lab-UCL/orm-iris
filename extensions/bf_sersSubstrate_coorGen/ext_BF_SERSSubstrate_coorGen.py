import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'..\library')
    EXT_DIR = os.path.abspath(r'..\extensions')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
    sys.path.insert(0, os.path.dirname(EXT_DIR))

import threading
import multiprocessing.pool as mpp

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import PySide6.QtWidgets as qw
from PySide6.QtCore import Qt, Signal, Slot, QObject, QThread

from typing import Callable, Iterable

from extensions.extension_template import Extension_MainWindow
from extensions.extension_intermediary import Ext_DataIntermediary as Intermediary

from iris.data.measurement_coordinates import MeaCoor_mm
from iris.data.measurement_coordinates import List_MeaCoor_Hub

from extensions.bf_sersSubstrate_coorGen.bf_sersSubstrate_coorGen_ui import Ui_bf_sresSubstrate_coorGen

from extensions.bf_sersSubstrate_coorGen.masking.fitting import Param_Smoothen_Boundary
from extensions.bf_sersSubstrate_coorGen.masking.basic_image_processing import (
    Params_Centre_Estimation, Params_Edge_Detection,
)
from extensions.bf_sersSubstrate_coorGen.masking.pipeline import PipelineOutput, PipelineParams, run_pipeline


# ── Data classes ──────────────────────────────────────────────────────────────

class ProcessResult:
    """
    A finished pipeline run, ready to plot and to save to the coordinate hub.

    Holds only the plain data returned by the pool worker — notably *not* the
    MeaImg_Unit, so keeping several results around no longer pins a full set of
    raw tile images in memory per result.
    """
    def __init__(self, out: PipelineOutput):
        self._out = out
        self._coor = MeaCoor_mm(
            mappingUnit_name=out.unit_name,
            mapping_coordinates=out.scan_coordinates,
        )

    def get_name(self) -> str:
        return self._out.unit_name

    def get_coor(self) -> MeaCoor_mm:
        return self._coor

    def get_output(self) -> PipelineOutput:
        return self._out


class List_ProcessResult(list):
    def __init__(self):
        super().__init__()
        self._callbacks: list[Callable] = []

    def add_observer(self, cb: Callable):
        if callable(cb) and cb not in self._callbacks:
            self._callbacks.append(cb)

    def remove_observer(self, cb: Callable):
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    def _notify(self):
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                print(f'List_ProcessResult observer error: {e}')

    def append(self, item: ProcessResult) -> None:
        super().append(item)
        self._notify()

    def extend(self, items: Iterable[ProcessResult]) -> None:  # type: ignore[override]
        super().extend(items)
        self._notify()

    def remove(self, item: ProcessResult) -> None:
        super().remove(item)
        self._notify()

    def replace_or_append(self, item: ProcessResult) -> None:
        for i, r in enumerate(self):
            if r.get_name() == item.get_name():
                self[i] = item
                self._notify()
                return
        self.append(item)


# ── Worker: run the full pipeline for a list of MeaImg_Units ─────────────────

class _ProcessWorker(QObject):
    """
    Feeds units to the app-wide process pool, keeping one task in flight per
    worker so every core stays busy.

    This object lives on a QThread, but the QThread is only a waiting room: the
    actual work runs in pool worker processes and `AsyncResult.get()` blocks on
    a pipe read, which releases the GIL. Running the pipeline in the QThread
    itself would instead share the GIL and a core with the GUI, which on a
    full-size stitched image leaves the event loop visibly stuttering.
    """
    sig_result   = Signal(object)        # emits ProcessResult
    sig_error    = Signal(str, str)      # (unit_name, error_message)
    sig_progress = Signal(str, int, int) # (unit_name, index, total)
    sig_done     = Signal(bool)          # was_cancelled

    def __init__(self, pool: mpp.Pool | None):
        super().__init__()
        self._pool = pool
        self._cancel = threading.Event()

    def request_cancel(self):
        """
        Ask to stop dispatching further units.

        A pool task cannot be interrupted once it has started, so units
        already in flight still run to completion and their results are
        still emitted; only units not yet dispatched are skipped.
        """
        self._cancel.set()

    @Slot(list, object)
    def submit(self, units: list, params: PipelineParams):
        self._cancel.clear()
        total = len(units)

        if self._pool is None:
            # No shared pool (e.g. the extension run standalone). Still
            # correct, but the GUI will stutter while this runs, and there's
            # no pool to parallelise across.
            for i, unit in enumerate(units):
                if self._cancel.is_set():
                    break
                name = unit.get_IdName()[1]
                self.sig_progress.emit(name, i, total)
                try:
                    out = run_pipeline(unit, params)
                    self.sig_result.emit(ProcessResult(out))
                except Exception as e:
                    self.sig_error.emit(name, str(e))
            self.sig_done.emit(self._cancel.is_set())
            return

        # Dispatch up to `window` units at once (roughly one per CPU core) so
        # the pool's workers run in parallel, then top the window back up as
        # each one finishes. Submitting every unit up front instead would
        # pickle every unit's raw image to the pool immediately, spiking
        # memory on a large batch.
        pool = self._pool
        window = max(1, os.cpu_count() or 1)
        next_index = 0
        inflight: list[tuple[str, mpp.AsyncResult]] = []

        def _dispatch_next():
            nonlocal next_index
            unit = units[next_index]
            name = unit.get_IdName()[1]
            future = pool.apply_async(run_pipeline, (unit, params))
            inflight.append((name, future))
            self.sig_progress.emit(name, next_index, total)
            next_index += 1

        while next_index < len(units) and len(inflight) < window:
            _dispatch_next()

        while inflight:
            name, future = inflight.pop(0)
            try:
                out = future.get()
                self.sig_result.emit(ProcessResult(out))
            except Exception as e:
                self.sig_error.emit(name, str(e))
            if not self._cancel.is_set() and next_index < len(units):
                _dispatch_next()

        self.sig_done.emit(self._cancel.is_set())


# ── Worker: render full pipeline collage for a single ProcessResult ───────────

class _PlotWorker(QObject):
    """
    Builds the diagnostic collage off the GUI thread.

    Only artist objects are created here (a bare Figure, never pyplot); the
    actual rasterisation happens on the main thread when the canvas draws.
    """
    sig_done = Signal(object, object)  # (Figure, result_name)

    def __init__(self, result: ProcessResult):
        super().__init__()
        self._result = result

    @Slot()
    def run(self):
        r = self._result.get_output()

        fig = Figure(figsize=(12, 16))
        fig.set_tight_layout(True) # pyright: ignore[reportAttributeAccessIssue] ; set_tight_layout is valid for Figure
        ax = fig.subplot_mosaic(
            [['rgb',     's_ch'  ],
             ['centre',  'sobel' ],
             ['ransac',  'smooth'],
             ['overlay', 'mea'  ]],
        )

        fs = 7  # common font size for titles / labels

        # The diagnostic images come back downsampled for display, while every
        # coordinate below is in full-resolution pixels. Drawing each image
        # with the full-resolution extent puts the two back on the same axes.
        img_h, img_w = r.img_shape_full
        extent = (-0.5, img_w - 0.5, img_h - 0.5, -0.5)

        # ── Affine transform: stage mm → image pixel ───────────────────────
        # Derived from the boundary (known in both coordinate systems).
        # Handles rotation + scale without needing to store coor_min_mm.
        N = len(r.boundary_px_x)
        src = np.column_stack([r.boundary_stage_mm, np.ones(N)])
        Ax, _, _, _ = np.linalg.lstsq(src, r.boundary_px_x, rcond=None)
        Ay, _, _, _ = np.linalg.lstsq(src, r.boundary_px_y, rcond=None)

        def stg2px(pts_mm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            h = np.column_stack([pts_mm, np.ones(len(pts_mm))])
            return h @ Ax, h @ Ay

        exp_px_x, exp_px_y = stg2px(r.boundary_stage_mm_expanded)

        # ── Row 0 ──────────────────────────────────────────────────────────
        ax['rgb'].imshow(r.arr, extent=extent)
        ax['rgb'].set_title('RGB input', fontsize=fs)
        ax['rgb'].axis('off')

        ch_label = r.hsv_channels if len(r.hsv_channels) == 1 else f'{r.hsv_channels} → PCA'
        ax['s_ch'].imshow(r.S, cmap='gray', extent=extent)
        ax['s_ch'].set_title(ch_label, fontsize=fs)
        ax['s_ch'].axis('off')

        ax['centre'].imshow(r.S_blurred_centre, cmap='gray', extent=extent)
        ax['centre'].scatter(r.cx_est, r.cy_est, s=60, c='red', marker='x', zorder=5)
        ax['centre'].set_title(f'Centre est. ({r.cx_est:.0f}, {r.cy_est:.0f}) px', fontsize=fs)
        ax['centre'].axis('off')

        # ── Row 1 ──────────────────────────────────────────────────────────
        ax['sobel'].imshow(r.S_sobel_viz, cmap='gray', extent=extent)
        ax['sobel'].scatter(r.ellipse_sobel.x, r.ellipse_sobel.y,
                            s=2, c='red', marker='x', label='Edge samples')
        ax['sobel'].set_title(f'Sobel edges  ({len(r.ellipse_sobel.x)} samples)', fontsize=fs)
        ax['sobel'].axis('off')
        ax['sobel'].legend(fontsize=fs - 1, markerscale=2)

        f = r.ellipse_fit
        t = np.linspace(0, 2 * np.pi, 200)
        ex = f.xc + f.a * np.cos(t) * np.cos(f.theta) - f.b * np.sin(t) * np.sin(f.theta)
        ey = f.yc + f.a * np.cos(t) * np.sin(f.theta) + f.b * np.sin(t) * np.cos(f.theta)
        ax['ransac'].imshow(r.S, cmap='gray', extent=extent)
        ax['ransac'].scatter(r.ellipse_sobel.x, r.ellipse_sobel.y,
                             s=1, c='blue', alpha=0.4, label='Edge samples')
        ax['ransac'].plot(ex, ey, 'g-', lw=1.5, label='RANSAC fit')
        ax['ransac'].scatter(f.xc, f.yc, s=40, c='yellow', zorder=5)
        ax['ransac'].set_title(
            f'RANSAC  Ø{f.major_d:.0f}×{f.minor_d:.0f} px  circ={f.circularity:.3f}',
            fontsize=fs)
        ax['ransac'].axis('off')
        ax['ransac'].legend(fontsize=fs - 1)

        raw_r, raw_theta = r.ellipse_sobel.get_polar(
            centre_x=r.ellipse_fit.xc, centre_y=r.ellipse_fit.yc)
        sort_raw = np.argsort(np.degrees(raw_theta))
        ax['smooth'].plot(np.degrees(raw_theta)[sort_raw] + 180,
                          raw_r[sort_raw], 'b-', lw=0.8, label='Raw')
        ax['smooth'].plot(np.degrees(r.ellipse_clean.theta) + 180,
                          r.ellipse_clean.r, 'r-', lw=0.8, label='Cleaned')
        ax['smooth'].plot(np.degrees(r.ellipse_smooth.theta) + 180,
                          r.ellipse_smooth.r, 'g-', lw=1.2, label='Smoothed')
        ax['smooth'].set_title('Boundary radius vs angle', fontsize=fs)
        ax['smooth'].set_xlabel('Angle (°)', fontsize=fs)
        ax['smooth'].set_ylabel('Radius (px)', fontsize=fs)
        ax['smooth'].tick_params(labelsize=fs - 1)
        ax['smooth'].legend(fontsize=fs - 1)

        # ── Row 2 — image overlay (spans 2 cols) + measurement frame ───────
        ax['overlay'].imshow(r.arr, extent=extent)
        ax['overlay'].plot(r.boundary_px_x, r.boundary_px_y,
                           'r-', lw=1.5, label='Detected boundary')
        ax['overlay'].plot(exp_px_x, exp_px_y,
                           'r--', lw=1, label=f'+{r.expansion_mm * 1e3:.0f} µm expansion')
        ax['overlay'].scatter(f.xc, f.yc, s=60, c='yellow', zorder=5, label='Centre')
        # The expansion may run past the edge of the image; grid points out
        # there are dropped, so pin the view to the image itself to make the
        # clipping visible rather than zooming out to fit the dashed outline.
        ax['overlay'].set_xlim(extent[0], extent[1])
        ax['overlay'].set_ylim(extent[2], extent[3])
        clipped = f'  |  {r.n_clipped_by_image} clipped' if r.n_clipped_by_image else ''
        ax['overlay'].set_title(
            f'Scan grid overlay  |  '
            f'step={r.step_size_x_mm * 1e3:.0f}×{r.step_size_y_mm * 1e3:.0f} µm  |  '
            f'N={len(r.scan_coordinates)}{clipped}',
            fontsize=fs)
        ax['overlay'].axis('off')

        sc_arr = np.array(r.scan_coordinates)
        ax['mea'].scatter(sc_arr[:, 0], sc_arr[:, 1],
                          s=2, c='darkorange', alpha=0.6, label='Scan pts (mea)')
        ax['mea'].set_aspect('equal')
        ax['mea'].set_xlabel('X mea [mm]', fontsize=fs)
        ax['mea'].set_ylabel('Y mea [mm]', fontsize=fs)
        ax['mea'].tick_params(labelsize=fs - 1)
        ax['mea'].set_title('Measurement frame (laser position)', fontsize=fs)

        self.sig_done.emit(fig, self._result.get_name())


# ── Main extension window ─────────────────────────────────────────────────────

class Ext_BF_SERSSubstrate_coorGen(Ui_bf_sresSubstrate_coorGen, Extension_MainWindow):

    _sig_update_img_list = Signal()
    _sig_submit_work     = Signal(list, object)

    def __init__(self, parent, intermediary: Intermediary):
        super().__init__(parent, intermediary)
        self.setupUi(self)
        self.setWindowTitle("BF SERS Substrate Coordinate Generator")

        self._imghub = intermediary.get_datahub_image_gui().get_ImageMeasurement_Hub()
        self._coorhub: List_MeaCoor_Hub = intermediary.get_coorhub()

        self._process_results = List_ProcessResult()
        self._process_results.add_observer(self._sync_result_tree)

        # Permanent background processor — created once, never torn down.
        # The QThread only marshals work to the app-wide process pool, so the
        # pipeline never runs on the GUI's interpreter.
        self._process_worker = _ProcessWorker(intermediary.get_processor())
        self._process_thread = QThread(self)
        self._process_worker.moveToThread(self._process_thread)
        self._process_worker.sig_result.connect(self._on_process_result)
        self._process_worker.sig_error.connect(self._on_process_error)
        self._process_worker.sig_progress.connect(self._on_process_progress)
        self._process_worker.sig_done.connect(self._on_process_done)
        self._sig_submit_work.connect(self._process_worker.submit)
        self._process_thread.start()
        self._processing = False

        self._plot_thread: QThread | None = None
        self._plot_worker: _PlotWorker | None = None
        self._pending_plot_result: ProcessResult | None = None

        self._init_params_widgets()
        self._init_progress_widgets()
        self._init_result_plot()
        self._init_result_buttons()
        self._init_signals()

        self._imghub.add_observer(self._sig_update_img_list.emit)
        self._sig_update_img_list.connect(self._refresh_img_tree)
        self._refresh_img_tree()

    # ── closeEvent: minimise instead of destroy ────────────────────────────

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    # ── Image tree ─────────────────────────────────────────────────────────

    @Slot()
    def _refresh_img_tree(self):
        self.tree_img.clear()
        self.tree_img.setHeaderLabels(['Image unit'])
        for name in self._imghub.get_list_ImageUnit_names():
            qw.QTreeWidgetItem(self.tree_img, [name])

    # ── Parameter widgets (auto-generated) ────────────────────────────────

    def _init_params_widgets(self):
        lyt = self.lyt_params
        lyt.setFieldGrowthPolicy(qw.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        sp_expand = qw.QSizePolicy(qw.QSizePolicy.Policy.Expanding, qw.QSizePolicy.Policy.Fixed)

        def _add_spin(label: str, value: float, min_: float, max_: float,
                      decimals: int = 3, suffix: str = '') -> qw.QDoubleSpinBox:
            spin = qw.QDoubleSpinBox()
            spin.setRange(min_, max_)
            spin.setDecimals(decimals)
            spin.setValue(value)
            spin.setSizePolicy(sp_expand)
            if suffix:
                spin.setSuffix(suffix)
            lyt.addRow(label, spin)
            return spin

        def _add_ispin(label: str, value: int, min_: int, max_: int) -> qw.QSpinBox:
            spin = qw.QSpinBox()
            spin.setRange(min_, max_)
            spin.setValue(value)
            spin.setSizePolicy(sp_expand)
            lyt.addRow(label, spin)
            return spin

        lyt.addRow(_make_section_label('Image preprocessing'))
        self._combo_hsv_channels = qw.QComboBox()
        self._combo_hsv_channels.setSizePolicy(sp_expand)
        for opt in ['S', 'H', 'V', 'HS', 'HV', 'SV', 'HSV']:
            self._combo_hsv_channels.addItem(opt)
        lyt.addRow('HSV channels', self._combo_hsv_channels)

        lyt.addRow(_make_section_label('Centre estimation'))
        self._spin_ce_sigma      = _add_spin('Blur sigma [px]',   50,    1,  500, 1)
        self._spin_ce_percentile = _add_spin('Blob percentile',   70,    1,   99, 1, ' %')

        lyt.addRow(_make_section_label('Edge detection (Sobel)'))
        self._spin_ed_sigma      = _add_spin('Blur sigma [px]',    5,  0.1,   50, 1)
        self._spin_ed_thresh     = _add_spin('Sobel threshold',   0.2, 0.0,  1.0, 3)
        self._spin_ed_rmin       = _add_ispin('r_min [px]',       100,   0, 2000)
        self._spin_ed_rmax       = _add_ispin('r_max [px]',       300,   1, 5000)
        self._spin_ed_nbins      = _add_ispin('Angular bins',     720,  36, 3600)

        lyt.addRow(_make_section_label('RANSAC fit'))
        self._spin_ransac_thresh = _add_spin('Residual threshold [px]', 5, 0.1, 100, 1)
        self._spin_ransac_trials = _add_ispin('Max trials',             500,  10, 5000)

        lyt.addRow(_make_section_label('Boundary smoothing'))
        self._spin_sm_outlier    = _add_spin('Outlier threshold [px]', 40, 1, 500, 1)
        self._spin_sm_window     = _add_ispin('Savgol window',         11,  3, 101)
        self._spin_sm_poly       = _add_ispin('Savgol polyorder',       2,  1,   5)

        lyt.addRow(_make_section_label('Scan grid'))
        self._spin_step_x_um    = _add_spin('Step X [µm]',        50.0,     1.0,    10000.0,    1, ' µm')
        self._spin_step_y_um    = _add_spin('Step Y [µm]',        50.0,     1.0,    10000.0,    1, ' µm')
        self._spin_expansion_um = _add_spin('ROI expansion [µm]',  200.0,   0.0,    10000.0,    3, ' µm')

    def _init_progress_widgets(self):
        """
        A status line under the Process button, so a long run reads as 'busy'
        rather than 'hung'.
        """
        self._btn_process_label = self.btn_process.text()
        self._lbl_status = qw.QLabel('')
        self._lbl_status.setWordWrap(True)
        self._progress = qw.QProgressBar()
        self._progress.setTextVisible(False)
        self._progress.setVisible(False)
        self.lyt.addWidget(self._lbl_status)
        self.lyt.addWidget(self._progress)

    def _read_params(self) -> PipelineParams:
        return PipelineParams(
            params_centre=Params_Centre_Estimation(
                sigma=self._spin_ce_sigma.value(),
                percentile=self._spin_ce_percentile.value(),
            ),
            params_edge=Params_Edge_Detection(
                sigma=self._spin_ed_sigma.value(),
                sobel_threshold=self._spin_ed_thresh.value(),
                r_min=self._spin_ed_rmin.value(),
                r_max=self._spin_ed_rmax.value(),
                n_bins=self._spin_ed_nbins.value(),
            ),
            params_smooth=Param_Smoothen_Boundary(
                outlier_threshold_px=self._spin_sm_outlier.value(),
                savgol_window=self._spin_sm_window.value(),
                savgol_polyorder=self._spin_sm_poly.value(),
            ),
            ransac_threshold=self._spin_ransac_thresh.value(),
            ransac_trials=self._spin_ransac_trials.value(),
            step_size_x_mm=self._spin_step_x_um.value() / 1000.0,  # µm → mm
            step_size_y_mm=self._spin_step_y_um.value() / 1000.0,  # µm → mm
            expansion_mm=self._spin_expansion_um.value() / 1000.0,  # µm → mm
            hsv_channels=self._combo_hsv_channels.currentText(),
        )

    # ── Result tab: plot canvas + buttons ─────────────────────────────────

    def _init_result_plot(self):
        fig = Figure(figsize=(5, 5), tight_layout=True)
        self._result_ax = fig.add_subplot(111)
        self._result_ax.axis('off')
        self._result_canvas = FigureCanvas(fig)
        self.lyt_result.addWidget(self._result_canvas)

    def _init_result_buttons(self):
        self.tree_result.setHeaderLabels(['Result'])

    # ── Signal wiring ──────────────────────────────────────────────────────

    def _init_signals(self):
        self.btn_process.clicked.connect(self._on_process_clicked)
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        self.btn_saveall.clicked.connect(self._on_saveall_clicked)
        self.tree_result.itemSelectionChanged.connect(self._on_result_selection_changed)

    # ── Processing ─────────────────────────────────────────────────────────

    @Slot()
    def _on_process_clicked(self):
        # While a run is in flight the button doubles as Cancel
        if self._processing:
            self._process_worker.request_cancel()
            self.btn_process.setEnabled(False)
            self._lbl_status.setText('Cancelling after the current unit…')
            return

        selected_names = [item.text(0) for item in self.tree_img.selectedItems()]
        if not selected_names:
            qw.QMessageBox.information(self, 'No selection', 'Please select at least one image unit.')
            return

        units = [self._imghub.get_ImageMeasurementUnit(unit_name=n) for n in selected_names]
        params = self._read_params()

        self._processing = True
        self.btn_process.setText('Cancel processing')
        self._progress.setRange(0, len(units))
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._sig_submit_work.emit(units, params)

    @Slot(str, int, int)
    def _on_process_progress(self, unit_name: str, index: int, total: int):
        self._progress.setValue(index)
        self._lbl_status.setText(f'Processing {unit_name} ({index + 1}/{total})…')

    @Slot(object)
    def _on_process_result(self, result: ProcessResult):
        self._process_results.replace_or_append(result)

    @Slot(str, str)
    def _on_process_error(self, unit_name: str, msg: str):
        qw.QMessageBox.warning(self, f'Error processing {unit_name}', msg)

    @Slot(bool)
    def _on_process_done(self, cancelled: bool):
        self._processing = False
        self.btn_process.setText(self._btn_process_label)
        self.btn_process.setEnabled(True)
        self._progress.setVisible(False)
        self._lbl_status.setText('Cancelled.' if cancelled else '')
        if cancelled:
            return
        self.tabWidget.setCurrentWidget(self.tab_result)
        qw.QMessageBox.information(
            self, 'Processing complete',
            f'All units processed. {len(self._process_results)} result(s) ready in the Result tab.'
        )

    # ── Result tree sync ───────────────────────────────────────────────────

    def _sync_result_tree(self):
        self.tree_result.clear()
        for r in self._process_results:
            qw.QTreeWidgetItem(self.tree_result, [r.get_name()])

    # ── Result selection → overlay plot ───────────────────────────────────

    @Slot()
    def _on_result_selection_changed(self):
        items = self.tree_result.selectedItems()
        if not items:
            return
        name = items[0].text(0)
        result = next((r for r in self._process_results if r.get_name() == name), None)
        if result is None:
            return
        # Debounce: always set pending; only launch a new plot thread if none running
        self._pending_plot_result = result
        if self._plot_thread is None or not self._plot_thread.isRunning():
            self._start_plot_worker(result)

    def _start_plot_worker(self, result: ProcessResult):
        self._pending_plot_result = None
        worker = _PlotWorker(result)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.sig_done.connect(self._on_plot_done)
        worker.sig_done.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._plot_worker = worker
        self._plot_thread = thread
        thread.start()

    @Slot(object, object)
    def _on_plot_done(self, fig: Figure, _: str):
        old_fig = self._result_canvas.figure
        self._result_canvas.figure = fig
        fig.set_canvas(self._result_canvas)
        w, h = self._result_canvas.width(), self._result_canvas.height()
        if w > 0 and h > 0:
            fig.set_size_inches(w / fig.dpi, h / fig.dpi, forward=False)
        self._result_canvas.draw_idle()
        # The old figure was built with the bare OO API, so pyplot never knew
        # about it and plt.close() would not have released anything. Dropping
        # its artists is what actually frees the memory.
        old_fig.clear()

        self._plot_thread = None
        self._plot_worker = None

        # If a newer selection came in while we were rendering, render it now
        if self._pending_plot_result is not None:
            self._start_plot_worker(self._pending_plot_result)

    # ── Remove / Save ──────────────────────────────────────────────────────

    @Slot()
    def _on_remove_clicked(self):
        items = self.tree_result.selectedItems()
        if not items:
            return
        names = {item.text(0) for item in items}
        next_index = min(self.tree_result.indexOfTopLevelItem(item) for item in items)
        for r in [r for r in self._process_results if r.get_name() in names]:
            self._process_results.remove(r)

        count = self.tree_result.topLevelItemCount()
        if count:
            item = self.tree_result.topLevelItem(min(next_index, count - 1))
            if item is not None:
                self.tree_result.setCurrentItem(item)

    @Slot()
    def _on_saveall_clicked(self):
        if not self._process_results:
            qw.QMessageBox.information(self, 'Nothing to save', 'No results to save.')
            return
        errors = []
        saved = []
        for result in list(self._process_results):
            try:
                self._coorhub.append(result.get_coor())
                saved.append(result)
            except Exception as e:
                errors.append(f'{result.get_name()}: {e}')
        for r in saved:
            self._process_results.remove(r)
        if errors:
            qw.QMessageBox.warning(
                self, 'Save errors',
                'Some results could not be saved:\n' + '\n'.join(errors)
            )


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_section_label(text: str) -> qw.QLabel:
    lbl = qw.QLabel(f'— {text} —')
    font = lbl.font()
    font.setBold(True)
    lbl.setFont(font)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl
