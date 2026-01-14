# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dataHub_Raman.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QTreeWidget, QTreeWidgetItem, QWidget)

class Ui_DataHub_mapping(object):
    def setupUi(self, DataHub_mapping):
        if not DataHub_mapping.objectName():
            DataHub_mapping.setObjectName(u"DataHub_mapping")
        DataHub_mapping.resize(558, 356)
        self.gridLayout = QGridLayout(DataHub_mapping)
        self.gridLayout.setObjectName(u"gridLayout")
        self.btn_rename = QPushButton(DataHub_mapping)
        self.btn_rename.setObjectName(u"btn_rename")

        self.gridLayout.addWidget(self.btn_rename, 2, 1, 1, 1)

        self.btn_delete = QPushButton(DataHub_mapping)
        self.btn_delete.setObjectName(u"btn_delete")

        self.gridLayout.addWidget(self.btn_delete, 2, 2, 1, 1)

        self.btn_refresh = QPushButton(DataHub_mapping)
        self.btn_refresh.setObjectName(u"btn_refresh")

        self.gridLayout.addWidget(self.btn_refresh, 2, 0, 1, 1)

        self.tree_data = QTreeWidget(DataHub_mapping)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_data.setHeaderItem(__qtreewidgetitem)
        self.tree_data.setObjectName(u"tree_data")
        self.tree_data.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_data.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.gridLayout.addWidget(self.tree_data, 1, 0, 1, 3)

        self.lbl_autosave = QLabel(DataHub_mapping)
        self.lbl_autosave.setObjectName(u"lbl_autosave")

        self.gridLayout.addWidget(self.lbl_autosave, 6, 0, 1, 3)

        self.ent_searchbar = QLineEdit(DataHub_mapping)
        self.ent_searchbar.setObjectName(u"ent_searchbar")

        self.gridLayout.addWidget(self.ent_searchbar, 0, 0, 1, 3)

        self.lyt_saveload = QHBoxLayout()
        self.lyt_saveload.setObjectName(u"lyt_saveload")
        self.btn_save_ext = QPushButton(DataHub_mapping)
        self.btn_save_ext.setObjectName(u"btn_save_ext")

        self.lyt_saveload.addWidget(self.btn_save_ext)

        self.btn_save_db = QPushButton(DataHub_mapping)
        self.btn_save_db.setObjectName(u"btn_save_db")

        self.lyt_saveload.addWidget(self.btn_save_db)

        self.btn_load_db = QPushButton(DataHub_mapping)
        self.btn_load_db.setObjectName(u"btn_load_db")

        self.lyt_saveload.addWidget(self.btn_load_db)


        self.gridLayout.addLayout(self.lyt_saveload, 3, 0, 1, 3)


        self.retranslateUi(DataHub_mapping)

        QMetaObject.connectSlotsByName(DataHub_mapping)
    # setupUi

    def retranslateUi(self, DataHub_mapping):
        DataHub_mapping.setWindowTitle(QCoreApplication.translate("DataHub_mapping", u"Form", None))
        self.btn_rename.setText(QCoreApplication.translate("DataHub_mapping", u"Rename selected ROI", None))
        self.btn_delete.setText(QCoreApplication.translate("DataHub_mapping", u"Delete selected ROI", None))
        self.btn_refresh.setText(QCoreApplication.translate("DataHub_mapping", u"Refresh", None))
        self.lbl_autosave.setText(QCoreApplication.translate("DataHub_mapping", u"Autosave: Disabled", None))
        self.ent_searchbar.setPlaceholderText(QCoreApplication.translate("DataHub_mapping", u"Search by typing here...", None))
        self.btn_save_ext.setText(QCoreApplication.translate("DataHub_mapping", u"Save selected ROI [.csv, etc]", None))
        self.btn_save_db.setText(QCoreApplication.translate("DataHub_mapping", u"Save all ROIs [.db]", None))
        self.btn_load_db.setText(QCoreApplication.translate("DataHub_mapping", u"Load ROIs [.db]", None))
    # retranslateUi

