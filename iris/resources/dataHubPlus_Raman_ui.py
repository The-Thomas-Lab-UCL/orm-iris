# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dataHubPlus_Raman.ui'
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QHeaderView, QLabel,
    QSizePolicy, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_DataHubPlus_mapping(object):
    def setupUi(self, DataHubPlus_mapping):
        if not DataHubPlus_mapping.objectName():
            DataHubPlus_mapping.setObjectName(u"DataHubPlus_mapping")
        DataHubPlus_mapping.resize(688, 508)
        self.verticalLayout_2 = QVBoxLayout(DataHubPlus_mapping)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.groupBox_main = QGroupBox(DataHubPlus_mapping)
        self.groupBox_main.setObjectName(u"groupBox_main")
        self.verticalLayout = QVBoxLayout(self.groupBox_main)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tree_data = QTreeWidget(self.groupBox_main)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_data.setHeaderItem(__qtreewidgetitem)
        self.tree_data.setObjectName(u"tree_data")

        self.verticalLayout.addWidget(self.tree_data)

        self.lbl_info = QLabel(self.groupBox_main)
        self.lbl_info.setObjectName(u"lbl_info")

        self.verticalLayout.addWidget(self.lbl_info)


        self.verticalLayout_2.addWidget(self.groupBox_main)


        self.retranslateUi(DataHubPlus_mapping)

        QMetaObject.connectSlotsByName(DataHubPlus_mapping)
    # setupUi

    def retranslateUi(self, DataHubPlus_mapping):
        DataHubPlus_mapping.setWindowTitle(QCoreApplication.translate("DataHubPlus_mapping", u"Form", None))
        self.groupBox_main.setTitle(QCoreApplication.translate("DataHubPlus_mapping", u"ROI sampling points viewer", None))
        self.lbl_info.setText(QCoreApplication.translate("DataHubPlus_mapping", u"TextLabel", None))
    # retranslateUi

