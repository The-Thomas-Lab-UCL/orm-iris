"""
A GUI to visualize the topology of a mapping coordinates
"""
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from typing import Literal

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.colorbar import Colorbar
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub
from iris.utils.general import *

from iris.gui import AppPlotEnum

class TopologyVisualizer(tk.Frame):
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        *args, **kwargs) -> None:
        """Initializes the mapping method
        
        Args:
            parent (tk.Frame): The parent frame to place this widget in
            MappingCoorHub (MappingCoordinatesHub): The hub to store the resulting mapping coordinates in
            getter_MappingCoor (Callable[[], MappingCoordinates_mm]): A function to get the mapping coordinates to modify
        """
        super().__init__(parent)
        self._coorHub = mappingCoorHub
        
    # >>> Top level frame <<<
        frm_instruction = tk.Frame(self)
        frm_mapUnit_selection = tk.Frame(self)
        frm_plot = tk.Frame(self)
        frm_plot_params = tk.Frame(self)
        
        row=0; col_curr=0
        frm_instruction.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_mapUnit_selection.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_plot_params.grid(row=row, column=0, sticky='nsew', padx=5, pady=5)
        
        frm_plot.grid(row=0, column=1, sticky='nsew', padx=5, pady=5, rowspan=row+1)
         
        
        [self.grid_rowconfigure(i, weight=1) for i in range(row+1)]
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
    # >>> Information widget <<<
        btn_instructions = tk.Button(frm_instruction, text='Show instructions', command=self._show_instructions)
        
        row=0; col_curr=0
        btn_instructions.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        [frm_instruction.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_instruction.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Plotting parameters and widget <<<
        self._figsize_pxl = AppPlotEnum.PLT_MAP_SIZE_PIXEL.value
        self._dpi = plt.rcParams['figure.dpi']
        self._figsize_in = (self._figsize_pxl[1]/self._dpi,self._figsize_pxl[0]/self._dpi)
        self._fig, self._ax = plt.subplots(figsize=self._figsize_in)
        self._plt_canvas = FigureCanvasTkAgg(self._fig, master=frm_plot)
        self._plt_widget = self._plt_canvas.get_tk_widget()
        self._plt_canvas.draw()
        
        self._plt_widget.grid(row=0, column=0, sticky='nsew')
        frm_plot.grid_rowconfigure(0, weight=1)
        frm_plot.grid_columnconfigure(0, weight=1)
        
        # Typehinting
        self._fig: Figure
        self._ax: Axes
        self._cbar: Colorbar = None
        
    # >>> Selection widget <<<
        lbl_mapUnit_source = tk.Label(frm_mapUnit_selection, text='Select the mapping coordinates to visualise its topology:')
        self._combo_mapUnit_source = ttk.Combobox(frm_mapUnit_selection, state='readonly')
        self._combo_mapUnit_source.bind('<<ComboboxSelected>>', lambda e: self._show_topology())
        
        row=0; col_curr=0
        lbl_mapUnit_source.grid(row=row, column=0, sticky='w', padx=5, pady=5); row+=1
        self._combo_mapUnit_source.grid(row=row, column=0, sticky='ew', padx=5, pady=5); row+=1
        
        [frm_mapUnit_selection.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_mapUnit_selection.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]
        
    # >>> Plot parameter widgets <<<
        self._bool_edge = tk.BooleanVar(value=True)  # Whether to show the edges of the triangles
        self._chk_edge = tk.Checkbutton(frm_plot_params,text='Show edges',variable=self._bool_edge, command=self._show_topology)
        
        self._chk_edge.grid(row=0, column=0, sticky='w', padx=5, pady=5)
        
        frm_plot_params.grid_rowconfigure(0, weight=0)
        frm_plot_params.grid_columnconfigure(0, weight=1)
        
    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        self._thread_plot:threading.Thread = None  # Thread for plotting the topology
        
    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()
        
    def _show_instructions(self):
        instructions = (
            "This module allows you to modify the z-coordinates of a mapping coordinates list.\n"
            "TODO: Add instructions on how to use this module.\n"
        )
        messagebox.showinfo("Instructions", instructions)
    
    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}
        
        self._combo_mapUnit_source.configure(
            values=list(self._dict_mapUnit.keys()),
            state='readonly'
        )
        
    @thread_assign
    def _show_topology(self):
        """Shows the topology of the selected mapping coordinates"""
        selected_unit_name = self._combo_mapUnit_source.get()
        if not selected_unit_name:
            messagebox.showwarning("Warning", "Please select a mapping unit.")
            return
        
        selected_unit = self._dict_mapUnit.get(selected_unit_name)
        if not selected_unit:
            messagebox.showerror("Error", "Selected mapping unit not found.")
            return
        
        if len(selected_unit.mapping_coordinates) < 2:
            messagebox.showwarning('Warning', 'Not enough coordinates to plot topology. Please select a unit with at least 2 coordinates.')
            return
        
        if isinstance(self._thread_plot, threading.Thread) and self._thread_plot.is_alive():
            messagebox.showwarning('Warning', 'A topology plot is already in progress. Please wait for it to finish.')
            return
        
        self._thread_plot = threading.Thread(
            target=self._plot_topology,
            args=(selected_unit,),
            daemon=True
        )
        self._thread_plot.start()
        
    def _plot_topology(self, mapping_coordinates: MeaCoor_mm):
        # Disable the widgets during plotting
        self._combo_mapUnit_source.configure(state='disabled')
        self._chk_edge.configure(state='disabled')
        
        # Clear the current plot
        try:
            self._cbar.remove()
            self._ax.clear()
        except: pass
        
        # Plot the coordinates
        x, y, z = zip(*mapping_coordinates.mapping_coordinates)
        self._ax.tripcolor(
            x, y, z,
            cmap=AppPlotEnum.PLT_COLOUR_MAP.value,
            shading=AppPlotEnum.PLT_SHADING.value,
            edgecolors='k' if self._bool_edge.get() else 'none',
            vmin=min(z),
            vmax=max(z),
        )
        
        self._ax.set_aspect('equal', adjustable='box')
        self._ax.set_title(f"Topology of {mapping_coordinates.mappingUnit_name} [mm]")
        self._ax.set_xlabel('X Coordinate (mm)')
        self._ax.set_ylabel('Y Coordinate (mm)')
        self._cbar = self._fig.colorbar(self._ax.collections[0], ax=self._ax)
        self._cbar.set_label('Z Coordinate (mm)', rotation=270, labelpad=15)
        
        # Redraw the canvas
        self._plt_canvas.draw()
        
        # Re-enable the widgets
        self._combo_mapUnit_source.configure(state='readonly')
        self._chk_edge.configure(state='normal')
        
def test():
    from iris.gui.motion_video import generate_dummy_motion_controller
    
    root = tk.Tk()
    root.title('Test')
    
    frm_motion = generate_dummy_motion_controller(root)
    frm_motion.initialise_auto_updater()
    frm_motion.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
    
    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[
            (0, 0, 0),
            (1, 0, 1),
            (2, 0, 2),
            (0, 1, 1),
            (1, 1, 2),
            (2, 1, 3),
            (0, 2, 2),
            (1, 2, 3),
            (2, 2, 4),
        ]
    )
    
    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)
    
    frm_coor_mod = TopologyVisualizer(
        root,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )
    
    frm_coor_mod.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)
    
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    
    root.mainloop()
    
if __name__ == '__main__':
    test()