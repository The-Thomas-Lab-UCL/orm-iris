# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'brightfieldcontrol.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDockWidget,
    QGridLayout, QHBoxLayout, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_wdg_brightfield_controller(object):
    def setupUi(self, wdg_brightfield_controller):
        if not wdg_brightfield_controller.objectName():
            wdg_brightfield_controller.setObjectName(u"wdg_brightfield_controller")
        wdg_brightfield_controller.resize(585, 504)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(wdg_brightfield_controller.sizePolicy().hasHeightForWidth())
        wdg_brightfield_controller.setSizePolicy(sizePolicy)
        self.verticalLayout = QVBoxLayout(wdg_brightfield_controller)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.dock_video = QDockWidget(wdg_brightfield_controller)
        self.dock_video.setObjectName(u"dock_video")
        self.dock_video.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_3 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.wdg_video = QWidget(self.dockWidgetContents)
        self.wdg_video.setObjectName(u"wdg_video")
        sizePolicy.setHeightForWidth(self.wdg_video.sizePolicy().hasHeightForWidth())
        self.wdg_video.setSizePolicy(sizePolicy)

        self.verticalLayout_2.addWidget(self.wdg_video)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.chk_crosshair = QCheckBox(self.dockWidgetContents)
        self.chk_crosshair.setObjectName(u"chk_crosshair")
        self.chk_crosshair.setChecked(True)

        self.horizontalLayout_3.addWidget(self.chk_crosshair)

        self.chk_scalebar = QCheckBox(self.dockWidgetContents)
        self.chk_scalebar.setObjectName(u"chk_scalebar")
        self.chk_scalebar.setChecked(True)

        self.horizontalLayout_3.addWidget(self.chk_scalebar)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)


        self.verticalLayout_3.addLayout(self.verticalLayout_2)

        self.dock_video.setWidget(self.dockWidgetContents)

        self.main_layout.addWidget(self.dock_video)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.btn_saveff = QPushButton(wdg_brightfield_controller)
        self.btn_saveff.setObjectName(u"btn_saveff")

        self.gridLayout.addWidget(self.btn_saveff, 5, 0, 1, 1)

        self.pushButton_2 = QPushButton(wdg_brightfield_controller)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.gridLayout.addWidget(self.pushButton_2, 1, 1, 1, 1)

        self.btn_setffgain = QPushButton(wdg_brightfield_controller)
        self.btn_setffgain.setObjectName(u"btn_setffgain")

        self.gridLayout.addWidget(self.btn_setffgain, 4, 0, 1, 1)

        self.combo_image_correction = QComboBox(wdg_brightfield_controller)
        self.combo_image_correction.setObjectName(u"combo_image_correction")

        self.gridLayout.addWidget(self.combo_image_correction, 2, 0, 1, 2)

        self.btn_setff = QPushButton(wdg_brightfield_controller)
        self.btn_setff.setObjectName(u"btn_setff")

        self.gridLayout.addWidget(self.btn_setff, 4, 1, 1, 1)

        self.btn_loadff = QPushButton(wdg_brightfield_controller)
        self.btn_loadff.setObjectName(u"btn_loadff")

        self.gridLayout.addWidget(self.btn_loadff, 5, 1, 1, 1)

        self.btn_camera_onoff = QPushButton(wdg_brightfield_controller)
        self.btn_camera_onoff.setObjectName(u"btn_camera_onoff")
        self.btn_camera_onoff.setStyleSheet(u"background: 'red'")

        self.gridLayout.addWidget(self.btn_camera_onoff, 1, 0, 1, 1)


        self.main_layout.addLayout(self.gridLayout)


        self.verticalLayout.addLayout(self.main_layout)

        QWidget.setTabOrder(self.btn_camera_onoff, self.pushButton_2)
        QWidget.setTabOrder(self.pushButton_2, self.combo_image_correction)
        QWidget.setTabOrder(self.combo_image_correction, self.btn_setffgain)
        QWidget.setTabOrder(self.btn_setffgain, self.btn_setff)
        QWidget.setTabOrder(self.btn_setff, self.btn_saveff)
        QWidget.setTabOrder(self.btn_saveff, self.btn_loadff)

        self.retranslateUi(wdg_brightfield_controller)

        QMetaObject.connectSlotsByName(wdg_brightfield_controller)
    # setupUi

    def retranslateUi(self, wdg_brightfield_controller):
        wdg_brightfield_controller.setWindowTitle(QCoreApplication.translate("wdg_brightfield_controller", u"Form", None))
        self.chk_crosshair.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Show crosshair", None))
        self.chk_scalebar.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Show scalebar", None))
        self.btn_saveff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Save flatfield correction", None))
        self.pushButton_2.setText(QCoreApplication.translate("wdg_brightfield_controller", u"PushButton", None))
        self.btn_setffgain.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Set flatfield gain", None))
        self.btn_setff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Acquire flatfield correction", None))
        self.btn_loadff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Load flatfield correction", None))
        self.btn_camera_onoff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Pause camera feed", None))
    # retranslateUi

