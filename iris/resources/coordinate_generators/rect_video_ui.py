# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rect_video.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

class Ui_Rect_Video(object):
    def setupUi(self, Rect_Video):
        if not Rect_Video.objectName():
            Rect_Video.setObjectName(u"Rect_Video")
        Rect_Video.resize(685, 653)
        self.verticalLayout_2 = QVBoxLayout(Rect_Video)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(Rect_Video)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.chk_lres = QCheckBox(self.groupBox)
        self.chk_lres.setObjectName(u"chk_lres")
        self.chk_lres.setChecked(True)

        self.gridLayout.addWidget(self.chk_lres, 2, 0, 1, 2)

        self.lyt_canvas = QVBoxLayout()
        self.lyt_canvas.setObjectName(u"lyt_canvas")

        self.gridLayout.addLayout(self.lyt_canvas, 0, 0, 1, 2)

        self.btn_defineROI = QPushButton(self.groupBox)
        self.btn_defineROI.setObjectName(u"btn_defineROI")

        self.gridLayout.addWidget(self.btn_defineROI, 1, 0, 1, 1)

        self.btn_instruction = QPushButton(self.groupBox)
        self.btn_instruction.setObjectName(u"btn_instruction")

        self.gridLayout.addWidget(self.btn_instruction, 1, 1, 1, 1)


        self.verticalLayout_3.addLayout(self.gridLayout)


        self.main_layout.addWidget(self.groupBox)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_11 = QLabel(Rect_Video)
        self.label_11.setObjectName(u"label_11")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_11.sizePolicy().hasHeightForWidth())
        self.label_11.setSizePolicy(sizePolicy)
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_11, 6, 0, 1, 1)

        self.label_9 = QLabel(Rect_Video)
        self.label_9.setObjectName(u"label_9")
        sizePolicy.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_9, 5, 0, 1, 1)

        self.spin_resXum = QDoubleSpinBox(Rect_Video)
        self.spin_resXum.setObjectName(u"spin_resXum")
        self.spin_resXum.setMinimum(-1000000.000000000000000)
        self.spin_resXum.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_resXum, 6, 1, 1, 1)

        self.label_5 = QLabel(Rect_Video)
        self.label_5.setObjectName(u"label_5")
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_5, 3, 0, 1, 1)

        self.spin_resXPt = QSpinBox(Rect_Video)
        self.spin_resXPt.setObjectName(u"spin_resXPt")
        self.spin_resXPt.setMinimum(1)
        self.spin_resXPt.setMaximum(1000000)

        self.gridLayout_2.addWidget(self.spin_resXPt, 5, 1, 1, 1)

        self.spin_z = QDoubleSpinBox(Rect_Video)
        self.spin_z.setObjectName(u"spin_z")
        self.spin_z.setMinimum(-1000000.000000000000000)
        self.spin_z.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_z, 3, 1, 1, 1)

        self.label_10 = QLabel(Rect_Video)
        self.label_10.setObjectName(u"label_10")
        sizePolicy.setHeightForWidth(self.label_10.sizePolicy().hasHeightForWidth())
        self.label_10.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_10, 5, 2, 1, 1)

        self.label_12 = QLabel(Rect_Video)
        self.label_12.setObjectName(u"label_12")
        sizePolicy.setHeightForWidth(self.label_12.sizePolicy().hasHeightForWidth())
        self.label_12.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_12, 6, 2, 1, 1)

        self.label_7 = QLabel(Rect_Video)
        self.label_7.setObjectName(u"label_7")
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_7, 3, 2, 1, 1)

        self.label_13 = QLabel(Rect_Video)
        self.label_13.setObjectName(u"label_13")
        sizePolicy.setHeightForWidth(self.label_13.sizePolicy().hasHeightForWidth())
        self.label_13.setSizePolicy(sizePolicy)
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_13, 5, 3, 1, 1)

        self.label_8 = QLabel(Rect_Video)
        self.label_8.setObjectName(u"label_8")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy1)

        self.gridLayout_2.addWidget(self.label_8, 4, 0, 1, 6)

        self.spin_resYPt = QSpinBox(Rect_Video)
        self.spin_resYPt.setObjectName(u"spin_resYPt")
        self.spin_resYPt.setMinimum(1)
        self.spin_resYPt.setMaximum(1000000)

        self.gridLayout_2.addWidget(self.spin_resYPt, 5, 4, 1, 1)

        self.label_14 = QLabel(Rect_Video)
        self.label_14.setObjectName(u"label_14")
        sizePolicy.setHeightForWidth(self.label_14.sizePolicy().hasHeightForWidth())
        self.label_14.setSizePolicy(sizePolicy)
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_14, 6, 3, 1, 1)

        self.spin_resYum = QDoubleSpinBox(Rect_Video)
        self.spin_resYum.setObjectName(u"spin_resYum")
        self.spin_resYum.setMinimum(-1000000.000000000000000)
        self.spin_resYum.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_resYum, 6, 4, 1, 1)

        self.label_16 = QLabel(Rect_Video)
        self.label_16.setObjectName(u"label_16")
        sizePolicy.setHeightForWidth(self.label_16.sizePolicy().hasHeightForWidth())
        self.label_16.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_16, 6, 5, 1, 1)

        self.label_15 = QLabel(Rect_Video)
        self.label_15.setObjectName(u"label_15")
        sizePolicy.setHeightForWidth(self.label_15.sizePolicy().hasHeightForWidth())
        self.label_15.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_15, 5, 5, 1, 1)

        self.btn_storeZ = QPushButton(Rect_Video)
        self.btn_storeZ.setObjectName(u"btn_storeZ")

        self.gridLayout_2.addWidget(self.btn_storeZ, 3, 3, 1, 3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_4 = QLabel(Rect_Video)
        self.label_4.setObjectName(u"label_4")
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_4)

        self.lbl_scanEdges = QLabel(Rect_Video)
        self.lbl_scanEdges.setObjectName(u"lbl_scanEdges")
        sizePolicy1.setHeightForWidth(self.lbl_scanEdges.sizePolicy().hasHeightForWidth())
        self.lbl_scanEdges.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.lbl_scanEdges)


        self.gridLayout_2.addLayout(self.horizontalLayout, 2, 0, 1, 6)


        self.main_layout.addLayout(self.gridLayout_2)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.btn_defineROI, self.btn_instruction)
        QWidget.setTabOrder(self.btn_instruction, self.chk_lres)
        QWidget.setTabOrder(self.chk_lres, self.spin_z)
        QWidget.setTabOrder(self.spin_z, self.btn_storeZ)
        QWidget.setTabOrder(self.btn_storeZ, self.spin_resXPt)
        QWidget.setTabOrder(self.spin_resXPt, self.spin_resYPt)
        QWidget.setTabOrder(self.spin_resYPt, self.spin_resXum)
        QWidget.setTabOrder(self.spin_resXum, self.spin_resYum)

        self.retranslateUi(Rect_Video)

        QMetaObject.connectSlotsByName(Rect_Video)
    # setupUi

    def retranslateUi(self, Rect_Video):
        Rect_Video.setWindowTitle(QCoreApplication.translate("Rect_Video", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("Rect_Video", u"Image-based coordinate selection", None))
        self.chk_lres.setText(QCoreApplication.translate("Rect_Video", u"Show low-resolution image (faster processing)", None))
        self.btn_defineROI.setText(QCoreApplication.translate("Rect_Video", u"Define ROI", None))
        self.btn_instruction.setText(QCoreApplication.translate("Rect_Video", u"Show instructions", None))
        self.label_11.setText(QCoreApplication.translate("Rect_Video", u"X:", None))
        self.label_9.setText(QCoreApplication.translate("Rect_Video", u"X:", None))
        self.label_5.setText(QCoreApplication.translate("Rect_Video", u"Z:", None))
        self.label_10.setText(QCoreApplication.translate("Rect_Video", u"points", None))
        self.label_12.setText(QCoreApplication.translate("Rect_Video", u"\u00b5m", None))
        self.label_7.setText(QCoreApplication.translate("Rect_Video", u"\u00b5m", None))
        self.label_13.setText(QCoreApplication.translate("Rect_Video", u"Y:", None))
        self.label_8.setText(QCoreApplication.translate("Rect_Video", u"Imaging resolution:", None))
        self.label_14.setText(QCoreApplication.translate("Rect_Video", u"Y:", None))
        self.label_16.setText(QCoreApplication.translate("Rect_Video", u"\u00b5m", None))
        self.label_15.setText(QCoreApplication.translate("Rect_Video", u"points", None))
        self.btn_storeZ.setText(QCoreApplication.translate("Rect_Video", u"Set current Z-coordinate", None))
        self.label_4.setText(QCoreApplication.translate("Rect_Video", u"Scan edges (\u00b5m):", None))
        self.lbl_scanEdges.setText(QCoreApplication.translate("Rect_Video", u"None", None))
    # retranslateUi

