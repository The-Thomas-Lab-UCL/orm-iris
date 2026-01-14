# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spectrometer_calibration.ui'
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QHeaderView,
    QPushButton, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_spectrometerCalibrator(object):
    def setupUi(self, spectrometerCalibrator):
        if not spectrometerCalibrator.objectName():
            spectrometerCalibrator.setObjectName(u"spectrometerCalibrator")
        spectrometerCalibrator.resize(659, 698)
        self.horizontalLayout_3 = QHBoxLayout(spectrometerCalibrator)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox_3 = QGroupBox(spectrometerCalibrator)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnLoad = QPushButton(self.groupBox_3)
        self.btnLoad.setObjectName(u"btnLoad")

        self.horizontalLayout.addWidget(self.btnLoad)

        self.btnSave = QPushButton(self.groupBox_3)
        self.btnSave.setObjectName(u"btnSave")

        self.horizontalLayout.addWidget(self.btnSave)


        self.verticalLayout_2.addLayout(self.horizontalLayout)


        self.main_layout.addWidget(self.groupBox_3)

        self.groupBox = QGroupBox(spectrometerCalibrator)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.treePixelmap = QTreeWidget(self.groupBox)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.treePixelmap.setHeaderItem(__qtreewidgetitem)
        self.treePixelmap.setObjectName(u"treePixelmap")

        self.horizontalLayout_2.addWidget(self.treePixelmap)

        self.lytPixelmapCanvas = QVBoxLayout()
        self.lytPixelmapCanvas.setObjectName(u"lytPixelmapCanvas")

        self.horizontalLayout_2.addLayout(self.lytPixelmapCanvas)


        self.verticalLayout_6.addLayout(self.horizontalLayout_2)

        self.btnLoadPixelmap = QPushButton(self.groupBox)
        self.btnLoadPixelmap.setObjectName(u"btnLoadPixelmap")

        self.verticalLayout_6.addWidget(self.btnLoadPixelmap)


        self.verticalLayout_3.addLayout(self.verticalLayout_6)


        self.main_layout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(spectrometerCalibrator)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.lytIntensityCanvas = QVBoxLayout()
        self.lytIntensityCanvas.setObjectName(u"lytIntensityCanvas")

        self.verticalLayout_5.addLayout(self.lytIntensityCanvas)

        self.btnLoadIntensity = QPushButton(self.groupBox_2)
        self.btnLoadIntensity.setObjectName(u"btnLoadIntensity")

        self.verticalLayout_5.addWidget(self.btnLoadIntensity)


        self.verticalLayout_4.addLayout(self.verticalLayout_5)


        self.main_layout.addWidget(self.groupBox_2)


        self.horizontalLayout_3.addLayout(self.main_layout)


        self.retranslateUi(spectrometerCalibrator)

        QMetaObject.connectSlotsByName(spectrometerCalibrator)
    # setupUi

    def retranslateUi(self, spectrometerCalibrator):
        spectrometerCalibrator.setWindowTitle(QCoreApplication.translate("spectrometerCalibrator", u"Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("spectrometerCalibrator", u"Calibration file save/load", None))
        self.btnLoad.setText(QCoreApplication.translate("spectrometerCalibrator", u"Load", None))
        self.btnSave.setText(QCoreApplication.translate("spectrometerCalibrator", u"Save", None))
        self.groupBox.setTitle(QCoreApplication.translate("spectrometerCalibrator", u"Wavelength calibration (pixel mapping)", None))
        self.btnLoadPixelmap.setText(QCoreApplication.translate("spectrometerCalibrator", u"Load wavelength calibration file (.csv)", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("spectrometerCalibrator", u"Intensity calibration", None))
        self.btnLoadIntensity.setText(QCoreApplication.translate("spectrometerCalibrator", u"Load intensity calibration file (.csv)", None))
    # retranslateUi

