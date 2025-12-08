# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'point_image.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Point_Image(object):
    def setupUi(self, Point_Image):
        if not Point_Image.objectName():
            Point_Image.setObjectName(u"Point_Image")
        Point_Image.resize(685, 653)
        self.verticalLayout_2 = QVBoxLayout(Point_Image)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(Point_Image)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.lyt_canvas = QVBoxLayout()
        self.lyt_canvas.setObjectName(u"lyt_canvas")

        self.gridLayout.addLayout(self.lyt_canvas, 0, 0, 1, 2)

        self.combo_image = QComboBox(self.groupBox)
        self.combo_image.setObjectName(u"combo_image")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.combo_image.sizePolicy().hasHeightForWidth())
        self.combo_image.setSizePolicy(sizePolicy)

        self.gridLayout.addWidget(self.combo_image, 1, 0, 1, 1)

        self.chk_lres = QCheckBox(self.groupBox)
        self.chk_lres.setObjectName(u"chk_lres")
        self.chk_lres.setChecked(True)

        self.gridLayout.addWidget(self.chk_lres, 2, 0, 1, 2)

        self.btn_instruction = QPushButton(self.groupBox)
        self.btn_instruction.setObjectName(u"btn_instruction")

        self.gridLayout.addWidget(self.btn_instruction, 1, 1, 1, 1)


        self.verticalLayout_3.addLayout(self.gridLayout)


        self.main_layout.addWidget(self.groupBox)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.spin_z = QDoubleSpinBox(Point_Image)
        self.spin_z.setObjectName(u"spin_z")
        self.spin_z.setMinimum(-1000000.000000000000000)
        self.spin_z.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_z, 3, 1, 1, 1)

        self.label_5 = QLabel(Point_Image)
        self.label_5.setObjectName(u"label_5")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy1)
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_5, 3, 0, 1, 1)

        self.label_7 = QLabel(Point_Image)
        self.label_7.setObjectName(u"label_7")
        sizePolicy1.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy1)

        self.gridLayout_2.addWidget(self.label_7, 3, 2, 1, 1)

        self.btn_storeZ = QPushButton(Point_Image)
        self.btn_storeZ.setObjectName(u"btn_storeZ")

        self.gridLayout_2.addWidget(self.btn_storeZ, 3, 3, 1, 2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_4 = QLabel(Point_Image)
        self.label_4.setObjectName(u"label_4")
        sizePolicy1.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_4)

        self.lbl_scanEdges = QLabel(Point_Image)
        self.lbl_scanEdges.setObjectName(u"lbl_scanEdges")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.lbl_scanEdges.sizePolicy().hasHeightForWidth())
        self.lbl_scanEdges.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.lbl_scanEdges)


        self.gridLayout_2.addLayout(self.horizontalLayout, 2, 0, 1, 5)


        self.main_layout.addLayout(self.gridLayout_2)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.combo_image, self.btn_instruction)
        QWidget.setTabOrder(self.btn_instruction, self.chk_lres)
        QWidget.setTabOrder(self.chk_lres, self.spin_z)
        QWidget.setTabOrder(self.spin_z, self.btn_storeZ)

        self.retranslateUi(Point_Image)

        QMetaObject.connectSlotsByName(Point_Image)
    # setupUi

    def retranslateUi(self, Point_Image):
        Point_Image.setWindowTitle(QCoreApplication.translate("Point_Image", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("Point_Image", u"Image-based coordinate selection", None))
        self.chk_lres.setText(QCoreApplication.translate("Point_Image", u"Use low-resolution image (faster processing)", None))
        self.btn_instruction.setText(QCoreApplication.translate("Point_Image", u"Show instructions", None))
        self.label_5.setText(QCoreApplication.translate("Point_Image", u"Z:", None))
        self.label_7.setText(QCoreApplication.translate("Point_Image", u"\u00b5m", None))
        self.btn_storeZ.setText(QCoreApplication.translate("Point_Image", u"Set current Z-coordinate", None))
        self.label_4.setText(QCoreApplication.translate("Point_Image", u"Scan points (\u00b5m):", None))
        self.lbl_scanEdges.setText(QCoreApplication.translate("Point_Image", u"None", None))
    # retranslateUi

