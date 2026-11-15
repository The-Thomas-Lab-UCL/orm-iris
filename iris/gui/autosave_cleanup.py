"""Manual selection and cleanup of inactive IRIS recovery copies."""
from datetime import datetime, timezone
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from iris.utils.autosave_storage import GIB, list_recovery_runs, delete_recovery_run, disk_capacity


def _work(result, root, active, names=None):
    """Workers hold no Tk objects and perform no Tk calls."""
    try:
        if names is None:
            result.put(('listed', (list_recovery_runs(root, active), disk_capacity(root))))
        else:
            removed, size, failures = 0, 0, []
            for name in names:
                try:
                    size += delete_recovery_run(root, name, active)
                    removed += 1
                except (OSError, ValueError) as error:
                    failures.append(f'{name}: {error}')
            result.put(('deleted', (removed, size, failures)))
    except Exception as error:
        result.put(('error', str(error)))


class AutosaveCleanup(tk.Toplevel):
    def __init__(self, parent, folder, active_paths):
        super().__init__(parent)
        self.title('Manage autosave recovery copies')
        self.geometry('960x520')
        self.transient(parent.winfo_toplevel())
        self._folder = Path(folder).resolve()
        self._active_paths = active_paths
        self._result = queue.Queue()
        self._poll_id = None
        self._busy = False
        self._runs = {}
        self._last_action = ''
        self._status = tk.StringVar(value='Loading recovery runs...')
        self._space = tk.StringVar(value='')
        tk.Label(self, text=str(self._folder), anchor='w', wraplength=920).pack(fill=tk.X, padx=10, pady=5)
        tk.Label(self, text='Select recovery copies using Ctrl/Shift. Verify your exported dataset reopens before deleting.\n'
                 'No automatic deletion. Exported files and active/finishing runs are protected.',
                 anchor='w', justify=tk.LEFT).pack(fill=tk.X, padx=10, pady=5)
        tk.Label(self, textvariable=self._space, anchor='w').pack(fill=tk.X, padx=10)
        container = tk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._tree = ttk.Treeview(container, columns=('name', 'modified', 'size', 'status'),
                                  show='headings', selectmode='extended')
        for name, title, width in (('name', 'Recovery run', 280), ('modified', 'Modified (UTC)', 150),
                                   ('size', 'Size', 100), ('status', 'Status', 300)):
            self._tree.heading(name, text=title)
            self._tree.column(name, width=width)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.bind('<<TreeviewSelect>>', self._selection_changed)
        self._tree.tag_configure('protected', foreground='grey')
        tk.Label(self, textvariable=self._status, anchor='w', wraplength=920).pack(fill=tk.X, padx=10, pady=5)
        controls = tk.Frame(self)
        controls.pack(fill=tk.X, padx=10, pady=10)
        self._refresh_button = tk.Button(controls, text='Refresh', command=self.refresh)
        self._refresh_button.pack(side=tk.LEFT)
        self._delete_button = tk.Button(controls, text='Delete selected recovery copies', command=self.delete_selected,
                                        state='disabled')
        self._delete_button.pack(side=tk.LEFT, padx=10)
        tk.Button(controls, text='Close', command=self.destroy).pack(side=tk.RIGHT)
        self.grab_set()
        self.refresh()

    def _launch(self, names=None):
        self._busy = True
        self._delete_button.configure(state='disabled')
        self._refresh_button.configure(state='disabled')
        active = tuple(self._active_paths())
        threading.Thread(target=_work, args=(self._result, self._folder, active, names), daemon=True).start()
        self._poll_id = self.after(100, self._poll)

    def refresh(self):
        if not self._busy:
            self._status.set('Reading recovery folders...')
            self._launch()

    def _selection_changed(self, event=None):
        eligible = bool(self._tree.selection()) and all(
            self._runs[key]['deletable'] for key in self._tree.selection())
        self._delete_button.configure(state='normal' if eligible and not self._busy else 'disabled')

    def delete_selected(self):
        if self._busy:
            return
        selected = [self._runs[key] for key in self._tree.selection()]
        if not selected or any(not run['deletable'] for run in selected):
            return
        total = sum(run['size_bytes'] or 0 for run in selected)
        names = [run['name'] for run in selected]
        listing = '\n'.join(names[:8]) + ('\n...' if len(names) > 8 else '')
        if not messagebox.askyesno('Delete recovery copies?',
                f'Permanently delete {len(names)} recovery run(s), approximately {total/GIB:.2f} GiB?\n\n'
                f'{listing}\n\nConfirm that any data you need has been exported and reopens correctly. '
                'These recovery copies cannot be restored after deletion.', parent=self):
            return
        self._status.set('Deleting selected recovery copies...')
        self._launch(names)

    def _poll(self):
        self._poll_id = None
        try:
            kind, data = self._result.get_nowait()
        except queue.Empty:
            self._poll_id = self.after(100, self._poll)
            return
        self._busy = False
        self._refresh_button.configure(state='normal')
        if kind == 'listed':
            runs, capacity = data
            self._tree.delete(*self._tree.get_children())
            self._runs = {}
            for index, run in enumerate(runs):
                key = str(index)
                self._runs[key] = run
                date = datetime.fromtimestamp(run['modified'], timezone.utc).strftime('%Y-%m-%d %H:%M') if run['modified'] else '-'
                size = f"{run['size_bytes']/GIB:.3f} GiB" if run['size_bytes'] is not None else 'Protected'
                self._tree.insert('', 'end', iid=key, values=(run['name'], date, size, run['status']),
                                  tags=() if run['deletable'] else ('protected',))
            total = sum(run['size_bytes'] or 0 for run in runs)
            prefix = 'LOW DISK SPACE. ' if capacity['low_space'] else ''
            self._space.set(f"{prefix}{capacity['free_bytes']/GIB:.1f} GiB free of {capacity['total_bytes']/GIB:.1f} GiB. "
                            f'Listed recovery copies: {total/GIB:.2f} GiB.')
            self._status.set(self._last_action or f'{len(runs)} recovery folders. No export verification is assumed.')
        elif kind == 'deleted':
            removed, size, failures = data
            self._last_action = f'Deleted {removed} recovery run(s), approximately {size/GIB:.2f} GiB.'
            if failures:
                messagebox.showerror('Some recovery copies were not removed', '\n'.join(failures), parent=self)
            self.refresh()
        else:
            self._status.set('Could not read recovery folders: ' + data)
        self._selection_changed()

    def destroy(self):
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        self._status = self._space = None
        super().destroy()
