"""A bounded Tk viewport whose contents can exceed the available window space."""

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, minimum_width=None):
        super().__init__(parent)
        self._pending_layout = None
        self.minimum_width = minimum_width
        # Keep content requests (including hidden notebook tabs) out of the
        # surrounding window's geometry. Only the viewport receives extra space.
        self.canvas = tk.Canvas(self, width=1, height=1, highlightthickness=0)
        self.content = tk.Frame(self.canvas)
        self._window = self.canvas.create_window(0, 0, window=self.content, anchor='nw')
        self._vertical = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self._horizontal = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self._vertical.set, xscrollcommand=self._horizontal.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self._vertical.grid(row=0, column=1, sticky='ns')
        self._horizontal.grid(row=1, column=0, sticky='ew')
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.canvas.bind('<Configure>', self.refresh)
        self.content.bind('<Configure>', self.refresh)
        # Descendants may change their requested size while the content window
        # keeps the same allocated size (e.g. the Z plot moves beside controls).
        self._toplevel = self.winfo_toplevel()
        self._configure_binding = self._toplevel.bind(
            '<Configure>', self._content_configured, add='+')
        # Local bindings leave Matplotlib zoom and existing control bindings alone.
        for widget in (self.canvas, self.content):
            widget.bind('<MouseWheel>', self._scroll)
            widget.bind('<Button-4>', self._scroll)
            widget.bind('<Button-5>', self._scroll)

    def refresh(self, event=None):
        if self._pending_layout is None:
            self._pending_layout = self.after_idle(self._sync_content)

    def _content_configured(self, event):
        if str(event.widget).startswith(str(self.content) + '.'):
            self.refresh()

    def _sync_content(self):
        self._pending_layout = None
        minimum = (self.minimum_width() if self.minimum_width is not None
                   else self.content.winfo_reqwidth())
        width = max(self.canvas.winfo_width(), minimum)
        height = max(self.canvas.winfo_height(), self.content.winfo_reqheight())
        self.canvas.itemconfigure(self._window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def _scroll(self, event):
        if self.canvas.yview() == (0., 1.):
            return
        if getattr(event, 'num', None) in (4, 5):
            steps = -1 if event.num == 4 else 1
        else:
            steps = -int(event.delta / 120)
        self.canvas.yview_scroll(steps, 'units')
        return 'break'

    def destroy(self):
        self._toplevel.unbind('<Configure>', self._configure_binding)
        if self._pending_layout is not None:
            self.after_cancel(self._pending_layout)
            self._pending_layout = None
        super().destroy()
