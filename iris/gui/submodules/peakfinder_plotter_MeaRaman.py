import PySide6.QtWidgets as qw
from PySide6.QtCore import Signal, Slot, QTimer, QCoreApplication, QObject, QThread

import matplotlib
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
matplotlib.use('Agg')   # Force matplotlib to use the backend to prevent memory leak

from scipy.signal import find_peaks
import bisect
from dataclasses import dataclass, fields, asdict
from typing import Dict

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.insert(0, os.path.dirname(libdir))

from iris.utils.general import *

from iris.data.measurement_Raman import MeaRaman, MeaRaman_Plotter, MeaRaman_Handler

from iris.resources.spectra_peak_finder_ui import Ui_spectra_peak_finder

@dataclass
class PeakFinderOptions:
    height: str = ''
    threshold: str = ''
    distance: str = ''
    prominence: str = ''
    width: str = ''
    wlen: str = ''
    rel_height: str = ''
    plateau_size: str = ''

class PeakFinderPlotter_Worker(QObject):
    
    sig_peaks = Signal(list,list,list)
    sig_error = Signal(str)
    sig_drawPlot = Signal()
    
    def __init__(self,plotter:MeaRaman_Plotter):
        """
        Initialises the Peak Finder Plotter Worker.

        Args:
            canvas (FigureCanvas): The matplotlib figure canvas
        """
        super().__init__()
        self._plotter = plotter
    
    @Slot(MeaRaman, dict, tuple, bool)
    def plot_spectra(self, mea:MeaRaman, options:dict, limits:tuple,
                     flg_RamanShift:bool) -> None:
        """
        Plots the Raman spectra.
        
        Args:
            mea (RamanMeasurement): The Raman measurement
            options (dict): The options for peak finding
            limits (tuple): The plot limits
            flg_RamanShift (bool): Whether to plot Raman shift or wavelength
        """
        list_wavelength = mea.get_measurements()[-1][mea.label_wavelength]
        list_intensity = mea.get_measurements()[-1][mea.label_intensity]
        
        try:
            peaks_idx = find_peaks(list_intensity,**options)[0]
            peak_wavelength = [list_wavelength[i] for i in peaks_idx]
            peak_intensity = [list_intensity[i] for i in peaks_idx]
            
            laser_wavelength = mea.get_laser_params()[1]
            list_peak_Ramanshift_str = ['{:1f}'.format(convert_wavelength_to_ramanshift(wavelength,laser_wavelength)) for wavelength in peak_wavelength]
            list_peak_intensity_str = ['{:3f}'.format(list_intensity[i]) for i in peaks_idx]
            list_peak_wavelength_str = ['{:1f}'.format(list_wavelength[i]) for i in peaks_idx]
            
            # Update the treeview
            self._plotter.plot_scatter(
                measurement=mea,
                title='Raman spectra of {}'.format(str(mea.get_latest_timestamp())),
                list_scatter_wavelength=peak_wavelength,
                list_scatter_intensity=peak_intensity,
                flg_plot_ramanshift=flg_RamanShift,
                limits=limits,
            )
            
            self.sig_peaks.emit(list_peak_wavelength_str,list_peak_Ramanshift_str,list_peak_intensity_str)
            self.sig_drawPlot.emit()
        except Exception as e:
            self.sig_error.emit(str(e))

