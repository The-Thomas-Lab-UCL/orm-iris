"""
A class to control the plot for SERS mapping measurements. To be used inside the high level controller module.
"""
import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QTimer, QCoreApplication, Qt, QObject, QThread

import matplotlib
import matplotlib.backend_bases
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
matplotlib.use('Agg')   # Force matplotlib to use the backend to prevent memory leak

import threading
import queue
from typing import Any
from dataclasses import dataclass, fields

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *
from iris.data.measurement_RamanMap import MeaRMap_Hub,MeaRMap_Unit, MeaRMap_Plotter, PlotterOptions, PlotterParams, PlotterExtraParamsBase

from iris.resources.heatmap_plotter_ui import Ui_HeatmapPlotter

class HeatmapPlotter_Design(Ui_HeatmapPlotter, qw.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
        # Set the initial dock location
        self.main_win = self.window()
        
        self._register_videofeed_dock()
        self.dock_plot.installEventFilter(self)
        self.dock_plot.topLevelChanged.connect(self._handle_videofeed_docking_changed)
        
    def _register_videofeed_dock(self):
        if isinstance(self.main_win, qw.QMainWindow):
            # This tells the Main Window: "You are the boss of this dock now"
            self._dock_original_index = self.main_win.layout().indexOf(self.dock_plot)
            self._dock_original_index = max(0,self._dock_original_index-1)
            self.main_win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_plot)
            self.dock_plot.setFloating(True)
            self.dock_plot.setFloating(False)
            self.main_layout.insertWidget(self._dock_original_index, self.dock_plot)
    
    @Slot(bool)
    def _handle_videofeed_docking_changed(self,floating:bool):
        if floating:
            if isinstance(self.main_win, qw.QMainWindow):
                self.main_win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_plot)
            self.dock_plot.setFloating(True)
        else:
            self.main_layout.insertWidget(self._dock_original_index, self.dock_plot)
            self.main_layout.insertWidget(self._dock_original_index, self.dock_plot)
            self.dock_plot.setFloating(False)

@dataclass
class XYLimits:
    x_min:float|None = None
    x_max:float|None = None
    y_min:float|None = None
    y_max:float|None = None

class HeatmapPlotter_Worker(QObject):
    
    sig_plotready = Signal()  # Signal emitted when the plot is ready to be drawn in the main thread
    sig_finished_plotting = Signal()  # Signal emitted when the plotting is finished

    def __init__(self, plotter:MeaRMap_Plotter):
        super().__init__()
        self._plotter = plotter
        
    @Slot(PlotterOptions, PlotterParams, PlotterExtraParamsBase, XYLimits)
    def plot_heatmap(self, option:PlotterOptions, params:PlotterParams, extra_params:PlotterExtraParamsBase,
                     limits_xy:XYLimits) -> None:
        """
        Extracts the necessary measurement data to make the heatmap plot and then pass it onto the
        plotting queue
        """
        mappingUnit = params.mapping_unit
        if not isinstance(mappingUnit, MeaRMap_Unit) or not mappingUnit.check_measurement_and_metadata_exist():
            self.sig_finished_plotting.emit()
            return
        
        wavelength = params.wavelength
        if isinstance(wavelength, (int,float)):
            ramanshift = mappingUnit.convert(wavelength=wavelength) # pyright: ignore[reportAssignmentType] ; In this case wavelength is guaranteed to be float
            ramanshift_str = '{:.1f}'.format(ramanshift)
        else:
            ramanshift_str = 'N/A'
        
        title = f'{mappingUnit.get_unit_name()}\n{ramanshift_str}cm⁻¹ [{wavelength}nm]'
        params.title = title
        self._plotter.plot_heatmap(
            plotter=option,
            params=params,
            params_extra=extra_params,
        )
        ax = self._plotter.get_figure_axes()[1]
        
        ax.set_xlim(limits_xy.x_min, limits_xy.x_max)
        ax.set_ylim(limits_xy.y_min, limits_xy.y_max)
        
        self.sig_plotready.emit()
        self.sig_finished_plotting.emit()

