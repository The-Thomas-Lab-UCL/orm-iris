import sys
import os

if __name__ == '__main__':
    SCRIPT_DIR = os.path.abspath(r'..\library')
    EXT_DIR = os.path.abspath(r'..\extensions')
    sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
    sys.path.insert(0, os.path.dirname(EXT_DIR))

import numpy as np
from matplotlib.path import Path as MplPath
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import PySide6.QtWidgets as qw
from PySide6.QtCore import Qt, Signal, Slot, QObject, QThread

from typing import Callable, Iterable

from extensions.extension_template import Extension_MainWindow
from extensions.extension_intermediary import Ext_DataIntermediary as Intermediary

from iris.data.measurement_image import MeaImg_Unit
from iris.data.measurement_coordinates import MeaCoor_mm
from iris.data.measurement_coordinates import List_MeaCoor_Hub

from extensions.bf_sersSubstrate_coorGen.bf_sersSubstrate_coorGen_ui import Ui_bf_sresSubstrate_coorGen

from extensions.bf_sersSubstrate_coorGen.masking.fitting import (
    Param_Smoothen_Boundary, fit_ellipse_ransac, smoothen_boundary,
)
from extensions.bf_sersSubstrate_coorGen.masking.basic_image_processing import (
    Params_Centre_Estimation, Params_Edge_Detection,
    estimate_centre_blurring, detect_edge_Sobel,
)
from extensions.bf_sersSubstrate_coorGen.masking.image_preprocessing import convert_img2gray_s_channel
from extensions.bf_sersSubstrate_coorGen.utils import generate_mask  # noqa: F401  (available for future overlay use)


# ── Data classes ──────────────────────────────────────────────────────────────

class ProcessResult:
    def __init__(self, img_unit: MeaImg_Unit, coor: MeaCoor_mm,
                 arr: np.ndarray, S: np.ndarray,
                 cx_est: float, cy_est: float,
                 ellipse_sobel, ellipse_fit, ellipse_smooth, ellipse_clean,
                 boundary_px_x: np.ndarray, boundary_px_y: np.ndarray,
                 boundary_stage_mm: np.ndarray, boundary_stage_mm_expanded: np.ndarray,
                 scan_pts_stage: np.ndarray, scan_pts_mea: np.ndarray,
                 expansion_mm: float, step_size_mm: float):
        self._img_unit = img_unit
        self._coor = coor
        self._arr = arr
        self._S = S
        self._cx_est = cx_est
        self._cy_est = cy_est
        self._ellipse_sobel = ellipse_sobel
        self._ellipse_fit = ellipse_fit
        self._ellipse_smooth = ellipse_smooth
        self._ellipse_clean = ellipse_clean
        self._bx = boundary_px_x
        self._by = boundary_px_y
        self._boundary_stage = boundary_stage_mm
        self._boundary_expanded = boundary_stage_mm_expanded
        self._scan_pts_stage = scan_pts_stage
        self._scan_pts_mea = scan_pts_mea
        self._expansion_mm = expansion_mm
        self._step_size_mm = step_size_mm

    def get_name(self) -> str:
        return self._img_unit.get_IdName()[1]

    def get_coor(self) -> MeaCoor_mm:
        return self._coor


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


# ── Worker: run the full pipeline for a list of MeaImg_Units ─────────────────

class _PipelineParams:
    """Plain-data carrier so the worker doesn't touch Qt widgets."""
    def __init__(self,
                 params_centre: Params_Centre_Estimation,
                 params_edge: Params_Edge_Detection,
                 params_smooth: Param_Smoothen_Boundary,
                 ransac_threshold: float,
                 ransac_trials: int,
                 step_size_mm: float,
                 z_mm: float,
                 expansion_mm: float):
        self.params_centre = params_centre
        self.params_edge = params_edge
        self.params_smooth = params_smooth
        self.ransac_threshold = ransac_threshold
        self.ransac_trials = ransac_trials
        self.step_size_mm = step_size_mm
        self.z_mm = z_mm
        self.expansion_mm = expansion_mm


