"""
A GUI module to modify the z-coordinates of a mapping coordinates list.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from typing import Literal
import threading
import queue
import math

if __name__ == '__main__':
    import sys
    import os
    libdir = os.path.abspath(r'.\iris')
    sys.path.append(os.path.dirname(libdir))

from iris.gui.motion_video import Frm_MotionController
from iris.data.measurement_coordinates import MeaCoor_mm, List_MeaCoor_Hub

from iris.utils.general import get_all_widgets, messagebox_request_input

class EveryZ(tk.Frame):
    def __init__(
        self,
        parent,
        mappingCoorHub: List_MeaCoor_Hub,
        motion_controller:Frm_MotionController,
        *args, **kwargs) -> None:
        """Initializes the mapping method

        Args:
            parent (tk.Frame): The parent frame to place this widget in
            MappingCoorHub (MappingCoordinatesHub): The hub to store the resulting mapping coordinates in
            getter_MappingCoor (Callable[[], MappingCoordinates_mm]): A function to get the mapping coordinates to modify
            motion_controller (Frm_MotionController): The motion controller to use for the mapping
        """
        super().__init__(parent)
        self._coorHub = mappingCoorHub
        self._motion_controller = motion_controller

    # >>> Top level frame <<<
        self._frm_controls = tk.Frame(self)
        self._frm_controls.grid(row=0, column=0, sticky="nsew")
        frm_instruction = tk.Frame(self._frm_controls)
        frm_mapUnit_selection = tk.Frame(self._frm_controls)
        self._frm_zModification = tk.LabelFrame(self._frm_controls, text='Z-coordinates modifier', padx=5, pady=5)

        row=0; col_curr=0
        frm_instruction.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        frm_mapUnit_selection.grid(row=row, column=0, sticky='nsew', padx=5, pady=5); row+=1
        self._frm_zModification.grid(row=row, column=0, sticky='nsew', padx=5, pady=5)

        self._frm_controls.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

    # >>> Information widget <<<
        btn_instructions = tk.Button(frm_instruction, text='Show instructions', command=self._show_instructions)

        row=0; col_curr=0
        btn_instructions.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

        [frm_instruction.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_instruction.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]

    # >>> Selection widget <<<
        self._combo_mapUnit = ttk.Combobox(frm_mapUnit_selection, state='readonly')
        self._btn_modifyZ = tk.Button(frm_mapUnit_selection, text='Modify Z-coordinates', command=self._run_modify_z_coordinates)

        row=0; col_curr=0
        self._combo_mapUnit.grid(row=row, column=0, sticky='ew', padx=5, pady=5); row+=1
        self._btn_modifyZ.grid(row=row, column=0, sticky='ew', padx=5, pady=5)
        self._btn_surface = tk.Button(frm_mapUnit_selection, text='Hide live 3D surface',
                                      command=self._toggle_surface_plot)
        self._btn_surface.grid(row=row+1, column=0, sticky='ew', padx=5, pady=5)

        [frm_mapUnit_selection.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [frm_mapUnit_selection.grid_columnconfigure(i, weight=1) for i in range(col_curr+1)]

    # >>> Z-coordinates modification widgets <<<
        lbl_coorinfo = tk.Label(self._frm_zModification, text='Coordinates left to review:')
        self._str_coorinfo_val = tk.StringVar(value='N/A')
        lbl_coorinfo_value = tk.Label(self._frm_zModification, textvariable=self._str_coorinfo_val)

        lbl_old_z_coor = tk.Label(self._frm_zModification, text='Old Z-coordinate [μm]:')
        self._str_oldZCoor = tk.StringVar(value='N/A')
        lbl_old_z_value = tk.Label(self._frm_zModification, textvariable=self._str_oldZCoor)

        lbl_previous_z_coor = tk.Label(self._frm_zModification, text='Previous coordinate Z [\u00b5m]:')
        self._str_previousZCoor = tk.StringVar(value='N/A')
        lbl_previous_z_value = tk.Label(self._frm_zModification, textvariable=self._str_previousZCoor)

        lbl_new_z_coor = tk.Label(self._frm_zModification, text='New Z-coordinate [μm]:')
        self._entry_newZCoor = tk.Entry(self._frm_zModification)
        self._btn_currentZCoor = tk.Button(self._frm_zModification, text='Insert current Z-coordinate',\
            command=self._insert_current_z_coordinate)

        self._btn_currentZCoor_commit = tk.Button(self._frm_zModification, text='Insert current Z-coordinate and commit', command=self._insert_and_commit)
        self._btn_commit_modification = tk.Button(self._frm_zModification, text='Commit modification', command=self._commit_modification)
        self._btn_cancel_modification = tk.Button(self._frm_zModification, text='Cancel modification', command=self._cancel_modification)

        self._combo_point = ttk.Combobox(self._frm_zModification, state='disabled', width=45)
        self._combo_point.bind('<<ComboboxSelected>>', self._select_point)
        self._btn_back = tk.Button(self._frm_zModification, text='Back',
                                   command=lambda: self._navigate_point(self._point_index - 1))
        self._btn_forward = tk.Button(self._frm_zModification, text='Forward',
                                      command=lambda: self._navigate_point(self._point_index + 1))
        self._btn_save = tk.Button(self._frm_zModification, text='Save modified coordinates',
                                   command=self._save_modifications)
        self._entry_newZCoor.bind('<Return>', lambda event: self._commit_modification())
        self._entry_newZCoor.bind('<KeyRelease>', self._schedule_surface_update)

        row=0; col_curr=0; col_max=0
        tk.Label(self._frm_zModification, text='Go to coordinate (moves stage):').grid(
            row=row, column=0, sticky='w', padx=5, pady=5)
        self._combo_point.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1
        self._btn_back.grid(row=row, column=0, sticky='ew', padx=5, pady=5)
        self._btn_forward.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1
        lbl_coorinfo.grid(row=row, column=0, sticky='w', padx=5, pady=5); col_curr+=1
        lbl_coorinfo_value.grid(row=row, column=1, sticky='w', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0

        lbl_old_z_coor.grid(row=row, column=0, sticky='w', padx=5, pady=5); col_curr+=1
        lbl_old_z_value.grid(row=row, column=1, sticky='w', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0

        lbl_previous_z_coor.grid(row=row, column=0, sticky='w', padx=5, pady=5)
        lbl_previous_z_value.grid(row=row, column=1, sticky='w', padx=5, pady=5); row+=1

        lbl_new_z_coor.grid(row=row, column=0, sticky='w', padx=5, pady=5); col_curr+=1
        self._entry_newZCoor.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0

        self._btn_currentZCoor.grid(row=row, column=0, sticky='ew', padx=5, pady=5); col_curr+=1
        self._btn_currentZCoor_commit.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1; col_max=max(col_max, col_curr); col_curr=0

        self._btn_commit_modification.grid(row=row, column=0, sticky='ew', padx=5, pady=5); col_curr+=1
        self._btn_cancel_modification.grid(row=row, column=1, sticky='ew', padx=5, pady=5); row+=1
        self._btn_save.grid(row=row, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

        col_max = max(col_max, col_curr)
        [self._frm_zModification.grid_rowconfigure(i, weight=0) for i in range(row+1)]
        [self._frm_zModification.grid_columnconfigure(i, weight=1) for i in range(col_max+1)]

        # Disable the buttons and entry fields initially
        self._reset_zMod_widgets('disabled')

    # >>> Parameters for the mapping coordinates modification <<<
        self._dict_mapUnit = {}  # Dictionary to store mapping units
        self._editing = False
        self._moving = False
        self._point_index = 0
        self._coordinates = []
        self._reviewed = set()
        self._surface_frame = None
        self._surface_visible = False
        self._surface_layout = None
        self._surface_update = None
        self._surface_triangles = None

    # >>> Others <<<
        self._coorHub.add_observer(self._update_list_units)
        self._update_list_units()
        self.bind("<Configure>", self._layout_surface_plot)
        self._show_surface_plot()

    def _insert_current_z_coordinate(self):
        """Inserts the current z-coordinate from the motion controller into the new
        Z-coordinate entry field"""
        current_z_um = self._motion_controller.get_coordinates_closest_mm()[2]*1e3
        self._entry_newZCoor.delete(0, tk.END)
        self._entry_newZCoor.insert(0, f'{current_z_um:.12g}')
        self._update_surface_plot()

    def _show_instructions(self):
        instructions = (
            "This module allows you to modify the z-coordinates of a mapping coordinates list.\n"
            "Select a mapping unit and click Modify Z-coordinates.\n"
            "Enter Z in micrometres or insert the current stage Z, then commit to advance.\n"
            "Use the coordinate dropdown or Back/Forward to revisit points. Navigation saves "
            "the current valid Z edit and moves the stage to the selected XYZ coordinate.\n"
            "Previous coordinate Z shows the latest saved Z for the preceding point in the list.\n"
            "The live 3D surface is embedded beside or below the controls. Use Hide/Show live 3D surface "
            "to make room. Drag the graph to rotate it. Orange shows the selected point "
            "and previews valid Z input; green points are reviewed and grey points are pending. "
            "The connecting surface is a visual interpolation of all points. The title shows the plotted Z range; "
            "the Z axis spans at least 1 micrometre so numerical noise is not exaggerated.\n"
            "Reset stage view restores +X to the right, -Y towards you and +Z downwards.\n"
            "After reviewing every point, click Save modified coordinates to create a named copy. "
            "Cancel discards the edits.\n"
        )
        messagebox.showinfo("Instructions", instructions)

    def _update_list_units(self):
        """Updates the list of mapping units in the combobox"""
        self._dict_mapUnit.clear()  # Clear the existing dictionary
        self._dict_mapUnit = {unit.mappingUnit_name: unit for unit in self._coorHub}

        self._combo_mapUnit.configure(
            values=list(self._dict_mapUnit.keys()),
            state='disabled' if self._editing else 'readonly'
        )

    def _reset_zMod_widgets(self,state:Literal['normal', 'disabled']):
        """Resets the widgets in the z-coordinates modification frame to the given state
        Args:
            state (Literal['normal', 'disabled']): The state to set the widgets to
        """
        assert state in ['normal', 'disabled'], f"Invalid state: {state}"
        [widget.configure(state=state) for widget in get_all_widgets(self._frm_zModification) if isinstance(widget, (tk.Button, tk.Entry))]

    def _run_modify_z_coordinates(self):
        """Start an editable copy; all UI callbacks remain on the Tk thread."""
        if self._editing:
            return
        name = self._combo_mapUnit.get()
        coordinates = self._dict_mapUnit.get(name)
        if not name:
            messagebox.showwarning('Warning', 'Please select a mapping unit to modify.')
            return
        if not isinstance(coordinates, MeaCoor_mm):
            messagebox.showerror('Error', 'Invalid mapping coordinates selection.')
            return
        if not coordinates.mapping_coordinates:
            messagebox.showwarning('Warning', 'The selected mapping unit has no coordinates.')
            return
        self._source_name = name
        self._coordinates = coordinates.mapping_coordinates.copy()
        self._surface_triangles = None
        self._reviewed = set()
        self._editing = True
        self._btn_modifyZ.configure(state='disabled')
        self._combo_mapUnit.configure(state='disabled')
        self._show_point(0)

    def _update_point_controls(self):
        active = self._editing and not self._moving
        self._reset_zMod_widgets('normal' if active else 'disabled')
        self._combo_point.configure(state='readonly' if active else 'disabled')
        self._btn_back.configure(state='normal' if active and self._point_index > 0 else 'disabled')
        self._btn_forward.configure(state='normal' if active and self._point_index < len(self._coordinates)-1 else 'disabled')
        self._btn_save.configure(state='normal' if active and len(self._reviewed) == len(self._coordinates) else 'disabled')
        self._str_coorinfo_val.set(f'{len(self._coordinates)-len(self._reviewed)}/{len(self._coordinates)}')
        self._combo_point.configure(values=[
            f'{i+1}: X={x:.6g}, Y={y:.6g}, Z={z:.6g} mm'
            + (' (reviewed)' if i in self._reviewed else '')
            for i, (x, y, z) in enumerate(self._coordinates)
        ])
        self._combo_point.current(self._point_index)

    def _store_current_point(self):
        try:
            text = self._entry_newZCoor.get().strip()
            entered_um = float(text)
            x, y, saved_z = self._coordinates[self._point_index]
            # Keep full file precision when accepting the displayed, rounded value.
            z = saved_z if text == f'{saved_z*1e3:.12g}' else entered_um * 1e-3
            if not math.isfinite(z):
                raise ValueError('Z must be a finite number')
            if not self._motion_controller.check_coordinates((x, y, z)):
                raise ValueError("Out of the stage's travel range")
        except Exception as error:
            messagebox.showerror('Error', f'Invalid input for new Z-coordinate: {error}')
            return False
        self._coordinates[self._point_index] = (x, y, z)
        self._reviewed.add(self._point_index)
        self._update_point_controls()
        self._update_surface_plot()
        return True

    def _show_point(self, index):
        self._point_index = index
        x, y, z = self._coordinates[index]
        self._str_oldZCoor.set(f'{z*1e3:.12g}')
        self._str_previousZCoor.set(
            f'{self._coordinates[index-1][2]*1e3:.12g}' if index > 0 else 'N/A')
        self._entry_newZCoor.configure(state='normal')
        self._entry_newZCoor.delete(0, tk.END)
        self._entry_newZCoor.insert(0, f'{z*1e3:.12g}')
        self._update_surface_plot()
        self._moving = True
        self._update_point_controls()
        result = queue.Queue()

        def move():
            try:
                self._motion_controller.go_to_coordinates(coor_x_mm=x, coor_y_mm=y, coor_z_mm=z)
            except Exception as error:
                result.put(error)
            else:
                result.put(None)

        threading.Thread(target=move, daemon=True).start()
        self.after(50, self._poll_point_move, result)

    def _poll_point_move(self, result):
        try:
            error = result.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_point_move, result)
            return
        self._moving = False
        if error is not None:
            # Do not allow a commit at a point the stage failed to reach.
            self._end_modification()
            messagebox.showerror('Stage movement failed', str(error))
            return
        self._update_point_controls()

    def _navigate_point(self, index):
        if not self._editing or self._moving:
            return
        if not 0 <= index < len(self._coordinates) or index == self._point_index:
            self._combo_point.current(self._point_index)
            return
        if not self._store_current_point():
            self._combo_point.current(self._point_index)
            return
        self._show_point(index)

    def _select_point(self, event=None):
        self._navigate_point(self._combo_point.current())

    def _commit_modification(self):
        if not self._editing or self._moving or not self._store_current_point():
            return
        if self._point_index + 1 < len(self._coordinates):
            self._show_point(self._point_index + 1)

    def _insert_and_commit(self):
        if self._editing and not self._moving:
            self._insert_current_z_coordinate()
            self._commit_modification()

    def _save_modifications(self):
        if not self._editing or self._moving or not self._store_current_point():
            return
        if len(self._reviewed) != len(self._coordinates):
            messagebox.showwarning('Review coordinates', 'Please review every coordinate before saving.')
            return
        new_name = messagebox_request_input(
            'New Mapping Unit Name', 'Please enter a new name for the modified mapping coordinates:',
            default=f'{self._source_name}_z modified')
        if not new_name:
            return
        try:
            self._coorHub.append(MeaCoor_mm(new_name, self._coordinates.copy()))
        except Exception as error:
            messagebox.showerror('Error', f'Failed to add new mapping coordinates: {error}')
            return
        self._end_modification(keep_surface=True)
        messagebox.showinfo('Success', 'Z-coordinates modified successfully.')

    def _cancel_modification(self):
        if self._editing and not self._moving:
            self._end_modification()
            messagebox.showinfo('Cancelled', 'Z-coordinates modification cancelled.')

    def _end_modification(self, keep_surface=False):
        self._editing = False
        self._reset_zMod_widgets('disabled')
        self._combo_point.configure(state='disabled')
        self._combo_mapUnit.configure(state='readonly')
        self._btn_modifyZ.configure(state='normal')
        self._str_coorinfo_val.set('N/A')
        self._str_previousZCoor.set('N/A')
        if not keep_surface:
            self._coordinates = []
        self._update_surface_plot()

    def _show_surface_plot(self):
        """Show the embedded plot, keeping its camera when hidden and restored."""
        if self._surface_frame is None:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

            self._surface_frame = tk.LabelFrame(self, text='Live Z surface', padx=5, pady=5)
            self._btn_surface_reset = tk.Button(self._surface_frame, text='Reset stage view',
                                                command=self._reset_surface_view)
            self._btn_surface_reset.pack(side=tk.TOP, anchor='e', pady=(0, 4))
            figure = Figure(figsize=(3.8, 3.2), layout='constrained')
            self._surface_ax = figure.add_subplot(111, projection='3d')
            self._surface_canvas = FigureCanvasTkAgg(figure, master=self._surface_frame)
            # Hover coordinates must not change the parent window's requested size.
            toolbar_container = tk.Frame(self._surface_frame, width=1, height=50)
            toolbar_container.pack(side=tk.BOTTOM, fill=tk.X)
            toolbar_container.pack_propagate(False)
            self._surface_toolbar = NavigationToolbar2Tk(
                self._surface_canvas, toolbar_container, pack_toolbar=False)
            self._surface_toolbar.pack(fill=tk.BOTH, expand=True)
            toolbar_container.update_idletasks()
            toolbar_container.configure(height=self._surface_toolbar.winfo_reqheight())
            self._surface_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            self._reset_surface_view()
        self._surface_visible = True
        self._btn_surface.configure(text='Hide live 3D surface')
        self._surface_layout = None
        self._layout_surface_plot()
        self._update_surface_plot()

    def _reset_surface_view(self):
        """Look from the negative Y side: +X right, -Y towards us, +Z down."""
        self._surface_ax.view_init(elev=30, azim=-90, roll=0)
        self._update_surface_plot()

    def _hide_surface_plot(self):
        self._surface_visible = False
        self._surface_frame.grid_remove()
        self._btn_surface.configure(text='Show live 3D surface')
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self._surface_layout = None

    def _toggle_surface_plot(self):
        if self._surface_visible:
            self._hide_surface_plot()
        else:
            self._show_surface_plot()

    def _layout_surface_plot(self, event=None):
        if event is not None and event.widget is not self:
            return
        if not self._surface_visible:
            return
        width = event.width if event is not None else self.winfo_width()
        # Before Tk has allocated space, request a compact horizontal layout.
        threshold = self._frm_controls.winfo_reqwidth() + 400
        # Avoid flipping layouts repeatedly near the breakpoint during resizing.
        if self._surface_layout == 'side':
            threshold -= 20
        elif self._surface_layout == 'below':
            threshold += 20
        side_by_side = width <= 1 or width >= threshold
        layout = 'side' if side_by_side else 'below'
        if layout == self._surface_layout:
            return
        self._surface_layout = layout
        self._surface_frame.grid(row=0 if side_by_side else 1,
                                 column=1 if side_by_side else 0, sticky='nsew', padx=5, pady=5)
        self.grid_columnconfigure(0, weight=0 if side_by_side else 1)
        self.grid_columnconfigure(1, weight=1 if side_by_side else 0)
        self.grid_rowconfigure(0, weight=1 if side_by_side else 0)
        self.grid_rowconfigure(1, weight=0 if side_by_side else 1)

    def destroy(self):
        if self._surface_update is not None:
            self.after_cancel(self._surface_update)
            self._surface_update = None
        if self._surface_frame is not None:
            # Cancel Matplotlib's queued redraw before destroying its Tk widget.
            if self._surface_canvas._idle_draw_id is not None:
                self._surface_canvas.get_tk_widget().after_cancel(self._surface_canvas._idle_draw_id)
                self._surface_canvas._idle_draw_id = None
        super().destroy()

    def _schedule_surface_update(self, event=None):
        if self._surface_update is not None:
            self.after_cancel(self._surface_update)
        self._surface_update = self.after(150, self._update_surface_plot)

    def _update_surface_plot(self):
        """Render accepted coordinates, with a separate unsaved entry preview."""
        if self._surface_update is not None:
            self.after_cancel(self._surface_update)
            self._surface_update = None
        if not self._surface_visible:
            return
        import numpy as np
        from matplotlib.tri import Triangulation

        ax = self._surface_ax
        # Preserve the user's rotation while the data changes.
        elevation, azimuth, roll = ax.elev, ax.azim, ax.roll
        ax.clear()
        ax.view_init(elev=elevation, azim=azimuth, roll=roll)
        ax.set_xlabel('X [mm]')
        ax.set_ylabel('Y [mm]')
        ax.set_zlabel('Z [\u00b5m]')
        ax.zaxis.set_inverted(True)
        if not self._coordinates:
            ax.set_title('Start modifying coordinates to view the surface')
            self._surface_canvas.draw_idle()
            return

        points = np.array(self._coordinates, dtype=float)
        points[:, 2] *= 1e3
        preview = False
        invalid = False
        if self._editing:
            try:
                text = self._entry_newZCoor.get().strip()
                z = float(text)
                if not math.isfinite(z):
                    raise ValueError('Non-finite Z')
                saved_um = points[self._point_index, 2]
                preview = (text != f'{saved_um:.12g}'
                           and not math.isclose(z, saved_um, rel_tol=1e-14, abs_tol=1e-10))
                if preview:
                    points[self._point_index, 2] = z
            except ValueError:
                invalid = True
        finite = np.isfinite(points).all(axis=1)
        surface = False
        # Triangulation is cached because only Z changes during an edit session.
        if self._surface_triangles is None:
            self._surface_triangles = False
            xy = points[:, :2]
            if (finite.all() and len(points) >= 3
                    and len(np.unique(xy, axis=0)) == len(points)
                    and np.linalg.matrix_rank(xy - xy[0]) == 2):
                try:
                    self._surface_triangles = Triangulation(xy[:, 0], xy[:, 1]).triangles
                except (ValueError, RuntimeError):
                    pass
        if self._surface_triangles is not False and finite.all():
            ax.plot_trisurf(points[:, 0], points[:, 1], points[:, 2],
                            triangles=self._surface_triangles, cmap='viridis', alpha=.45,
                            linewidth=.3, edgecolor='grey')
            surface = True
        for reviewed, color, label in ((False, 'grey', 'Pending'), (True, 'seagreen', 'Reviewed')):
            mask = np.array([i in self._reviewed for i in range(len(points))]) == reviewed
            mask &= finite
            if mask.any():
                ax.scatter(*points[mask].T, color=color, s=30, depthshade=False, label=label)
        if self._editing and finite[self._point_index]:
            ax.scatter(*points[self._point_index], color='darkorange', edgecolor='black',
                       s=100, depthshade=False, label='Selected (preview)' if preview else 'Selected')
        title = f'{self._source_name}: {len(self._reviewed)}/{len(points)} reviewed'
        if finite.any():
            z_min, z_max = points[finite, 2].min(), points[finite, 2].max()
            # A tiny numerical difference must not become a dramatic apparent slope.
            center = (z_min + z_max) / 2
            half_span = max((z_max-z_min)*.55, .5)
            ax.set_zlim(center+half_span, center-half_span)
            title += f'\nZ range: {z_min:.9g} to {z_max:.9g} \u00b5m'
        if invalid:
            title += '\nInvalid Z input; showing accepted value'
        elif preview:
            title += '\nPreview; commit or navigate to accept'
        if not surface:
            title += '\nPoints only: surface needs distinct, non-collinear XY positions'
        ax.set_title(title, fontsize=9)
        if finite.any():
            ax.legend(loc='upper left', fontsize='small')
        self._surface_canvas.draw_idle()


def test():
    from iris.gui.motion_video import generate_dummy_motion_controller

    root = tk.Tk()
    root.title('Test')

    frm_motion = generate_dummy_motion_controller(root)
    frm_motion.initialise_auto_updater()
    frm_motion.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

    coorUnit = MeaCoor_mm(
        mappingUnit_name='Test Mapping Unit',
        mapping_coordinates=[(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3)]
    )

    coorHub = List_MeaCoor_Hub()
    coorHub.append(coorUnit)

    frm_coor_mod = EveryZ(
        root,
        mappingCoorHub=coorHub,
        motion_controller=frm_motion,
    )

    frm_coor_mod.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

    root.mainloop()

if __name__ == '__main__':
    test()