class Wdg_MappingMeasurement_Plotter(qw.QWidget):
    
    sig_plotclicked_id = Signal(str)  # Signal emitted when the plot is clicked, sends (mappingUnit_ID (str))
    sig_plotclicked_coor = Signal(tuple)  # Signal emitted when the plot is clicked, sends (x_mm, y_mm)
    sig_mappingUnit_changed = Signal(str)  # Signal emitted when the mappingUnit selection is changed, sends (mappingUnit_name (str))
    
    _sig_request_update_plot = Signal()  # Signal to update the plot in the main thread
    _sig_request_update_comboboxes = Signal()  # Signal to update the comboboxes in the main thread
    
    _sig_udpate_plot = Signal(PlotterOptions, PlotterParams, PlotterExtraParamsBase, XYLimits)  # Signal to update the plot in the worker thread
    
    def __init__(
        self,
        parent,
        mappingHub:MeaRMap_Hub,
        layout:qw.QLayout|None = None,
        ):
        """
        Initialise the plot_mapping_measurements class
        
        Args:
            parent (qw.QWidget): Parent widget.
            mappingHub (MappingMeasurement_Hub): Mapping measurement hub to be used for plotting.
            callback_click (Callable[[tuple[str,tuple[float,float]]], None]|None): Callback function to be called on click events,
                it will call the function with the measurement ID and the coordinates of the click.
            layout (qw.QLayout|None): Optional layout to set for this widget.
        """
        assert isinstance(mappingHub,MeaRMap_Hub),'mappingHub must be an instance of MappingMeasurement_Hub'
        
        super().__init__(parent)
        self._mappingHub:MeaRMap_Hub = mappingHub
        
    # >>> Main widget setup <<<
        self._widget = HeatmapPlotter_Design(self)
        if layout is None:
            layout = qw.QVBoxLayout(self)
        self._main_layout = layout
        self._main_layout.addWidget(self._widget)
        wdg = self._widget
        
    # >>> Plot widgets and parameters set up <<<
    # > Parameters <
        # Analysers for data analysis:
        self._plotter = MeaRMap_Plotter()
        self._fig, self._ax = self._plotter.get_figure_axes()
        
        # Latest measurement data storage for plotting purposes only
        self._eve_plot_req = threading.Event()  # Event to request a plot update
        self._eve_combo_req = threading.Event()  # Event to request a combobox update
        self._current_mappingUnit:MeaRMap_Unit = MeaRMap_Unit()
        # Defer observer registration to prevent signals during initialization
        QTimer.singleShot(0, lambda: self._current_mappingUnit.add_observer(self._sig_request_update_plot.emit))
        
    # >>> Plotter selection setup <<<
        self._init_plotter_options_widgets()
    
    # >>> Plotter setup <<<
    # > Matplotlib plot setup <
        holder = wdg.lyt_heatmap_holder
        self._canvas_widget = FigureCanvas(figure=self._fig) # The plot widget
        holder.addWidget(self._canvas_widget)
        self._canvas_id_interaction = self._canvas_widget.mpl_connect('button_press_event', self._retrieve_click_idxcol) # The plot widget's canvas ID for interaction setups
        self._isplotting = False
        self._isupdating_comboboxes = False
        self._plotter.initialise_empty_plot()
        self._canvas_widget.draw_idle()
        
    # > Plot control widgets <
        # Subframes
        self._init_plot_control_widgets()
        
    # > General control widgets <
        # Set up the other widgets
        # self._btn_restart_threads = tk.Button(self._frm_generalControls,text='Restart auto-updater',command=self._reinitialise_auto_plot)
        self._lbl_coordinates = wdg.lbl_clickedcoor
        self._lbl_coordinates_ori = wdg.lbl_clickedcoor.text()
        
        lineedit_specpos = self._combo_plot_SpectralPosition.lineEdit()
        assert isinstance(lineedit_specpos, qw.QLineEdit), "lineedit_specpos must be a QLineEdit"
        lineedit_specpos.editingFinished.connect(lambda: self._set_combobox_closest_value(lineedit_specpos.text()))
        
        # Set the callbacks - defer to prevent signals during initialization
        QTimer.singleShot(0, lambda: self._mappingHub.add_observer(lambda:
            self._update_currentMappingUnit_observer(
            mappingUnit_name=self._current_mappingUnit.get_unit_name()
        )))
        
    # > Set the connections <<
        # Plot update timer
        # self._sig_request_update_plot.connect(lambda: self.plot_heatmap())
        self._sig_request_update_plot.connect(self.request_plot_heatmap)
        self._timer_plot = QTimer(self)
        self._timer_plot.setInterval(1000)
        self._timer_plot.timeout.connect(self._process_plot_request)
        self.destroyed.connect(self._timer_plot.stop)
        # Defer timer start until after event loop is running
        QTimer.singleShot(0, self._timer_plot.start)
        
        # Combobox update timer
        # self._sig_request_update_comboboxes.connect(lambda: self._update_comboboxes())
        self._sig_request_update_comboboxes.connect(lambda: self.request_combobox_update())
        self._timer_combobox = QTimer(self)
        self._timer_combobox.setInterval(1000)
        self._timer_combobox.timeout.connect(self._process_combobox_request)
        self.destroyed.connect(self._timer_combobox.stop)
        # Defer timer start until after event loop is running
        QTimer.singleShot(0, self._timer_combobox.start)
        
    # > Reset button <
        self._widget.btn_plotterreset.clicked.connect(lambda: self.reinitialise_plotter())
        
        self._init_worker_thread()
        
    def _init_worker_thread(self):
        """
        Initializes the worker thread for plotting
        """
        self._thread_plotter = QThread()
        self._worker_plotter = HeatmapPlotter_Worker(plotter=self._plotter)
        self._worker_plotter.moveToThread(self._thread_plotter)
        
        # Connect the signals
        self._sig_udpate_plot.connect(self._worker_plotter.plot_heatmap)
        self._worker_plotter.sig_plotready.connect(self.on_plotter_worker_plotready)
        self._worker_plotter.sig_finished_plotting.connect(self.on_plotter_worker_finished)
        
        # Defer thread start until after initialization is complete
        QTimer.singleShot(0, lambda: self._thread_plotter.start(QThread.Priority.NormalPriority))
        
    def _init_plot_control_widgets(self):
        """
        Initializes the widgets for the plot controls (save options, color limits, axis limits)
        """
        wdg = self._widget
        self._lbl_SpectralPosition = wdg.lbl_specposunit

        # Set up the comboboxes
        self._combo_plot_mappingUnitName = wdg.combo_unitchoise
        self._combo_plot_SpectralPosition = wdg.combo_spectralpos
        
        # Bind selections to plot the latest measurement_data df
        self._combo_plot_mappingUnitName.currentTextChanged.connect(lambda: self._sig_request_update_comboboxes.emit())
        self._combo_plot_SpectralPosition.currentIndexChanged.connect(lambda: self._sig_request_update_plot.emit())
        
        self._combo_plot_mappingUnitName.currentTextChanged.connect(self._emit_current_mappingUnit_name)
        
        # > Set up the save widgets
        wdg.btn_saveplot.clicked.connect(self.save_plot)
        wdg.btn_savedata.clicked.connect(self.save_plot_data)
        
        # > Set up the colour bar limit widgets
        self._entry_plot_clim_min = wdg.ent_cbar_min
        self._entry_plot_clim_max = wdg.ent_cbar_max
        self._chk_auto_clim = wdg.chk_autocbar
        wdg.chk_autocbar.stateChanged.connect(lambda: self._sig_request_update_plot.emit())
        
        # Bind enter key and changes to replot the heatmap
        def bind_enter_replot():
            wdg.chk_autocbar.setChecked(False)
            self._sig_request_update_plot.emit()
        self._entry_plot_clim_min.editingFinished.connect(bind_enter_replot)
        self._entry_plot_clim_max.editingFinished.connect(bind_enter_replot)
        
        # > Set up the xy limit widgets
        self._entry_plot_xlim_min = wdg.ent_xmin
        self._entry_plot_xlim_max = wdg.ent_xmax
        self._entry_plot_ylim_min = wdg.ent_ymin
        self._entry_plot_ylim_max = wdg.ent_ymax

        self._entry_plot_xlim_min.editingFinished.connect(lambda: self._sig_request_update_plot.emit())
        self._entry_plot_xlim_max.editingFinished.connect(lambda: self._sig_request_update_plot.emit())
        self._entry_plot_ylim_min.editingFinished.connect(lambda: self._sig_request_update_plot.emit())
        self._entry_plot_ylim_max.editingFinished.connect(lambda: self._sig_request_update_plot.emit())

        # > Set up the Raman shift / wavelength toggle
        self._chk_plot_in_RamanShift = wdg.chk_Ramanshift
        
    def _init_plotter_options_widgets(self):
        """
        Initialize the plotter option widgets
        """
        self._dict_plotter_opts = {option.value: option for option in PlotterOptions}
        self._dict_plotter_opts_kwargs = {
            option.value: self._plotter.get_plotter_params(option)
            for option in PlotterOptions
        }
        self._dict_plotter_kwargs_widgets:dict[str,qw.QLineEdit] = {}
        
        self._combo_plotter = self._widget.combo_plotoption
        self._combo_plotter.addItems(list(self._dict_plotter_opts.keys()))
        self._combo_plotter.currentTextChanged.connect(self._setup_plotter_options)
        self._combo_plotter.setCurrentIndex(0)
        
        self._setup_plotter_options()
        
    def reinitialise_plotter(self):
        """
        Reinitialise the plotter to its default state
        """
        print('Reinitialising plotter... (not yet implemented)')
        self._update_comboboxes()
        
    @Slot()
    def _setup_plotter_options(self):
        """
        Set up the plotter options for the current mapping plot
        """
        chosen_option = self._combo_plotter.currentText()
        self._plotter_extra_params:PlotterExtraParamsBase= self._dict_plotter_opts_kwargs[chosen_option]
        
        # Destroy the previous widgets
        holder = self._widget.lyt_plot_params # Form layout
        for widget in get_all_widgets_from_layout(holder):
            widget.deleteLater()
        QCoreApplication.processEvents()
        
        # Auto generate widgets for the plotter options
        self._dict_plotter_kwargs_widgets.clear()

        for field in fields(self._plotter_extra_params):
            key = field.name
            entry = qw.QLineEdit()
            entry.editingFinished.connect(lambda: self._sig_request_update_plot.emit())
            holder.addRow(f'{key}:',entry)
            self._dict_plotter_kwargs_widgets[key] = entry

        self._sig_request_update_plot.emit()
    
    def _emit_current_mappingUnit_name(self):
        """
        Emit the current mappingUnit name through the sig_mappingUnit_changed signal
        """
        mappingUnit_name = self._combo_plot_mappingUnitName.currentText()
        self.sig_mappingUnit_changed.emit(mappingUnit_name)
    
    def _get_plotter_kwargs(self) -> dict:
        """
        Get the plotter options for the current mapping plot
        
        Returns:
            dict: Plotter options for the current mapping plot
        """
        kwargs = {}
        for key in self._dict_plotter_kwargs_widgets.keys():
            entry = self._dict_plotter_kwargs_widgets[key]
            try: kwargs[key] = float(entry.text())
            except: kwargs[key] = entry.text()
        return kwargs
    
    def _set_current_mappingUnit(self,mappingUnit:MeaRMap_Unit):
        """
        Set a new mappingUnit to be observed

        Args:
            mappingUnit (MeaRMap_Unit): The mapping unit to be set
        """
        assert mappingUnit in self._mappingHub.get_list_MappingUnit(),\
            "This is a private method, only to be used when setting up a new mappingUnit to be observed"\
            "the mappingUnit set must be obtained from the internal self._mappingHub."
        self._current_mappingUnit = mappingUnit
        self._current_mappingUnit.add_observer(self._sig_request_update_plot.emit)
        
    def _set_combobox_closest_value(self, new_val:str):
        """
        Set the combobox to the closest wavelength to the entered value
        """
        if not self._current_mappingUnit.check_measurement_and_metadata_exist(): return
        try: current_spectralPosition = float(new_val)
        except Exception as e: print('_set_combobox_closest_value', e); return
        
        if self._chk_plot_in_RamanShift.isChecked():
            idx = self._current_mappingUnit.get_raman_shift_idx(current_spectralPosition)
        else:
            idx = self._current_mappingUnit.get_wavelength_idx(current_spectralPosition)
        self._combo_plot_SpectralPosition.setCurrentIndex(idx)
        
        self._sig_request_update_plot.emit()
        
    @Slot(str)
    def set_combobox_name(self,mappingUnit_name:str) -> None:
        """
        Set the mappingUnit and spectralPosition selection in the combobox
        
        Args:
            mappingUnit_id (str): MappingUnit_ID to be selected. If None, no change is made.
        """
        list_names = self._mappingHub.get_list_MappingUnit_names()
        if not mappingUnit_name in list_names: return
        
        self._combo_plot_mappingUnitName.blockSignals(True)
        self._combo_plot_mappingUnitName.setCurrentText(mappingUnit_name)
        self._combo_plot_mappingUnitName.blockSignals(False)
            
        self._update_currentMappingUnit_observer(mappingUnit_name=mappingUnit_name)
        
    @Slot()
    def _process_combobox_request(self) -> None:
        """
        Store a combobox update request to be executed in the main thread
        """
        if not self._eve_combo_req.is_set(): return
        self._eve_combo_req.clear()
        self._update_comboboxes()
        
    @Slot()
    def request_combobox_update(self) -> None:
        """
        Request an update of the comboboxes
        """
        self._eve_combo_req.set()
        
    def _update_comboboxes(self, set_unit_name:str|None=None, set_wavelength:float|None=None) -> None:
        """
        Refreshes the plotter's combobox according to the mappingUnits in the mappingHub
        
        Args:
            set_unit_name (str|None): Unit name to be selected after the refresh if possible.
            set_wavelength (float|None): Wavelength to be selected after the refresh if possible. It will\
                be set to Raman shift automatically according to the checkbox state.
        """
        if self._isupdating_comboboxes: return
        if self._combo_plot_mappingUnitName.hasFocus() or self._combo_plot_SpectralPosition.hasFocus():
            self._eve_combo_req.set()   # Re-request the update later
            return
        
        self._isupdating_comboboxes = True
        self._combo_plot_mappingUnitName.blockSignals(True)
        self._combo_plot_SpectralPosition.blockSignals(True)
        
        if set_unit_name is None: set_unit_name = self._combo_plot_mappingUnitName.currentText()
        set_wavelength = self.get_current_wavelength()
        
        # Check if there are any measurements in the mappingHub for the refresh. Returns if not
        if not self._mappingHub.check_measurement_exist():
            self._isupdating_comboboxes = False
            return
        
        list_valid_names = [unit.get_unit_name() for unit in self._mappingHub.get_list_MappingUnit()\
            if unit.check_measurement_and_metadata_exist()]
        
        if len(list_valid_names) == 0:
            self._isupdating_comboboxes = False
            return
        
        # Get the mappingUnit to be set
        list_names = self._mappingHub.get_list_MappingUnit_names()
        if set_unit_name in list_valid_names:
            mappingUnit = self._mappingHub.get_MappingUnit(unit_name=set_unit_name)
        elif self._current_mappingUnit.get_unit_name() in list_valid_names and\
            self._current_mappingUnit.check_measurement_and_metadata_exist():
            mappingUnit = self._current_mappingUnit
        else: mappingUnit = self._mappingHub.get_MappingUnit(unit_name=list_valid_names[0])
        unit_name = mappingUnit.get_unit_name()
        
        # Get the wavelength or Raman shift list to be set
        current_wavelength = self.get_current_wavelength()
        if isinstance(set_wavelength, (int,float)): set_wavelength = float(set_wavelength)
        elif isinstance(current_wavelength, (int,float)): set_wavelength = float(current_wavelength)
        else: set_wavelength = 0.0
        
        if self._chk_plot_in_RamanShift.isChecked(): list_spectral_position = mappingUnit.get_list_Raman_shift()
        else: list_spectral_position = mappingUnit.get_list_wavelengths()
        idx_spectral_position = mappingUnit.get_wavelength_idx(set_wavelength)
        list_spectral_position = [f'{pos:.2f}' for pos in list_spectral_position]
        
        # Check if the new list is different from the current one
        flg_update_name = False
        flg_update_specpos = False
        if self._combo_plot_mappingUnitName.count() != len(list_names):
            flg_update_name = True
        elif not all(self._combo_plot_mappingUnitName.itemText(i) == list_names[i] for i in range(len(list_names))):
            flg_update_name = True
        if self._combo_plot_SpectralPosition.count() != len(list_spectral_position):
            flg_update_specpos = True
        elif not all(self._combo_plot_SpectralPosition.itemText(i) == list_spectral_position[i] for i in range(len(list_spectral_position))):
            flg_update_specpos = True
        
        if flg_update_name:
            self._combo_plot_mappingUnitName.clear()
            self._combo_plot_mappingUnitName.addItems(list_names)
        self._combo_plot_mappingUnitName.setCurrentText(unit_name)
        
        if flg_update_specpos:
            self._combo_plot_SpectralPosition.clear()
            self._combo_plot_SpectralPosition.addItems(list_spectral_position)
        self._combo_plot_SpectralPosition.setCurrentIndex(idx_spectral_position)
        
        # Store the values
        self._current_mappingUnit = mappingUnit
        
        # Plot the changes
        if flg_update_name or flg_update_specpos:
            self._sig_request_update_plot.emit()
        
        self._combo_plot_mappingUnitName.blockSignals(False)
        self._combo_plot_SpectralPosition.blockSignals(False)
        self._isupdating_comboboxes = False
        
    def _get_plotter_option(self) -> PlotterOptions:
        """
        Get the current plotter option from the combobox
        
        Returns:
            PlotterOptions: The current plotter option
        """
        chosen_option = self._combo_plotter.currentText()
        return self._dict_plotter_opts[chosen_option]
        
    def _get_plotter_extra_params(self) -> PlotterExtraParamsBase:
        """
        Get the current plotter extra parameters from the widgets
        
        Returns:
            PlotterExtraParamsBase: The current plotter extra parameters
        """
        for field in fields(self._plotter_extra_params):
            key = field.name
            entry = self._dict_plotter_kwargs_widgets[key]
            val_type = field.type
            try:
                if val_type == float:
                    setattr(self._plotter_extra_params, key, float(entry.text()))
                elif val_type == int:
                    setattr(self._plotter_extra_params, key, int(float(entry.text())))
                else:
                    setattr(self._plotter_extra_params, key, entry.text())
            except:
                setattr(self._plotter_extra_params, key, field.default)
        return self._plotter_extra_params
        
    @Slot()
    def request_plot_heatmap(self) -> None:
        """
        Replot the heatmap using the current mappingHub and the selected mappingUnit_ID and SpectralPosition
        """
        self._eve_plot_req.set()
        
    @Slot()
    def _process_plot_request(self) -> None:
        """
        Store a plot request to be executed in the main thread
        """
        if not self._eve_plot_req.is_set(): return
        self._eve_plot_req.clear()
        self.plot_heatmap()
        
    def get_selected_mappingUnit(self) -> MeaRMap_Unit|None:
        """
        Get the currently selected mapping unit from the combo box.
        
        Returns:
            MappingMeasurement_Unit: The currently selected mapping unit.
        """
        return self._current_mappingUnit
    
    def _update_currentMappingUnit_observer(self, mappingUnit_name:str) -> None:
        """
        Update the currently selected mapping unit according to the new combobox selection
        
        Args:
            mappingUnit_name (str): The name of the mapping unit to be set. If it doesn't exist, the
                first valid mapping unit will be selected.
        """
        # Remove observer
        try: self._current_mappingUnit.remove_observer(self._sig_request_update_plot.emit)
        except Exception as e: print('_update_currentMappingUnit_observer',e)
        
        try:
            # Set the new mapping unit and check if it's valid
            self._current_mappingUnit = self._mappingHub.get_MappingUnit(unit_name=mappingUnit_name)
            assert self._current_mappingUnit.check_measurement_and_metadata_exist(),\
                "Mapping unit is not valid."
        except Exception as e:
            # Set to the first valid mapping unit if the selected one is not valid
            list_valid_names = [unit.get_unit_name() for unit in self._mappingHub.get_list_MappingUnit() if unit.check_measurement_and_metadata_exist()]
            if len(list_valid_names) > 0: self._current_mappingUnit = self._mappingHub.get_MappingUnit(unit_name=list_valid_names[0])
            else: self._current_mappingUnit = MeaRMap_Unit()
        finally:
            self._current_mappingUnit.add_observer(self._sig_request_update_plot.emit)
        
        self._sig_request_update_comboboxes.emit()
        
    @Slot()
    def on_plotter_worker_finished(self) -> None:
        """
        Slot called when the plotter worker has finished plotting
        """
        self._isplotting = False
        
    @Slot()
    def on_plotter_worker_plotready(self) -> None:
        """
        Slot called when the plotter worker has finished plotting and the plot is ready to be drawn
        """
        self._canvas_widget.draw_idle()
    
    def plot_heatmap(self):
        """
        Extracts the necessary measurement data to make the heatmap plot and then pass it onto the
        plotting queue
        """
        if not self._widget.dock_plot.isVisible(): return
        if self._isplotting: return
        assert isinstance(self._mappingHub,MeaRMap_Hub),\
            "plot_heatmap: Measurement data is not of the correct type. Expected: MappingMeasurement_Hub"
        
        mappingUnit = self._current_mappingUnit
        if not isinstance(mappingUnit, MeaRMap_Unit) or not mappingUnit.check_measurement_and_metadata_exist(): return

        # >>> Find the wavelength
        wavelength = self.get_current_wavelength()
        if wavelength is None: return
        
        self._isplotting = True
        self._current_mappingUnit = mappingUnit
        
        #PlotterOptions, PlotterParams, PlotterExtraParamsBase, XYLimits
        options = self._get_plotter_option()
        params = PlotterParams(
            mapping_unit=mappingUnit,
            wavelength=wavelength,
            clim=None,
        )
        params_extra = self._get_plotter_extra_params()
        limits_xy = self._get_plot_xylim()
        
        try: clim_min = float(self._entry_plot_clim_min.text())
        except: clim_min = None
        try: clim_max = float(self._entry_plot_clim_max.text())
        except: clim_max = None
        clim = (clim_min,clim_max)
        if self._chk_auto_clim.isChecked(): clim = (None,None)
        params.clim = clim
        
        self._sig_udpate_plot.emit(
            options,
            params,
            params_extra,
            limits_xy,
        )
        
        self._isplotting = False
        
    @thread_assign
    def save_plot(self):
        """
        Save the current plot as an image, asks the user for the file path
        """
        try:
            filename = self._combo_plot_mappingUnitName.currentText()
            filepath = qw.QFileDialog.getSaveFileName(
                self,
                'Save plot as PNG',
                filename,
                'PNG files (*.png)')[0]
            if filepath == '': return
            
            self._fig.tight_layout()
            self._canvas_widget.draw_idle()
            self._canvas_widget.update_idletasks() # Process pending idle tasks
            self._canvas_widget.update() # Process pending events
            self._canvas_widget.after_idle(self._canvas_widget.print_png,filepath)

            qw.QMessageBox.information(self, 'Save plot', 'Plot saved successfully')
        except Exception as e: print('save_plot',e); return
        
    @thread_assign
    def save_plot_data(self):
        """
        Save the current plot data as a csv file, asks the user for the file path
        """
        try:
            if not isinstance(self._current_mappingUnit, MeaRMap_Unit) or\
                not self._current_mappingUnit.check_measurement_and_metadata_exist(): return
            filepath = qw.QFileDialog.getSaveFileName(self,
                'Save plot data', '',
                'data.csv',
                'CSV files (*.csv)')[0]
            
            spectralPosition_idx = self._combo_plot_SpectralPosition.currentIndex()
            list_wavelength = self._current_mappingUnit.get_list_wavelengths()
            wavelength = list_wavelength[spectralPosition_idx]
            df = self._current_mappingUnit.get_heatmap_table(wavelength)
            df.to_csv(filepath)
            qw.QMessageBox.information(self, 'Save data', 'Data saved successfully')
        except Exception as e: print('save_plot_data',e); return
    
    def _get_plot_xylim(self) -> XYLimits:
        """
        Gets the x and y limits of the plot using the values in the widgets
        
        Returns:
            XYLimits: The x and y limits of the plot
        """
        # Get the x and y limits
        try: xlim_min = float(self._entry_plot_xlim_min.text())
        except: xlim_min = None
        try: xlim_max = float(self._entry_plot_xlim_max.text())
        except: xlim_max = None
        try: ylim_min = float(self._entry_plot_ylim_min.text())
        except: ylim_min = None
        try: ylim_max = float(self._entry_plot_ylim_max.text())
        except: ylim_max = None
        
        return XYLimits(
            x_min=xlim_min,
            x_max=xlim_max,
            y_min=ylim_min,
            y_max=ylim_max,
        )
    
    def get_current_wavelength(self) -> float|None:
        """
        Retrieves the current wavelength being plotted.
        Returns:
            float|None: The current wavelength or None if not set.
        """
        if not isinstance(self._current_mappingUnit, MeaRMap_Unit) or\
            not self._current_mappingUnit.check_measurement_and_metadata_exist():
            return None
        
        # TODO: This often gets called before the comboboxes are fully populated, triggering the exceptions
        try:
            qw.QApplication.processEvents()
            current_val = float(self._combo_plot_SpectralPosition.currentText())
        except Exception as e: return None
        
        if self._chk_plot_in_RamanShift.isChecked():
            ret = self._current_mappingUnit.convert(Raman_shift=current_val)
        else: ret = current_val
        ret = self._current_mappingUnit.get_closest_wavelength(ret) # pyright: ignore[reportArgumentType] ; In this case ret is guaranteed to be float
        
        return ret

    def _retrieve_click_idxcol(self,event:matplotlib.backend_bases.MouseEvent|Any):
        """
        Retrieve the index and the column where the figure is clicked
        """
        if event.inaxes and isinstance(self._current_mappingUnit, MeaRMap_Unit)\
            and self._current_mappingUnit.check_measurement_and_metadata_exist():
            coorx,coory = event.xdata,event.ydata
            if coorx is None or coory is None: return
            
            clicked_measurementId = self._current_mappingUnit.get_measurementId_from_coor(coor=(coorx,coory))
            ramanMea = self._current_mappingUnit.get_RamanMeasurement(clicked_measurementId)
            try:
                wavelength = self.get_current_wavelength()
                if wavelength is None: raise ValueError('Wavelength is None')
                intensity = ramanMea.get_intensity(wavelength=wavelength)
                intensity_str = f"{intensity:.1f}"
            except Exception as e:
                print('_retrieve_click_idxcol: ',e)
                intensity_str = 'error'
                
            self._lbl_coordinates.setText(
                f"x={coorx:.3f} mm, y={coory:.3f} mm, intensity={intensity_str} (a.u.)"
            )
            
            self.sig_plotclicked_id.emit(str(clicked_measurementId))
            self.sig_plotclicked_coor.emit((coorx,coory))

