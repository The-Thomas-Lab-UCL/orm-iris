# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'objective_calibration_main.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_calibration_main(object):
    def setupUi(self, calibration_main):
        if not calibration_main.objectName():
            calibration_main.setObjectName(u"calibration_main")
        calibration_main.resize(859, 555)
        self.horizontalLayout_4 = QHBoxLayout(calibration_main)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.main_layout = QHBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.wdg_holder_canvas = QWidget(calibration_main)
        self.wdg_holder_canvas.setObjectName(u"wdg_holder_canvas")
        self.holder_canvas = QHBoxLayout(self.wdg_holder_canvas)
        self.holder_canvas.setObjectName(u"holder_canvas")

        self.verticalLayout.addWidget(self.wdg_holder_canvas)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.chk_lres = QCheckBox(calibration_main)
        self.chk_lres.setObjectName(u"chk_lres")

        self.horizontalLayout_2.addWidget(self.chk_lres)

        self.btn_showimage = QPushButton(calibration_main)
        self.btn_showimage.setObjectName(u"btn_showimage")

        self.horizontalLayout_2.addWidget(self.btn_showimage)

        self.btn_refresh = QPushButton(calibration_main)
        self.btn_refresh.setObjectName(u"btn_refresh")

        self.horizontalLayout_2.addWidget(self.btn_refresh)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.btn_capture = QPushButton(calibration_main)
        self.btn_capture.setObjectName(u"btn_capture")

        self.horizontalLayout_3.addWidget(self.btn_capture)

        self.btn_resetcapture = QPushButton(calibration_main)
        self.btn_resetcapture.setObjectName(u"btn_resetcapture")

        self.horizontalLayout_3.addWidget(self.btn_resetcapture)

        self.btn_savecaptured = QPushButton(calibration_main)
        self.btn_savecaptured.setObjectName(u"btn_savecaptured")

        self.horizontalLayout_3.addWidget(self.btn_savecaptured)


        self.verticalLayout.addLayout(self.horizontalLayout_3)


        self.main_layout.addLayout(self.verticalLayout)

        self.lyt_holder_calibration_controls = QVBoxLayout()
        self.lyt_holder_calibration_controls.setObjectName(u"lyt_holder_calibration_controls")

        self.main_layout.addLayout(self.lyt_holder_calibration_controls)


        self.horizontalLayout_4.addLayout(self.main_layout)


        self.retranslateUi(calibration_main)

        QMetaObject.connectSlotsByName(calibration_main)
    # setupUi

    def retranslateUi(self, calibration_main):
        calibration_main.setWindowTitle(QCoreApplication.translate("calibration_main", u"Form", None))
        self.chk_lres.setText(QCoreApplication.translate("calibration_main", u"Show low-resolution image\n"
"(faster processing)", None))
        self.btn_showimage.setText(QCoreApplication.translate("calibration_main", u"Show image", None))
        self.btn_refresh.setText(QCoreApplication.translate("calibration_main", u"Refresh live-feed", None))
        self.btn_capture.setText(QCoreApplication.translate("calibration_main", u"Capture image", None))
        self.btn_resetcapture.setText(QCoreApplication.translate("calibration_main", u"Reset capture", None))
        self.btn_savecaptured.setText(QCoreApplication.translate("calibration_main", u"Save captured image\n"
"to DataHub", None))
    # retranslateUi

