# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'heatmap_plotter.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDockWidget,
    QFormLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_HeatmapPlotter(object):
    def setupUi(self, HeatmapPlotter):
        if not HeatmapPlotter.objectName():
            HeatmapPlotter.setObjectName(u"HeatmapPlotter")
        HeatmapPlotter.resize(608, 576)
        self.verticalLayout_2 = QVBoxLayout(HeatmapPlotter)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.combo_plotoption = QComboBox(HeatmapPlotter)
        self.combo_plotoption.setObjectName(u"combo_plotoption")

        self.main_layout.addWidget(self.combo_plotoption)

        self.lyt_plot_params = QFormLayout()
        self.lyt_plot_params.setObjectName(u"lyt_plot_params")

        self.main_layout.addLayout(self.lyt_plot_params)

        self.dock_plot = QDockWidget(HeatmapPlotter)
        self.dock_plot.setObjectName(u"dock_plot")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.dock_plot.sizePolicy().hasHeightForWidth())
        self.dock_plot.setSizePolicy(sizePolicy)
        self.dock_plot.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lyt_heatmap_holder = QVBoxLayout()
        self.lyt_heatmap_holder.setObjectName(u"lyt_heatmap_holder")

        self.verticalLayout.addLayout(self.lyt_heatmap_holder)

        self.dock_plot.setWidget(self.dockWidgetContents)

        self.main_layout.addWidget(self.dock_plot)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_8 = QLabel(HeatmapPlotter)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.label_8)

        self.lbl_clickedcoor = QLabel(HeatmapPlotter)
        self.lbl_clickedcoor.setObjectName(u"lbl_clickedcoor")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.lbl_clickedcoor.sizePolicy().hasHeightForWidth())
        self.lbl_clickedcoor.setSizePolicy(sizePolicy1)

        self.horizontalLayout_3.addWidget(self.lbl_clickedcoor)


        self.main_layout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.combo_unitchoise = QComboBox(HeatmapPlotter)
        self.combo_unitchoise.setObjectName(u"combo_unitchoise")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(3)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.combo_unitchoise.sizePolicy().hasHeightForWidth())
        self.combo_unitchoise.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.combo_unitchoise)

        self.chk_Ramanshift = QCheckBox(HeatmapPlotter)
        self.chk_Ramanshift.setObjectName(u"chk_Ramanshift")
        self.chk_Ramanshift.setChecked(True)

        self.horizontalLayout.addWidget(self.chk_Ramanshift)

        self.combo_spectralpos = QComboBox(HeatmapPlotter)
        self.combo_spectralpos.setObjectName(u"combo_spectralpos")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(1)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.combo_spectralpos.sizePolicy().hasHeightForWidth())
        self.combo_spectralpos.setSizePolicy(sizePolicy3)
        self.combo_spectralpos.setEditable(True)

        self.horizontalLayout.addWidget(self.combo_spectralpos)

        self.lbl_specposunit = QLabel(HeatmapPlotter)
        self.lbl_specposunit.setObjectName(u"lbl_specposunit")

        self.horizontalLayout.addWidget(self.lbl_specposunit)


        self.main_layout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_saveplot = QPushButton(HeatmapPlotter)
        self.btn_saveplot.setObjectName(u"btn_saveplot")

        self.horizontalLayout_2.addWidget(self.btn_saveplot)

        self.btn_savedata = QPushButton(HeatmapPlotter)
        self.btn_savedata.setObjectName(u"btn_savedata")

        self.horizontalLayout_2.addWidget(self.btn_savedata)


        self.main_layout.addLayout(self.horizontalLayout_2)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_4 = QLabel(HeatmapPlotter)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_4, 2, 0, 1, 1)

        self.label_3 = QLabel(HeatmapPlotter)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_3, 1, 0, 1, 1)

        self.ent_cbar_min = QLineEdit(HeatmapPlotter)
        self.ent_cbar_min.setObjectName(u"ent_cbar_min")

        self.gridLayout_2.addWidget(self.ent_cbar_min, 0, 1, 1, 1)

        self.chk_autocbar = QCheckBox(HeatmapPlotter)
        self.chk_autocbar.setObjectName(u"chk_autocbar")

        self.gridLayout_2.addWidget(self.chk_autocbar, 0, 4, 1, 1)

        self.label_7 = QLabel(HeatmapPlotter)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_7, 2, 2, 1, 1)

        self.ent_xmin = QLineEdit(HeatmapPlotter)
        self.ent_xmin.setObjectName(u"ent_xmin")

        self.gridLayout_2.addWidget(self.ent_xmin, 1, 1, 1, 1)

        self.ent_cbar_max = QLineEdit(HeatmapPlotter)
        self.ent_cbar_max.setObjectName(u"ent_cbar_max")

        self.gridLayout_2.addWidget(self.ent_cbar_max, 0, 3, 1, 1)

        self.ent_ymax = QLineEdit(HeatmapPlotter)
        self.ent_ymax.setObjectName(u"ent_ymax")

        self.gridLayout_2.addWidget(self.ent_ymax, 2, 3, 1, 1)

        self.label_5 = QLabel(HeatmapPlotter)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_5, 0, 2, 1, 1)

        self.ent_xmax = QLineEdit(HeatmapPlotter)
        self.ent_xmax.setObjectName(u"ent_xmax")

        self.gridLayout_2.addWidget(self.ent_xmax, 1, 3, 1, 1)

        self.label_2 = QLabel(HeatmapPlotter)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_2, 0, 0, 1, 1)

        self.label_6 = QLabel(HeatmapPlotter)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_6, 1, 2, 1, 1)

        self.ent_ymin = QLineEdit(HeatmapPlotter)
        self.ent_ymin.setObjectName(u"ent_ymin")

        self.gridLayout_2.addWidget(self.ent_ymin, 2, 1, 1, 1)


        self.main_layout.addLayout(self.gridLayout_2)

        self.btn_plotterreset = QPushButton(HeatmapPlotter)
        self.btn_plotterreset.setObjectName(u"btn_plotterreset")

        self.main_layout.addWidget(self.btn_plotterreset)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(HeatmapPlotter)

        QMetaObject.connectSlotsByName(HeatmapPlotter)
    # setupUi

    def retranslateUi(self, HeatmapPlotter):
        HeatmapPlotter.setWindowTitle(QCoreApplication.translate("HeatmapPlotter", u"Form", None))
        self.label_8.setText(QCoreApplication.translate("HeatmapPlotter", u"Clicked (\u00b5m):", None))
        self.lbl_clickedcoor.setText(QCoreApplication.translate("HeatmapPlotter", u"(-,-)", None))
        self.chk_Ramanshift.setText(QCoreApplication.translate("HeatmapPlotter", u"Plot Raman-shift", None))
        self.lbl_specposunit.setText(QCoreApplication.translate("HeatmapPlotter", u"cm<sup>-1<sup>", None))
        self.btn_saveplot.setText(QCoreApplication.translate("HeatmapPlotter", u"Save plot", None))
        self.btn_savedata.setText(QCoreApplication.translate("HeatmapPlotter", u"Save plot data (.csv)", None))
        self.label_4.setText(QCoreApplication.translate("HeatmapPlotter", u"Y-min (mm):", None))
        self.label_3.setText(QCoreApplication.translate("HeatmapPlotter", u"X-min (mm):", None))
        self.chk_autocbar.setText(QCoreApplication.translate("HeatmapPlotter", u"Auto", None))
        self.label_7.setText(QCoreApplication.translate("HeatmapPlotter", u"Y-max (mm):", None))
        self.label_5.setText(QCoreApplication.translate("HeatmapPlotter", u"Colourbar max:", None))
        self.label_2.setText(QCoreApplication.translate("HeatmapPlotter", u"Colourbar min:", None))
        self.label_6.setText(QCoreApplication.translate("HeatmapPlotter", u"X-max (mm):", None))
        self.btn_plotterreset.setText(QCoreApplication.translate("HeatmapPlotter", u"Reset plotter (if not displaying correctly)", None))
    # retranslateUi

