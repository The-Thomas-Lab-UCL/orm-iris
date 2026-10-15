"""
A dialog to display the full metadata of one or more measurement units in a
scrollable table. Shared by the mapping measurement and image measurement data hubs.
"""
import PySide6.QtWidgets as qw
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import Qt, Slot

from typing import Any

MAX_VALUE_CHARS = 2000  # Values longer than this are truncated in the table (full value stays in the tooltip)


def flatten_metadata(metadata:Any, prefix:str='') -> list[tuple[str,str]]:
    """
    Flattens a (possibly nested) metadata structure into a list of (field, value) rows.
    Nested keys are joined with a dot, list/tuple entries with a bracketed index.

    Args:
        metadata (Any): The metadata structure (dict, list/tuple or scalar).
        prefix (str): The field path accumulated so far. Used for the recursion.

    Returns:
        list[tuple[str,str]]: List of (field path, value as string) rows.
    """
    rows:list[tuple[str,str]] = []

    if isinstance(metadata, dict):
        if not metadata: return [(prefix or '-', '{} (empty)')]
        for key, value in metadata.items():
            field = f'{prefix}.{key}' if prefix else str(key)
            rows.extend(flatten_metadata(value, field))
    elif isinstance(metadata, (list, tuple)):
        # Keep short flat sequences on a single row; expand the ones holding structures
        if not metadata: return [(prefix or '-', '[] (empty)')]
        if all(not isinstance(item, (dict, list, tuple)) for item in metadata) and len(metadata) <= 10:
            rows.append((prefix or '-', str(list(metadata))))
        else:
            for idx, item in enumerate(metadata):
                rows.extend(flatten_metadata(item, f'{prefix}[{idx}]'))
    else:
        rows.append((prefix or '-', str(metadata)))

    return rows


class Dlg_MetadataViewer(qw.QDialog):
    """
    Modeless dialog showing the metadata of the given units as a searchable, scrollable table.
    """

    def __init__(self, dict_name_metadata:dict[str,Any], parent=None, title:str='Metadata'):
        """
        Args:
            dict_name_metadata (dict[str,Any]): Mapping of unit name to that unit's metadata structure.
            parent (QWidget|None): Parent widget. Defaults to None.
            title (str): Window title. Defaults to 'Metadata'.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 520)
        self.setSizeGripEnabled(True)
        # Modeless and parented: free it on close so repeated openings do not pile up as children
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self._multi = len(dict_name_metadata) > 1
        self._headers = ['Unit', 'Field', 'Value'] if self._multi else ['Field', 'Value']

        # Build the rows: (unit name, field, value)
        self._rows:list[tuple[str,str,str]] = []
        for unit_name, metadata in dict_name_metadata.items():
            for field, value in flatten_metadata(metadata):
                self._rows.append((unit_name, field, value))

        layout = qw.QVBoxLayout(self)

        # > Search bar <
        lyt_search = qw.QHBoxLayout()
        lyt_search.addWidget(qw.QLabel('Filter:', self))
        self._ent_filter = qw.QLineEdit(self)
        self._ent_filter.setPlaceholderText('Type to filter by field or value...')
        self._ent_filter.textChanged.connect(self._apply_filter)
        lyt_search.addWidget(self._ent_filter)
        layout.addLayout(lyt_search)

        # > Metadata table <
        self._table = qw.QTableWidget(self)
        self._table.setColumnCount(len(self._headers))
        self._table.setHorizontalHeaderLabels(self._headers)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(qw.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(qw.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(qw.QAbstractItemView.SelectionMode.ExtendedSelection)
        self._table.setWordWrap(False)
        self._table.setAlternatingRowColors(True)
        self._table.setHorizontalScrollMode(qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setVerticalScrollMode(qw.QAbstractItemView.ScrollMode.ScrollPerPixel)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(len(self._headers) - 1, qw.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

        self._lbl_count = qw.QLabel(self)
        layout.addWidget(self._lbl_count)

        # > Buttons <
        lyt_btn = qw.QHBoxLayout()
        btn_copy = qw.QPushButton('Copy to clipboard', self)
        btn_copy.setToolTip('Copies the shown rows as tab-separated text')
        btn_copy.clicked.connect(self._copy_to_clipboard)
        lyt_btn.addWidget(btn_copy)
        lyt_btn.addStretch()
        btn_close = qw.QPushButton('Close', self)
        btn_close.clicked.connect(self.close)
        lyt_btn.addWidget(btn_close)
        layout.addLayout(lyt_btn)

        self._populate(self._rows)

    def _populate(self, rows:list[tuple[str,str,str]]):
        """
        Fills the table with the given rows.

        Args:
            rows (list[tuple[str,str,str]]): List of (unit name, field, value) rows.
        """
        self._table.setRowCount(len(rows))
        for row_idx, (unit_name, field, value) in enumerate(rows):
            texts = [unit_name, field, value] if self._multi else [field, value]
            for col_idx, text in enumerate(texts):
                shown = text if len(text) <= MAX_VALUE_CHARS else text[:MAX_VALUE_CHARS] + f'... [{len(text)} chars]'
                item = qw.QTableWidgetItem(shown)
                item.setToolTip(text)
                self._table.setItem(row_idx, col_idx, item)

        self._table.resizeColumnsToContents()
        # Keep the value column from pushing the others off-screen
        last_col = len(self._headers) - 1
        for col in range(last_col):
            self._table.setColumnWidth(col, min(self._table.columnWidth(col), 320))

        total = len(self._rows)
        if len(rows) == total: self._lbl_count.setText(f'{total} field(s)')
        else: self._lbl_count.setText(f'{len(rows)} of {total} field(s) shown')

    @Slot()
    def _apply_filter(self):
        """
        Repopulates the table with only the rows matching the filter text.
        """
        query = self._ent_filter.text().strip().lower()
        if not query: self._populate(self._rows); return
        rows = [row for row in self._rows if any(query in cell.lower() for cell in row)]
        self._populate(rows)

    @Slot()
    def _copy_to_clipboard(self):
        """
        Copies the currently shown rows to the clipboard as tab-separated text.
        """
        lines = ['\t'.join(self._headers)]
        for row_idx in range(self._table.rowCount()):
            cells = [self._table.item(row_idx, col).toolTip() if self._table.item(row_idx, col) else ''
                     for col in range(self._table.columnCount())]
            lines.append('\t'.join(cell.replace('\t', ' ').replace('\n', ' ') for cell in cells))

        clipboard = QGuiApplication.clipboard()
        if clipboard is not None: clipboard.setText('\n'.join(lines))
