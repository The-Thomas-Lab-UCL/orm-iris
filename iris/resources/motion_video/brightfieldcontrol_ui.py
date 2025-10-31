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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

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
        self.verticalLayoutWidget = QWidget(wdg_brightfield_controller)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(110, 30, 411, 401))
        self.lyt_main = QVBoxLayout(self.verticalLayoutWidget)
        self.lyt_main.setObjectName(u"lyt_main")
        self.lyt_main.setContentsMargins(0, 0, 0, 0)
        self.wdg_video = QWidget(self.verticalLayoutWidget)
        self.wdg_video.setObjectName(u"wdg_video")
        sizePolicy.setHeightForWidth(self.wdg_video.sizePolicy().hasHeightForWidth())
        self.wdg_video.setSizePolicy(sizePolicy)

        self.lyt_main.addWidget(self.wdg_video)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.btn_setffgain = QPushButton(self.verticalLayoutWidget)
        self.btn_setffgain.setObjectName(u"btn_setffgain")

        self.gridLayout.addWidget(self.btn_setffgain, 4, 0, 1, 1)

        self.btn_setff = QPushButton(self.verticalLayoutWidget)
        self.btn_setff.setObjectName(u"btn_setff")

        self.gridLayout.addWidget(self.btn_setff, 4, 1, 1, 1)

        self.combo_image_correction = QComboBox(self.verticalLayoutWidget)
        self.combo_image_correction.setObjectName(u"combo_image_correction")

        self.gridLayout.addWidget(self.combo_image_correction, 2, 0, 1, 2)

        self.chk_scalebar = QCheckBox(self.verticalLayoutWidget)
        self.chk_scalebar.setObjectName(u"chk_scalebar")
        self.chk_scalebar.setChecked(True)

        self.gridLayout.addWidget(self.chk_scalebar, 0, 1, 1, 1)

        self.btn_loadff = QPushButton(self.verticalLayoutWidget)
        self.btn_loadff.setObjectName(u"btn_loadff")

        self.gridLayout.addWidget(self.btn_loadff, 5, 1, 1, 1)

        self.btn_saveff = QPushButton(self.verticalLayoutWidget)
        self.btn_saveff.setObjectName(u"btn_saveff")

        self.gridLayout.addWidget(self.btn_saveff, 5, 0, 1, 1)

        self.chk_crosshair = QCheckBox(self.verticalLayoutWidget)
        self.chk_crosshair.setObjectName(u"chk_crosshair")
        self.chk_crosshair.setChecked(True)

        self.gridLayout.addWidget(self.chk_crosshair, 0, 0, 1, 1)

        self.pushButton_2 = QPushButton(self.verticalLayoutWidget)
        self.pushButton_2.setObjectName(u"pushButton_2")

        self.gridLayout.addWidget(self.pushButton_2, 1, 1, 1, 1)

        self.btn_camera_onoff = QPushButton(self.verticalLayoutWidget)
        self.btn_camera_onoff.setObjectName(u"btn_camera_onoff")
        self.btn_camera_onoff.setStyleSheet(u"background: 'red'")

        self.gridLayout.addWidget(self.btn_camera_onoff, 1, 0, 1, 1)


        self.lyt_main.addLayout(self.gridLayout)

        QWidget.setTabOrder(self.chk_crosshair, self.chk_scalebar)
        QWidget.setTabOrder(self.chk_scalebar, self.btn_camera_onoff)
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
        self.btn_setffgain.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Set flatfield gain", None))
        self.btn_setff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Acquire flatfield correction", None))
        self.chk_scalebar.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Show scalebar", None))
        self.btn_loadff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Load flatfield correction", None))
        self.btn_saveff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Save flatfield correction", None))
        self.chk_crosshair.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Show crosshair", None))
        self.pushButton_2.setText(QCoreApplication.translate("wdg_brightfield_controller", u"PushButton", None))
        self.btn_camera_onoff.setText(QCoreApplication.translate("wdg_brightfield_controller", u"Pause camera feed", None))
    # retranslateUi