class _ProcessWorker(QObject):
    sig_result = Signal(object)   # emits ProcessResult
    sig_error  = Signal(str, str) # (unit_name, error_message)
    sig_done   = Signal()

    def __init__(self, units: list[MeaImg_Unit], params: _PipelineParams):
        super().__init__()
        self._units = units
        self._p = params

    @Slot()
    def run(self):
        for unit in self._units:
            name = unit.get_IdName()[1]
            try:
                result = self._process_unit(unit)
                self.sig_result.emit(result)
            except Exception as e:
                self.sig_error.emit(name, str(e))
        self.sig_done.emit()

    def _process_unit(self, unit: MeaImg_Unit) -> ProcessResult:
        p = self._p

        # Load stitched image
        img_stitched, coor_min_mm, _ = unit.get_image_all_stitched(low_res=False)
        arr = np.array(img_stitched.convert('RGB'))

        # Pipeline
        S = convert_img2gray_s_channel(arr)
        cx_est, cy_est = estimate_centre_blurring(S, params=p.params_centre)
        ellipse_sobel = detect_edge_Sobel(S, cx_est, cy_est, params=p.params_edge)
        ellipse_fit = fit_ellipse_ransac(
            ellipse_sobel,
            residual_threshold=p.ransac_threshold,
            max_trials=p.ransac_trials,
        )
        ellipse_smooth, ellipse_clean = smoothen_boundary(ellipse_sobel, ellipse_fit, params=p.params_smooth)

        boundary_cart = ellipse_smooth.get_cartesian()
        bx, by = boundary_cart.x, boundary_cart.y

        # Pixel → stage coordinates
        boundary_stage_mm = np.array([
            unit.convert_imgpt2stg(
                frame_coor_mm=coor_min_mm,
                coor_pixel=(float(px), float(py)),
                correct_rot=True,
                low_res=False,
            )
            for px, py in zip(bx, by)
        ])

        # Minkowski-sum expansion
        boundary_stage_mm_expanded = self._expand_boundary(boundary_stage_mm, p.expansion_mm)

        # Grid generation
        polygon = MplPath(boundary_stage_mm_expanded)
        x_min = boundary_stage_mm_expanded[:, 0].min()
        x_max = boundary_stage_mm_expanded[:, 0].max()
        y_min = boundary_stage_mm_expanded[:, 1].min()
        y_max = boundary_stage_mm_expanded[:, 1].max()

        xs = np.arange(x_min, x_max + p.step_size_mm, p.step_size_mm)
        ys = np.arange(y_min, y_max + p.step_size_mm, p.step_size_mm)
        xx, yy = np.meshgrid(xs, ys)
        grid_candidates = np.column_stack([xx.ravel(), yy.ravel()])
        inside = polygon.contains_points(grid_candidates)
        scan_pts_stage = grid_candidates[inside]

        scan_pts_mea = np.array([
            unit.convert_stg2mea((float(x), float(y)))
            for x, y in scan_pts_stage
        ])

        scan_coordinates = [
            (float(x), float(y), float(p.z_mm))
            for x, y in scan_pts_mea
        ]

        unit_name = unit.get_IdName()[1]
        coor = MeaCoor_mm(
            mappingUnit_name=unit_name,
            mapping_coordinates=scan_coordinates,
        )

        return ProcessResult(
            img_unit=unit,
            coor=coor,
            arr=arr,
            S=S,
            cx_est=float(cx_est),
            cy_est=float(cy_est),
            ellipse_sobel=ellipse_sobel,
            ellipse_fit=ellipse_fit,
            ellipse_smooth=ellipse_smooth,
            ellipse_clean=ellipse_clean,
            boundary_px_x=bx,
            boundary_px_y=by,
            boundary_stage_mm=boundary_stage_mm,
            boundary_stage_mm_expanded=boundary_stage_mm_expanded,
            scan_pts_stage=scan_pts_stage,
            scan_pts_mea=scan_pts_mea,
            expansion_mm=p.expansion_mm,
            step_size_mm=p.step_size_mm,
        )

    @staticmethod
    def _expand_boundary(boundary: np.ndarray, expansion_mm: float) -> np.ndarray:
        centroid = boundary.mean(axis=0)
        n_circle = 36
        circle_angles = np.linspace(0, 2 * np.pi, n_circle, endpoint=False)
        offsets = expansion_mm * np.column_stack([np.cos(circle_angles), np.sin(circle_angles)])
        all_candidates = (boundary[:, None, :] + offsets[None, :, :]).reshape(-1, 2)
        cand_vec = all_candidates - centroid
        cand_angles = np.arctan2(cand_vec[:, 1], cand_vec[:, 0])
        cand_radii = np.linalg.norm(cand_vec, axis=1)
        n_bins = len(boundary)
        bin_edges = np.linspace(-np.pi, np.pi, n_bins + 1)
        expanded_pts = []
        for i in range(n_bins):
            in_bin = (cand_angles >= bin_edges[i]) & (cand_angles < bin_edges[i + 1])
            if not in_bin.any():
                continue
            best = np.argmax(cand_radii[in_bin])
            expanded_pts.append(all_candidates[in_bin][best])
        return np.array(expanded_pts)


