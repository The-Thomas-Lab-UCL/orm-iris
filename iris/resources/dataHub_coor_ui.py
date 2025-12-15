# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dataHub_coor.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QHeaderView,
    QPushButton, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QWidget)

class Ui_dataHub_coor(object):
    def setupUi(self, dataHub_coor):
        if not dataHub_coor.objectName():
            dataHub_coor.setObjectName(u"dataHub_coor")
        dataHub_coor.resize(674, 480)
        self.gridLayout = QGridLayout(dataHub_coor)
        self.gridLayout.setObjectName(u"gridLayout")
        self.btn_remove = QPushButton(dataHub_coor)
        self.btn_remove.setObjectName(u"btn_remove")

        self.gridLayout.addWidget(self.btn_remove, 1, 1, 1, 1)

        self.btn_load = QPushButton(dataHub_coor)
        self.btn_load.setObjectName(u"btn_load")

        self.gridLayout.addWidget(self.btn_load, 2, 0, 1, 1)

        self.tree_coor = QTreeWidget(dataHub_coor)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(2, u"3");
        __qtreewidgetitem.setText(1, u"2");
        __qtreewidgetitem.setText(0, u"1");
        self.tree_coor.setHeaderItem(__qtreewidgetitem)
        self.tree_coor.setObjectName(u"tree_coor")
        self.tree_coor.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_coor.setAllColumnsShowFocus(False)
        self.tree_coor.setColumnCount(3)

        self.gridLayout.addWidget(self.tree_coor, 0, 0, 1, 2)

        self.btn_rename = QPushButton(dataHub_coor)
        self.btn_rename.setObjectName(u"btn_rename")

        self.gridLayout.addWidget(self.btn_rename, 1, 0, 1, 1)

        self.btn_save = QPushButton(dataHub_coor)
        self.btn_save.setObjectName(u"btn_save")

        self.gridLayout.addWidget(self.btn_save, 2, 1, 1, 1)


        self.retranslateUi(dataHub_coor)

        QMetaObject.connectSlotsByName(dataHub_coor)
    # setupUi

    def retranslateUi(self, dataHub_coor):
        dataHub_coor.setWindowTitle(QCoreApplication.translate("dataHub_coor", u"Form", None))
        self.btn_remove.setText(QCoreApplication.translate("dataHub_coor", u"Remove ROI", None))
        self.btn_load.setText(QCoreApplication.translate("dataHub_coor", u"Load ROI", None))
        self.btn_rename.setText(QCoreApplication.translate("dataHub_coor", u"Rename ROI", None))
        self.btn_save.setText(QCoreApplication.translate("dataHub_coor", u"Save ROI (.csv)", None))
    # retranslateUi

