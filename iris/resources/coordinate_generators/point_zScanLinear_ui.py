# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'point_zScanLinear.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_singlePointZScan(object):
    def setupUi(self, singlePointZScan):
        if not singlePointZScan.objectName():
            singlePointZScan.setObjectName(u"singlePointZScan")
        singlePointZScan.resize(684, 621)
        self.verticalLayout_2 = QVBoxLayout(singlePointZScan)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_4 = QLabel(singlePointZScan)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.label_3 = QLabel(singlePointZScan)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.label = QLabel(singlePointZScan)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_2 = QLabel(singlePointZScan)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label_5 = QLabel(singlePointZScan)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)

        self.btn_storeXY = QPushButton(singlePointZScan)
        self.btn_storeXY.setObjectName(u"btn_storeXY")

        self.gridLayout.addWidget(self.btn_storeXY, 0, 3, 1, 1)

        self.btn_storeZEnd = QPushButton(singlePointZScan)
        self.btn_storeZEnd.setObjectName(u"btn_storeZEnd")

        self.gridLayout.addWidget(self.btn_storeZEnd, 2, 2, 1, 2)

        self.btn_storeZStart = QPushButton(singlePointZScan)
        self.btn_storeZStart.setObjectName(u"btn_storeZStart")

        self.gridLayout.addWidget(self.btn_storeZStart, 1, 2, 1, 2)

        self.spin_coorx = QDoubleSpinBox(singlePointZScan)
        self.spin_coorx.setObjectName(u"spin_coorx")
        self.spin_coorx.setDecimals(1)
        self.spin_coorx.setMinimum(-1000000.000000000000000)
        self.spin_coorx.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coorx, 0, 1, 1, 1)

        self.spin_coory = QDoubleSpinBox(singlePointZScan)
        self.spin_coory.setObjectName(u"spin_coory")
        self.spin_coory.setDecimals(1)
        self.spin_coory.setMinimum(-1000000.000000000000000)
        self.spin_coory.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coory, 0, 2, 1, 1)

        self.spin_coorZStart = QDoubleSpinBox(singlePointZScan)
        self.spin_coorZStart.setObjectName(u"spin_coorZStart")
        self.spin_coorZStart.setDecimals(1)
        self.spin_coorZStart.setMinimum(-1000000.000000000000000)
        self.spin_coorZStart.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coorZStart, 1, 1, 1, 1)

        self.spin_coorZEnd = QDoubleSpinBox(singlePointZScan)
        self.spin_coorZEnd.setObjectName(u"spin_coorZEnd")
        self.spin_coorZEnd.setDecimals(1)
        self.spin_coorZEnd.setMinimum(-1000000.000000000000000)
        self.spin_coorZEnd.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coorZEnd, 2, 1, 1, 1)

        self.spin_resUm = QDoubleSpinBox(singlePointZScan)
        self.spin_resUm.setObjectName(u"spin_resUm")
        self.spin_resUm.setDecimals(1)
        self.spin_resUm.setMaximum(1000000.000000000000000)
        self.spin_resUm.setValue(1.000000000000000)

        self.gridLayout.addWidget(self.spin_resUm, 4, 1, 1, 1)

        self.spin_resPt = QSpinBox(singlePointZScan)
        self.spin_resPt.setObjectName(u"spin_resPt")
        self.spin_resPt.setMinimum(1)
        self.spin_resPt.setMaximum(1000000)
        self.spin_resPt.setValue(2)

        self.gridLayout.addWidget(self.spin_resPt, 3, 1, 1, 1)


        self.main_layout.addLayout(self.gridLayout)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.spin_coorx, self.spin_coory)
        QWidget.setTabOrder(self.spin_coory, self.btn_storeXY)
        QWidget.setTabOrder(self.btn_storeXY, self.spin_coorZStart)
        QWidget.setTabOrder(self.spin_coorZStart, self.btn_storeZStart)
        QWidget.setTabOrder(self.btn_storeZStart, self.spin_coorZEnd)
        QWidget.setTabOrder(self.spin_coorZEnd, self.btn_storeZEnd)
        QWidget.setTabOrder(self.btn_storeZEnd, self.spin_resPt)
        QWidget.setTabOrder(self.spin_resPt, self.spin_resUm)

        self.retranslateUi(singlePointZScan)

        QMetaObject.connectSlotsByName(singlePointZScan)
    # setupUi

    def retranslateUi(self, singlePointZScan):
        singlePointZScan.setWindowTitle(QCoreApplication.translate("singlePointZScan", u"Form", None))
        self.label_4.setText(QCoreApplication.translate("singlePointZScan", u"Mapping resolution (points):", None))
        self.label_3.setText(QCoreApplication.translate("singlePointZScan", u"End Z-coordinate (\u00b5m):", None))
        self.label.setText(QCoreApplication.translate("singlePointZScan", u"Scan coordinates (X,Y) (\u00b5m):", None))
        self.label_2.setText(QCoreApplication.translate("singlePointZScan", u"Start Z-coordinate (\u00b5m):", None))
        self.label_5.setText(QCoreApplication.translate("singlePointZScan", u"Mapping resolution (\u00b5m):", None))
        self.btn_storeXY.setText(QCoreApplication.translate("singlePointZScan", u"Store current coordinate", None))
        self.btn_storeZEnd.setText(QCoreApplication.translate("singlePointZScan", u"Store current coordinate", None))
        self.btn_storeZStart.setText(QCoreApplication.translate("singlePointZScan", u"Store current coordinate", None))
    # retranslateUi