# ── Worker: render full pipeline collage for a single ProcessResult ───────────

class _PlotWorker(QObject):
    sig_done = Signal(object, object)  # (Figure, result_name)

    def __init__(self, result: ProcessResult):
        super().__init__()
        self._result = result

    @Slot()
    def run(self):
        from skimage import filters as skfilters
        r = self._result

        fig = Figure(figsize=(12, 16))
        fig.set_tight_layout(True)
        ax = fig.subplot_mosaic(
            [['rgb',     's_ch'  ],
             ['centre',  'sobel' ],
             ['ransac',  'smooth'],
             ['overlay', 'mea'  ]],
        )

        fs = 7  # common font size for titles / labels

        # ── Affine transform: stage mm → image pixel ───────────────────────
        # Derived from the boundary (known in both coordinate systems).
        # Handles rotation + scale without needing to store coor_min_mm.
        N = len(r._bx)
        src = np.column_stack([r._boundary_stage, np.ones(N)])
        Ax, _, _, _ = np.linalg.lstsq(src, r._bx, rcond=None)
        Ay, _, _, _ = np.linalg.lstsq(src, r._by, rcond=None)

        def stg2px(pts_mm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            h = np.column_stack([pts_mm, np.ones(len(pts_mm))])
            return h @ Ax, h @ Ay

        exp_px_x, exp_px_y = stg2px(r._boundary_expanded)
        scan_px_x, scan_px_y = stg2px(r._scan_pts_stage)

        # ── Row 0 ──────────────────────────────────────────────────────────
        ax['rgb'].imshow(r._arr)
        ax['rgb'].set_title('RGB input', fontsize=fs)
        ax['rgb'].axis('off')

        ax['s_ch'].imshow(r._S, cmap='gray')
        ax['s_ch'].set_title('S channel', fontsize=fs)
        ax['s_ch'].axis('off')

        S_blurred = skfilters.gaussian(r._S, sigma=40)
        ax['centre'].imshow(S_blurred, cmap='gray')
        ax['centre'].scatter(r._cx_est, r._cy_est, s=60, c='red', marker='x', zorder=5)
        ax['centre'].set_title(f'Centre est. ({r._cx_est:.0f}, {r._cy_est:.0f}) px', fontsize=fs)
        ax['centre'].axis('off')

        # ── Row 1 ──────────────────────────────────────────────────────────
        S_blur_sobel = skfilters.gaussian(r._S, sigma=5)
        sobel_img = skfilters.sobel(S_blur_sobel)
        ax['sobel'].imshow(sobel_img, cmap='gray')
        ax['sobel'].scatter(r._ellipse_sobel.x, r._ellipse_sobel.y,
                            s=2, c='red', marker='x', label='Edge samples')
        ax['sobel'].set_title(f'Sobel edges  ({len(r._ellipse_sobel.x)} samples)', fontsize=fs)
        ax['sobel'].axis('off')
        ax['sobel'].legend(fontsize=fs - 1, markerscale=2)

        f = r._ellipse_fit
        t = np.linspace(0, 2 * np.pi, 200)
        ex = f.xc + f.a * np.cos(t) * np.cos(f.theta) - f.b * np.sin(t) * np.sin(f.theta)
        ey = f.yc + f.a * np.cos(t) * np.sin(f.theta) + f.b * np.sin(t) * np.cos(f.theta)
        ax['ransac'].imshow(r._S, cmap='gray')
        ax['ransac'].scatter(r._ellipse_sobel.x, r._ellipse_sobel.y,
                             s=1, c='blue', alpha=0.4, label='Edge samples')
        ax['ransac'].plot(ex, ey, 'g-', lw=1.5, label='RANSAC fit')
        ax['ransac'].scatter(f.xc, f.yc, s=40, c='yellow', zorder=5)
        ax['ransac'].set_title(
            f'RANSAC  Ø{f.major_d:.0f}×{f.minor_d:.0f} px  circ={f.circularity:.3f}',
            fontsize=fs)
        ax['ransac'].axis('off')
        ax['ransac'].legend(fontsize=fs - 1)

        raw_r, raw_theta = r._ellipse_sobel.get_polar(
            centre_x=r._ellipse_fit.xc, centre_y=r._ellipse_fit.yc)
        sort_raw = np.argsort(np.degrees(raw_theta))
        ax['smooth'].plot(np.degrees(raw_theta)[sort_raw] + 180,
                          raw_r[sort_raw], 'b-', lw=0.8, label='Raw')
        ax['smooth'].plot(np.degrees(r._ellipse_clean.theta) + 180,
                          r._ellipse_clean.r, 'r-', lw=0.8, label='Cleaned')
        ax['smooth'].plot(np.degrees(r._ellipse_smooth.theta) + 180,
                          r._ellipse_smooth.r, 'g-', lw=1.2, label='Smoothed')
        ax['smooth'].set_title('Boundary radius vs angle', fontsize=fs)
        ax['smooth'].set_xlabel('Angle (°)', fontsize=fs)
        ax['smooth'].set_ylabel('Radius (px)', fontsize=fs)
        ax['smooth'].tick_params(labelsize=fs - 1)
        ax['smooth'].legend(fontsize=fs - 1)

        # ── Row 2 — image overlay (spans 2 cols) + measurement frame ───────
        ax['overlay'].imshow(r._arr)
        ax['overlay'].plot(r._bx, r._by,
                           'r-', lw=1.5, label='Detected boundary')
        ax['overlay'].plot(exp_px_x, exp_px_y,
                           'r--', lw=1, label=f'+{r._expansion_mm * 1e3:.0f} µm expansion')
        ax['overlay'].scatter(scan_px_x, scan_px_y,
                              s=3, c='cyan', alpha=0.6,
                              label=f'N={len(r._coor.mapping_coordinates)} scan pts')
        ax['overlay'].scatter(f.xc, f.yc, s=60, c='yellow', zorder=5, label='Centre')
        ax['overlay'].set_title(
            f'Scan grid overlay  |  step={r._step_size_mm * 1e3:.0f} µm  |  N={len(r._coor.mapping_coordinates)}',
            fontsize=fs)
        ax['overlay'].axis('off')
        ax['overlay'].legend(fontsize=fs - 1)

        sc_arr = np.array(r._coor.mapping_coordinates)
        ax['mea'].scatter(sc_arr[:, 0], sc_arr[:, 1],
                          s=2, c='darkorange', alpha=0.6, label='Scan pts (mea)')
        ax['mea'].set_aspect('equal')
        ax['mea'].set_xlabel('X mea [mm]', fontsize=fs)
        ax['mea'].set_ylabel('Y mea [mm]', fontsize=fs)
        ax['mea'].tick_params(labelsize=fs - 1)
        ax['mea'].set_title('Measurement frame (laser position)', fontsize=fs)
        ax['mea'].legend(fontsize=fs - 1)

        self.sig_done.emit(fig, r.get_name())


# ── Main extension window ─────────────────────────────────────────────────────

class Ext_BF_SERSSubstrate_coorGen(Ui_bf_sresSubstrate_coorGen, Extension_MainWindow):

    _sig_update_img_list = Signal()

    def __init__(self, parent, intermediary: Intermediary):
        super().__init__(parent, intermediary)
        self.setupUi(self)
        self.setWindowTitle("BF SERS Substrate Coordinate Generator")

        self._imghub = intermediary.get_datahub_image_gui().get_ImageMeasurement_Hub()
        self._coorhub: List_MeaCoor_Hub = intermediary.get_coorhub()

        self._process_results = List_ProcessResult()
        self._process_results.add_observer(self._sync_result_tree)

        self._process_thread: QThread | None = None
        self._process_worker: _ProcessWorker | None = None

        self._plot_thread: QThread | None = None
        self._plot_worker: _PlotWorker | None = None
        self._pending_plot_result: ProcessResult | None = None

        self._init_params_widgets()
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

        def _add_spin(label: str, value: float, min_: float, max_: float,
                      decimals: int = 3, suffix: str = '') -> qw.QDoubleSpinBox:
            spin = qw.QDoubleSpinBox()
            spin.setRange(min_, max_)
            spin.setDecimals(decimals)
            spin.setValue(value)
            if suffix:
                spin.setSuffix(suffix)
            lyt.addRow(label, spin)
            return spin

        def _add_ispin(label: str, value: int, min_: int, max_: int) -> qw.QSpinBox:
            spin = qw.QSpinBox()
            spin.setRange(min_, max_)
            spin.setValue(value)
            lyt.addRow(label, spin)
            return spin

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
        self._spin_step_mm       = _add_spin('Step size [mm]',    0.05, 0.001, 10.0, 3)
        self._spin_z_mm          = _add_spin('Z position [mm]',   0.0, -50.0, 50.0, 3)
        self._spin_expansion_mm  = _add_spin('ROI expansion [mm]', 0.1, 0.0,   5.0, 3)

    def _read_params(self) -> _PipelineParams:
        return _PipelineParams(
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
            step_size_mm=self._spin_step_mm.value(),
            z_mm=self._spin_z_mm.value(),
            expansion_mm=self._spin_expansion_mm.value(),
        )

    # ── Result tab: plot canvas + buttons ─────────────────────────────────

    def _init_result_plot(self):
        fig = Figure(figsize=(5, 5), tight_layout=True)
        self._result_ax = fig.add_subplot(111)
        self._result_ax.axis('off')
        self._result_canvas = FigureCanvas(fig)
        self.lyt_result.addWidget(self._result_canvas)

    def _init_result_buttons(self):
        btn_row = qw.QHBoxLayout()
        self.btn_remove  = qw.QPushButton("Remove selected")
        self.btn_saveall = qw.QPushButton("Save all to CoorHub")
        btn_row.addWidget(self.btn_remove)
        btn_row.addWidget(self.btn_saveall)
        self.verticalLayout_7.addLayout(btn_row)

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
        selected_names = [item.text(0) for item in self.tree_img.selectedItems()]
        if not selected_names:
            qw.QMessageBox.information(self, 'No selection', 'Please select at least one image unit.')
            return

        units = [self._imghub.get_ImageMeasurementUnit(unit_name=n) for n in selected_names]
        params = self._read_params()

        self.btn_process.setEnabled(False)

        self._process_worker = _ProcessWorker(units, params)
        self._process_thread = QThread(self)
        self._process_worker.moveToThread(self._process_thread)

        self._process_thread.started.connect(self._process_worker.run)
        self._process_worker.sig_result.connect(self._on_process_result)
        self._process_worker.sig_error.connect(self._on_process_error)
        self._process_worker.sig_done.connect(self._on_process_done)
        self._process_worker.sig_done.connect(self._process_thread.quit)
        self._process_thread.finished.connect(self._process_worker.deleteLater)
        self._process_thread.finished.connect(self._process_thread.deleteLater)

        self._process_thread.start()

    @Slot(object)
    def _on_process_result(self, result: ProcessResult):
        self._process_results.append(result)

    @Slot(str, str)
    def _on_process_error(self, unit_name: str, msg: str):
        qw.QMessageBox.warning(self, f'Error processing {unit_name}', msg)

    @Slot()
    def _on_process_done(self):
        self.btn_process.setEnabled(True)
        self._process_thread = None
        self._process_worker = None
        self.tabWidget.setCurrentWidget(self.tab_result)

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
        self._result_canvas.draw_idle()
        import matplotlib.pyplot as plt
        plt.close(old_fig)

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
        name = items[0].text(0)
        to_remove = next((r for r in self._process_results if r.get_name() == name), None)
        if to_remove is not None:
            self._process_results.remove(to_remove)

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
