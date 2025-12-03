# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'heatmap_plotter_overlay.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_heatmapPlotterOverlay(object):
    def setupUi(self, heatmapPlotterOverlay):
        if not heatmapPlotterOverlay.objectName():
            heatmapPlotterOverlay.setObjectName(u"heatmapPlotterOverlay")
        heatmapPlotterOverlay.resize(683, 585)
        self.verticalLayout_2 = QVBoxLayout(heatmapPlotterOverlay)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.lyt_holder_plotter = QVBoxLayout()
        self.lyt_holder_plotter.setObjectName(u"lyt_holder_plotter")

        self.gridLayout.addLayout(self.lyt_holder_plotter, 0, 0, 1, 1)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.combo_imgUnit = QComboBox(heatmapPlotterOverlay)
        self.combo_imgUnit.setObjectName(u"combo_imgUnit")

        self.verticalLayout_6.addWidget(self.combo_imgUnit)

        self.chk_lres = QCheckBox(heatmapPlotterOverlay)
        self.chk_lres.setObjectName(u"chk_lres")
        self.chk_lres.setChecked(True)

        self.verticalLayout_6.addWidget(self.chk_lres)


        self.gridLayout.addLayout(self.verticalLayout_6, 1, 0, 1, 1)

        self.lyt_holder_finetuning = QVBoxLayout()
        self.lyt_holder_finetuning.setObjectName(u"lyt_holder_finetuning")

        self.gridLayout.addLayout(self.lyt_holder_finetuning, 0, 1, 2, 1)


        self.main_layout.addLayout(self.gridLayout)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(heatmapPlotterOverlay)

        QMetaObject.connectSlotsByName(heatmapPlotterOverlay)
    # setupUi

    def retranslateUi(self, heatmapPlotterOverlay):
        heatmapPlotterOverlay.setWindowTitle(QCoreApplication.translate("heatmapPlotterOverlay", u"Form", None))
        self.chk_lres.setText(QCoreApplication.translate("heatmapPlotterOverlay", u"Show low-resolution image (faster processing)", None))
    # retranslateUi

