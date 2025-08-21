import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

from scipy.signal import find_peaks
import bisect

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
matplotlib.use('Agg')   # Force matplotlib to use the backend to prevent memory leak


from iris.utils.general import *

from iris.data.measurement_Raman import MeaRaman, MeaRaman_Plotter, MeaRaman_Handler

class Frm_RamanMeasurement_Plotter(tk.Frame):
    def __init__(self, master,tree_columnWidth:int=400,height:int=400):
        """
        Initialises the Raman measurement plotter.
        
        Args:
            master (tk.Tk): The master window
        """
        super().__init__(master)
        self._master:tk.Tk = master
        
    # >>> Frame setup <<<
        # > Top layout <
        self._frm_plot = tk.Frame(self)
        self._frm_control = tk.Frame(self)
        
        self._frm_plot.grid(row=0,column=0,sticky='nsew')
        self._frm_control.grid(row=1,column=0,sticky='nsew')
        
        self.grid_rowconfigure(0,weight=1)
        self.grid_rowconfigure(1,weight=1)
        self.grid_columnconfigure(0,weight=1)
        
        # > Subframes <
        self._sfrm_plotcontrol = tk.Frame(self._frm_control)
        self._sfrm_peakfindercontrol = tk.Frame(self._frm_control)
        
        self._sfrm_plotcontrol.grid(row=0,column=0,sticky='nsew')
        self._sfrm_peakfindercontrol.grid(row=1,column=0,sticky='nsew')
        
        self.grid_rowconfigure(0,weight=1)
        self.grid_rowconfigure(1,weight=1)
        self.grid_columnconfigure(0,weight=1)
        
    # >>> Storage setup <<<
        self._RamanMeasurement:MeaRaman|None = None
        self._RamanMeasurement_id:str = ''
        
    # >>> Plotter setup <<<
        self._plotter = MeaRaman_Plotter()
        self._plt_size_pxl = (tree_columnWidth,height)
        dpi = matplotlib.rcParams['figure.dpi']
        self._plt_size_in = (int(self._plt_size_pxl[0]/dpi),int(self._plt_size_pxl[1]/dpi))
        
        # Plot setup
        self._fig:Figure = None
        self._ax:Axes = None
        self._fig_canvas:FigureCanvasTkAgg = None
        self._widget_canvas:tk.Canvas = None
        self._reinit_plot(0,0)
        tk.Button(self._frm_plot,text='Reinitialise plot',command=self._reinit_plot).grid(row=1,column=0,sticky='ew')
        tk.Button(self._frm_plot,text='Save plot data (.txt)',command= self._save_txt).grid(row=1,column=1,sticky='ew')
        
    # >>> Plotter control setup <<<
        # x and y limits
        lbl_xmin = tk.Label(self._sfrm_plotcontrol,text='x-min: ')
        lbl_xmax = tk.Label(self._sfrm_plotcontrol,text='x-max: ')
        lbl_ymin = tk.Label(self._sfrm_plotcontrol,text='y-min: ')
        lbl_ymax = tk.Label(self._sfrm_plotcontrol,text='y-max: ')
        self._entry_xmin = tk.Entry(self._sfrm_plotcontrol)
        self._entry_xmax = tk.Entry(self._sfrm_plotcontrol)
        self._entry_ymin = tk.Entry(self._sfrm_plotcontrol)
        self._entry_ymax = tk.Entry(self._sfrm_plotcontrol)
        btn_reset = tk.Button(self._sfrm_plotcontrol,text='Reset plot',command=lambda: self._reset_plot_limits())
        
        lbl_xmin.grid(row=0,column=0)
        lbl_xmax.grid(row=0,column=2)
        lbl_ymin.grid(row=1,column=0)
        lbl_ymax.grid(row=1,column=2)
        
        self._entry_xmin.grid(row=0,column=1)
        self._entry_xmax.grid(row=0,column=3)
        self._entry_ymin.grid(row=1,column=1)
        self._entry_ymax.grid(row=1,column=3)
        
        btn_reset.grid(row=0,column=4,rowspan=2)
        
        [widget.bind('<Return>',lambda event: self._replot_spectra())\
            for widget in self._sfrm_plotcontrol.winfo_children() if isinstance(widget,tk.Entry)] 
        
        # Replot parameters
        self._dict_replot_params = {}
        
    # >>> Peak finder setup <<<
        self._peakfinder_params = {
            'height': None,
            'threshold': None,
            'distance': None,
            'prominence': None,
            'width': None,
            'wlen': None,
            'rel_height': None,
            'plateau_size': None
        }
        # Widgets setup
        self._dict_peakfinder_widgets = {}
        row=1
        for key in self._peakfinder_params.keys():
            tk.Label(self._sfrm_peakfindercontrol,text=key).grid(row=row,column=0,sticky='e')
            entry = tk.Entry(self._sfrm_peakfindercontrol)
            self._dict_peakfinder_widgets[key] = entry
            entry.grid(row=row,column=1,sticky='w')
            entry.bind('<Return>',lambda event: self.plot_spectra())
            row+=1
        tk.Button(self._sfrm_peakfindercontrol,text='Plot',command=self.plot_spectra).grid(row=row,column=0,columnspan=2,sticky='ew')
        
    # > Treeview to show the peaks found <
        frm_tree = tk.LabelFrame(self._sfrm_peakfindercontrol,text='Peaks found')
        frm_tree.grid(row=0,column=2,rowspan=row+1,sticky='nsew',pady=5,padx=5)
        frm_tree.grid_rowconfigure(0,weight=1)
        frm_tree.grid_columnconfigure(2,weight=1)
        
        self._tree_peakfinder = ttk.Treeview(frm_tree,columns=('wavelength','ramanshift','intensity'),
                                             show='headings',selectmode='browse')
        tree_columnWidth = 100
        self._tree_peakfinder.heading('wavelength',text='Wavelength',anchor='w')
        self._tree_peakfinder.heading('ramanshift',text='Raman shift',anchor='w')
        self._tree_peakfinder.heading('intensity',text='Intensity',anchor='w')
        self._tree_peakfinder.column('wavelength',width=tree_columnWidth,anchor='w')
        self._tree_peakfinder.column('ramanshift',width=tree_columnWidth,anchor='w')
        self._tree_peakfinder.column('intensity',width=tree_columnWidth,anchor='w')
        self._tree_peakfinder.grid(row=0,column=0,sticky='nsew')

        
        for row in range(0,row+1):
            self._sfrm_peakfindercontrol.grid_rowconfigure(row,weight=1)
        self._sfrm_peakfindercontrol.grid_columnconfigure(2,weight=1)
        
    # >>> Controller setup <<<
        self._bool_Ramanshift = tk.BooleanVar(value=True)
        self._chk_Ramanshift = tk.Checkbutton(self._sfrm_peakfindercontrol,text='Plot Raman shift',variable=self._bool_Ramanshift,
                                              command=self.plot_spectra)
        
        self._chk_Ramanshift.grid(row=0,column=0,sticky='w')
        
    def _save_txt(self):
        """
        Saves the Raman Measurement currently shown in the plot as a text file.
        """
        if not isinstance(self._RamanMeasurement,MeaRaman): messagebox.showerror('Error','No Raman measurement to save.'); return
        
        savepath = filedialog.asksaveasfilename(defaultextension='.txt',filetypes=[('Text file','*.txt')])
        
        handler = MeaRaman_Handler()
        handler.save_measurement_to_txt(self._RamanMeasurement,savepath,save_raw=False)
        
    def _reinit_plot(self,plot_row:int=0,plot_col:int=0,colspan:int=2):
        """
        Reinitialises the plot.
        
        Args:
            plot_row (int): The row to plot the figure. Default is 0.
            plot_col (int): The column to plot the figure. Default is 0.
            colspan (int): The number of columns to span. Default is 2.
        """
        self._fig, self._ax = plt.subplots(1,1,figsize=self._plt_size_in)
        self._fig_canvas = FigureCanvasTkAgg(self._fig,master=self._frm_plot)
        self._widget_canvas = self._fig_canvas.get_tk_widget()
        self._widget_canvas.grid(row=plot_row,column=plot_col,sticky='nsew',columnspan=colspan)
        
    def _reset_plot_limits(self):
        """
        Resets the plot limits.
        """
        self._entry_xmin.delete(0,'end')
        self._entry_xmax.delete(0,'end')
        self._entry_ymin.delete(0,'end')
        self._entry_ymax.delete(0,'end')
        
        try: self._replot_spectra()
        except Exception as e: print('_reset_plot_limits -> _replot_spectra:',e)
        
    def _get_plot_limits(self) -> tuple[float,float,float,float]:
        """
        Gets the plot limits.
        
        Returns:
            tuple[float,float,float,float]: The x-min, x-max, y-min, and y-max
        """
        try: xmin = float(self._entry_xmin.get())
        except: xmin = None
        try: xmax = float(self._entry_xmax.get())
        except: xmax = None
        try: ymin = float(self._entry_ymin.get())
        except: ymin = None
        try: ymax = float(self._entry_ymax.get())
        except: ymax = None
        
        return xmin,xmax,ymin,ymax
        
    def _replot_spectra(self):
        """
        Replots the Raman spectra based on the last plot parameters (and arguments).
        """
        try: self.plot_spectra(**self._dict_replot_params)
        except Exception as e: print('_replot_spectra:',e)
        
    def plot_spectra(self,mea:MeaRaman|None=None,mea_id:str|None=None) -> tuple[list,list]:
        """
        Plots the Raman spectra.
        
        Args:
            mea (RamanMeasurement): The Raman measurement
            mea_id (str): The ID of the Raman measurement for the plot title
        
        Returns:
            tuple[list,list]: The list of peak wavelengths and intensities
        """
        if mea is None: mea = self._RamanMeasurement
        if mea_id is None: mea_id = self._RamanMeasurement_id
        if mea is None: return
        
        self._dict_replot_params = {
            'mea': mea,
            'mea_id': mea_id
        }
        
        list_wavelength = mea.get_measurements()[-1][mea.label_wavelength]
        # list_ramanshift = [convert_wavelength_to_ramanshift(wavelength,mea.get_laser_params()[1]) for wavelength in list_wavelength]
        list_intensity = mea.get_measurements()[-1][mea.label_intensity]
        
        # # Slice the data
        # try:
        #     limits = self._get_plot_limits()
        #     list_spec_pos = list_ramanshift if self._bool_Ramanshift.get() else list_wavelength
        #     if limits[0] is not None: idx_min = bisect.bisect_left(list_spec_pos,limits[0])
        #     else: idx_min = 0
        #     if limits[1] is not None: idx_max = bisect.bisect_right(list_spec_pos,limits[1])
        #     else: idx_max = len(list_spec_pos)
        #     list_wavelength = list_wavelength[idx_min:idx_max]
        #     list_intensity = list_intensity[idx_min:idx_max]
        # except Exception as e: print('plot_spectra 1:',e)
        
        try:
            options = {key:float(self._dict_peakfinder_widgets[key].get()) for key in self._peakfinder_params.keys() if self._dict_peakfinder_widgets[key].get() != ''}
            peaks_idx = find_peaks(list_intensity,**options)[0]
            peak_wavelength = [list_wavelength[i] for i in peaks_idx]
            peak_intensity = [list_intensity[i] for i in peaks_idx]
            
            laser_wavelength = mea.get_laser_params()[1]
            peak_Ramanshift_str = ['{:3f}'.format(convert_wavelength_to_ramanshift(wavelength,laser_wavelength)) for wavelength in peak_wavelength]
            peak_intensity_str = ['{:3f}'.format(list_intensity[i]) for i in peaks_idx]
            peak_wavelength_str = ['{:3f}'.format(list_wavelength[i]) for i in peaks_idx]
            
            # Update the treeview
            self._tree_peakfinder.delete(*self._tree_peakfinder.get_children())
            for i in range(len(peak_wavelength)):
                self._tree_peakfinder.insert('','end',values=(peak_wavelength_str[i],peak_Ramanshift_str[i],peak_intensity_str[i]))
        except Exception as e:
            print('plot_spectra 1:',e)
            peak_wavelength = []
            peak_intensity = []
        
        try:
            limits = self._get_plot_limits()
            self._fig, self._ax = self._plotter.plot_with_scatter_RamanMeasurement(
                measurement=mea,
                spectralabel=mea_id,
                title='Raman spectra of {}'.format(mea_id),
                list_scatter_wavelength=peak_wavelength,
                list_scatter_intensity=peak_intensity,
                scatterlabel='Peaks',
                plt_size=self._plt_size_in,
                flg_plot_ramanshift=self._bool_Ramanshift.get(),
                fig=self._fig,
                ax=self._ax,
                limits=limits,
            )   
            self._fig_canvas.draw()
            
            self._RamanMeasurement = mea
            self._RamanMeasurement_id = mea_id
            return peak_wavelength,peak_intensity
        except Exception as e: print('plot_spectra 2:',e); return [],[]