def test_plotter():
    import sys
    from iris.data.measurement_RamanMap import generate_dummy_mappingHub, test_datasaveload_system
    from iris.gui.dataHub_MeaRMap import Wdg_DataHub_Mapping
    
    mappinghub = MeaRMap_Hub()
    # test_datasaveload_system(mappinghub)
    
    app = qw.QApplication([])
    window = qw.QMainWindow()
    window.show()
    main_wdg = qw.QWidget()
    window.setCentralWidget(main_wdg)
    lyt = qw.QHBoxLayout(main_wdg)
    
    queue_click = queue.Queue()
    wdg_plotter = Wdg_MappingMeasurement_Plotter(
        main_wdg,
        mappingHub=mappinghub,
        )
    wdg_plotter.sig_plotclicked_id.connect(lambda data: queue_click.put(data))
    wdg_plotter.request_plot_heatmap()
    lyt.addWidget(wdg_plotter)

    dataHub = Wdg_DataHub_Mapping(
        window,
        mappingHub=mappinghub
    )
    dataHub.update_tree()
    lyt.addWidget(dataHub)
    
    def retrieve_click():
        while True:
            print('Clicked:',queue_click.get())
    threading.Thread(target=retrieve_click).start()
    
    mappinghub.test_generate_dummy(3)
    
    sys.exit(app.exec())
    
if __name__=="__main__":
    test_plotter()