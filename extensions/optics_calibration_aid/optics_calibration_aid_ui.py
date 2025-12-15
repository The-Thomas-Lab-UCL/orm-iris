# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'optics_calibration_aid.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

class Ui_optics_calibration_aid(object):
    def setupUi(self, optics_calibration_aid):
        if not optics_calibration_aid.objectName():
            optics_calibration_aid.setObjectName(u"optics_calibration_aid")
        optics_calibration_aid.resize(756, 567)
        self.verticalLayout_2 = QVBoxLayout(optics_calibration_aid)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.lyt_plot = QVBoxLayout()
        self.lyt_plot.setObjectName(u"lyt_plot")

        self.main_layout.addLayout(self.lyt_plot)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_start = QPushButton(optics_calibration_aid)
        self.btn_start.setObjectName(u"btn_start")

        self.horizontalLayout_2.addWidget(self.btn_start)

        self.btn_stop = QPushButton(optics_calibration_aid)
        self.btn_stop.setObjectName(u"btn_stop")

        self.horizontalLayout_2.addWidget(self.btn_stop)

        self.btn_restart = QPushButton(optics_calibration_aid)
        self.btn_restart.setObjectName(u"btn_restart")

        self.horizontalLayout_2.addWidget(self.btn_restart)


        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(optics_calibration_aid)
        self.label_3.setObjectName(u"label_3")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.label_3)

        self.spin_numTrack = QSpinBox(optics_calibration_aid)
        self.spin_numTrack.setObjectName(u"spin_numTrack")
        self.spin_numTrack.setMinimum(1)
        self.spin_numTrack.setMaximum(1000)
        self.spin_numTrack.setValue(100)

        self.horizontalLayout_3.addWidget(self.spin_numTrack)

        self.chk_storeMax = QCheckBox(optics_calibration_aid)
        self.chk_storeMax.setObjectName(u"chk_storeMax")
        self.chk_storeMax.setChecked(True)

        self.horizontalLayout_3.addWidget(self.chk_storeMax)

        self.chk_ymin0 = QCheckBox(optics_calibration_aid)
        self.chk_ymin0.setObjectName(u"chk_ymin0")
        self.chk_ymin0.setChecked(True)

        self.horizontalLayout_3.addWidget(self.chk_ymin0)


        self.verticalLayout_3.addLayout(self.horizontalLayout_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.groupBox = QGroupBox(optics_calibration_aid)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.rad_plotAUC = QRadioButton(self.groupBox)
        self.rad_plotAUC.setObjectName(u"rad_plotAUC")
        self.rad_plotAUC.setChecked(True)

        self.verticalLayout_5.addWidget(self.rad_plotAUC)

        self.rad_plotOneWavenumber = QRadioButton(self.groupBox)
        self.rad_plotOneWavenumber.setObjectName(u"rad_plotOneWavenumber")

        self.verticalLayout_5.addWidget(self.rad_plotOneWavenumber)


        self.verticalLayout_4.addLayout(self.verticalLayout_5)


        self.horizontalLayout.addWidget(self.groupBox)

        self.label = QLabel(optics_calibration_aid)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label)

        self.spin_RamanWavenumber = QDoubleSpinBox(optics_calibration_aid)
        self.spin_RamanWavenumber.setObjectName(u"spin_RamanWavenumber")
        self.spin_RamanWavenumber.setMinimum(-10000.000000000000000)
        self.spin_RamanWavenumber.setMaximum(10000.000000000000000)
        self.spin_RamanWavenumber.setValue(520.000000000000000)

        self.horizontalLayout.addWidget(self.spin_RamanWavenumber)

        self.label_2 = QLabel(optics_calibration_aid)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_2)


        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.chk_alwaysOnTop = QCheckBox(optics_calibration_aid)
        self.chk_alwaysOnTop.setObjectName(u"chk_alwaysOnTop")
        self.chk_alwaysOnTop.setChecked(True)

        self.verticalLayout_3.addWidget(self.chk_alwaysOnTop)


        self.main_layout.addLayout(self.verticalLayout_3)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(optics_calibration_aid)

        QMetaObject.connectSlotsByName(optics_calibration_aid)
    # setupUi

    def retranslateUi(self, optics_calibration_aid):
        optics_calibration_aid.setWindowTitle(QCoreApplication.translate("optics_calibration_aid", u"Form", None))
        self.btn_start.setText(QCoreApplication.translate("optics_calibration_aid", u"Start", None))
        self.btn_stop.setText(QCoreApplication.translate("optics_calibration_aid", u"Stop", None))
        self.btn_restart.setText(QCoreApplication.translate("optics_calibration_aid", u"Restart", None))
        self.label_3.setText(QCoreApplication.translate("optics_calibration_aid", u"Number of points to track:", None))
        self.chk_storeMax.setText(QCoreApplication.translate("optics_calibration_aid", u"Store the maximum of all time", None))
        self.chk_ymin0.setText(QCoreApplication.translate("optics_calibration_aid", u"Force Y-minimum = 0", None))
        self.groupBox.setTitle("")
        self.rad_plotAUC.setText(QCoreApplication.translate("optics_calibration_aid", u"Track area under spectrum", None))
        self.rad_plotOneWavenumber.setText(QCoreApplication.translate("optics_calibration_aid", u"Track intensity of specific wavenumber", None))
        self.label.setText(QCoreApplication.translate("optics_calibration_aid", u"Raman wavenumber:", None))
        self.label_2.setText(QCoreApplication.translate("optics_calibration_aid", u"cm<sup>-1<sup>", None))
        self.chk_alwaysOnTop.setText(QCoreApplication.translate("optics_calibration_aid", u"Always on top (window)", None))
    # retranslateUi