class Wdg_RamanMeasurement_Peakfinder_Plotter(Ui_spectra_peak_finder, qw.QWidget):
    
    sig_request_plot = Signal(MeaRaman, dict, tuple, bool)
    
    def __init__(self, parent:qw.QWidget):
        """
        Initialises the Raman measurement plotter.
        
        Args:
            parent (QWidget): The parent widget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setLayout(self.main_layout)
        
    # >>> Storage setup <<<
        self._RamanMeasurement:MeaRaman|None = None
        
    # >>> Plotter setup <<<
        self._plotter = MeaRaman_Plotter()
        
        # Plot setup
        self._fig, self._ax = self._plotter.get_fig_ax()
        
        self._fig_canvas = FigureCanvas(figure=self._fig)
        self.lyt_plot.addWidget(self._fig_canvas)
        self._fig_canvas.draw_idle()
        
        self.btn_savePlotPng.clicked.connect(lambda: qw.QMessageBox.information(self,'Info','Not implemented yet.'))
        self.btn_savePlotTxt.clicked.connect(self._save_txt)
        
        # Replot parameters
        self._dict_replot_params = {}
        
    # > Treeview to show the peaks found <
        self.tree_peaks.setColumnCount(3)
        self.tree_peaks.setHeaderLabels(['Wavelength','Raman-shift','Intensity'])
        
    # > Entry widgets for peak finder parameters <
        self._init_entry_widgets_peakfinder()
        self._init_workers_and_signals()
        
    def _init_workers_and_signals(self):
        """
        Initialises the workers and signals for the peak finder plotter.
        """
        # Worker setup
        self._worker_thread = QThread()
        self._worker = PeakFinderPlotter_Worker(self._plotter)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.start(QThread.Priority.LowPriority)
        
        # Signals setup
        self._worker.sig_peaks.connect(self._update_treeview_peaks)
        self._worker.sig_error.connect(self._handle_error)
        self._worker.sig_drawPlot.connect(self._update_plot)
        
        self.sig_request_plot.connect(self._worker.plot_spectra)
        
    @Slot()
    def _update_plot(self):
        """
        Updates the plot.
        """
        self._fig_canvas.draw_idle()
        
    @Slot(list,list,list)
    def _update_treeview_peaks(self,list_wavelength_str:list,list_Ramanshift_str:list,
                               list_intensity_str:list):
        """
        Updates the treeview with the found peaks.
        
        Args:
            list_wavelength_str (list): The list of peak wavelengths as strings
            list_Ramanshift_str (list): The list of peak Raman shifts as strings
            list_intensity_str (list): The list of peak intensities as strings
        """
        self.tree_peaks.clear()
        assert len(list_wavelength_str) == len(list_Ramanshift_str) == len(list_intensity_str),\
            'Error in _update_treeview_peaks: Length of peak lists are not equal.'
        
        for i in range(len(list_wavelength_str)):
            item = qw.QTreeWidgetItem([list_wavelength_str[i],list_Ramanshift_str[i],list_intensity_str[i]])
            self.tree_peaks.addTopLevelItem(item)
        
    @Slot(str)
    def _handle_error(self,error_msg:str): qw.QMessageBox.warning(self,'Error',error_msg)
        
    def _init_entry_widgets_peakfinder(self) -> None:
        """
        Initialises the entry widgets for peak finder parameters.
        """
        self._dict_widgets_peakfinder:Dict[str, qw.QLineEdit] = {}
        lyt = self.lyt_form_parmas
        
        self._peakfinder_options = PeakFinderOptions()
        for i,key in enumerate(asdict(self._peakfinder_options).keys()):
            lbl = qw.QLabel(key,self)
            ent = qw.QLineEdit(self)
            ent.textChanged.connect(self._replot_spectra)
            
            # Place the widgets in the form layout
            lyt.setWidget(i, qw.QFormLayout.LabelRole, lbl) # pyright: ignore[reportAttributeAccessIssue] ; QFormLayout has setWidget method
            lyt.setWidget(i, qw.QFormLayout.FieldRole, ent) # pyright: ignore[reportAttributeAccessIssue] ; QFormLayout has setWidget method
            self._dict_widgets_peakfinder[key] = ent
            
        widgets = get_all_widgets_from_layout(self.lyt_limits)
        [wdg.textChanged.connect(self._replot_spectra) for wdg in widgets if isinstance(wdg,qw.QLineEdit)]
        
    def _get_dict_peakfinder_options(self) -> dict:
        """
        Updates the peak finder options based on the entry widgets.
        
        Returns:
            dict: The updated peak finder options
        """
        dict_options = asdict(self._peakfinder_options)
        dict_options_return = {}
        for key in dict_options.keys():
            val = self._dict_widgets_peakfinder[key].text()
            try: dict_options_return[key] = float(val)
            except: pass
            
        return dict_options_return
        
    @Slot()
    def _save_txt(self):
        """
        Saves the Raman Measurement currently shown in the plot as a text file.
        """
        if not isinstance(self._RamanMeasurement,MeaRaman):
            qw.QMessageBox.warning(self,'Error','No Raman measurement to save.'); return
        
        savepath = qw.QFileDialog.getSaveFileName(self,'Save Raman Measurement as Text File','','Text files (*.txt)')[0]
        
        handler = MeaRaman_Handler()
        handler.save_measurement_to_txt(self._RamanMeasurement,savepath,save_raw=False)
        
    @Slot()
    def _reset_plot_limits(self):
        """
        Resets the plot limits.
        """
        self.ent_xmin.clear()
        self.ent_xmax.clear()
        self.ent_ymin.clear()
        self.ent_ymax.clear()
        
    def _get_plot_limits(self) -> tuple[float|None,float|None,float|None,float|None]:
        """
        Gets the plot limits.
        
        Returns:
            tuple[float|None,float|None,float|None,float|None]: The x-min, x-max, y-min, and y-max
        """
        try: xmin = float(self.ent_xmin.text())
        except: xmin = None
        try: xmax = float(self.ent_xmax.text())
        except: xmax = None
        try: ymin = float(self.ent_ymin.text())
        except: ymin = None
        try: ymax = float(self.ent_ymax.text())
        except: ymax = None
        
        return xmin,xmax,ymin,ymax
        
    @Slot()
    def _replot_spectra(self):
        """
        Replots the Raman spectra based on the last plot parameters (and arguments).
        """
        self.plot_spectra(**self._dict_replot_params)
        
    @Slot(MeaRaman)
    def plot_spectra(self,mea:MeaRaman|None=None) -> None:
        """
        Plots the Raman spectra.
        
        Args:
            mea (RamanMeasurement): The Raman measurement
            mea_id (str): The ID of the Raman measurement for the plot title
        
        Returns:
            tuple[list,list]: The list of peak wavelengths and intensities
        """
        if mea is None: mea = self._RamanMeasurement
        if mea is None: qw.QMessageBox.warning(self,'Error','No Raman measurement to plot.'); return
        
        self._dict_replot_params = {
            'mea': mea,
        }
        
        dict_options = self._get_dict_peakfinder_options()
        limits = self._get_plot_limits()
        flg_RamanShift = self.chk_RamanShift.isChecked()
        
        self.sig_request_plot.emit(mea,dict_options,limits,flg_RamanShift)
        
        
def test():
    """
    Test function for the PeakFinderPlotter.
    """
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    mw = qw.QMainWindow()
    mwdg = Wdg_RamanMeasurement_Peakfinder_Plotter(mw)
    mw.setCentralWidget(mwdg)
    mw.show()
    
    mea = MeaRaman(reconstruct=True)
    mea.test_generate_dummy()
    
    mwdg.plot_spectra(
        mea=mea,
    )
    
    sys.exit(app.exec())
    
if __name__ == '__main__':
    test()