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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_DataHub_mapping(object):
    def setupUi(self, DataHub_mapping):
        if not DataHub_mapping.objectName():
            DataHub_mapping.setObjectName(u"DataHub_mapping")
        DataHub_mapping.resize(558, 356)
        self.gridLayout = QGridLayout(DataHub_mapping)
        self.gridLayout.setObjectName(u"gridLayout")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.ent_searchbar = QLineEdit(DataHub_mapping)
        self.ent_searchbar.setObjectName(u"ent_searchbar")

        self.main_layout.addWidget(self.ent_searchbar)

        self.tree_data = QTreeWidget(DataHub_mapping)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_data.setHeaderItem(__qtreewidgetitem)
        self.tree_data.setObjectName(u"tree_data")
        self.tree_data.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_data.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.main_layout.addWidget(self.tree_data)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_refresh = QPushButton(DataHub_mapping)
        self.btn_refresh.setObjectName(u"btn_refresh")

        self.horizontalLayout.addWidget(self.btn_refresh)

        self.btn_rename = QPushButton(DataHub_mapping)
        self.btn_rename.setObjectName(u"btn_rename")

        self.horizontalLayout.addWidget(self.btn_rename)

        self.btn_delete = QPushButton(DataHub_mapping)
        self.btn_delete.setObjectName(u"btn_delete")

        self.horizontalLayout.addWidget(self.btn_delete)


        self.main_layout.addLayout(self.horizontalLayout)

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


        self.main_layout.addLayout(self.lyt_saveload)

        self.lbl_autosave = QLabel(DataHub_mapping)
        self.lbl_autosave.setObjectName(u"lbl_autosave")

        self.main_layout.addWidget(self.lbl_autosave)

        self.chk_autoOffload = QCheckBox(DataHub_mapping)
        self.chk_autoOffload.setObjectName(u"chk_autoOffload")

        self.main_layout.addWidget(self.chk_autoOffload)


        self.gridLayout.addLayout(self.main_layout, 0, 0, 1, 1)

        QWidget.setTabOrder(self.btn_save_ext, self.btn_save_db)
        QWidget.setTabOrder(self.btn_save_db, self.btn_load_db)

        self.retranslateUi(DataHub_mapping)

        QMetaObject.connectSlotsByName(DataHub_mapping)
    # setupUi

    def retranslateUi(self, DataHub_mapping):
        DataHub_mapping.setWindowTitle(QCoreApplication.translate("DataHub_mapping", u"Form", None))
        self.ent_searchbar.setPlaceholderText(QCoreApplication.translate("DataHub_mapping", u"Search by typing here...", None))
        self.btn_refresh.setText(QCoreApplication.translate("DataHub_mapping", u"Refresh", None))
        self.btn_rename.setText(QCoreApplication.translate("DataHub_mapping", u"Rename selected ROI", None))
        self.btn_delete.setText(QCoreApplication.translate("DataHub_mapping", u"Delete selected ROI", None))
        self.btn_save_ext.setText(QCoreApplication.translate("DataHub_mapping", u"Save selected ROI [.csv, etc]", None))
        self.btn_save_db.setText(QCoreApplication.translate("DataHub_mapping", u"Save all ROIs [.db]", None))
        self.btn_load_db.setText(QCoreApplication.translate("DataHub_mapping", u"Load ROIs [.db]", None))
        self.lbl_autosave.setText(QCoreApplication.translate("DataHub_mapping", u"Autosave: Disabled", None))
        self.chk_autoOffload.setText(QCoreApplication.translate("DataHub_mapping", u"Auto-offload measurements when memory is full (to the autosave file)", None))
    # retranslateUi

