# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'multiTranslatorXYZ.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_MultiTranslatorXYZ(object):
    def setupUi(self, MultiTranslatorXYZ):
        if not MultiTranslatorXYZ.objectName():
            MultiTranslatorXYZ.setObjectName(u"MultiTranslatorXYZ")
        MultiTranslatorXYZ.resize(717, 546)
        self.verticalLayout_2 = QVBoxLayout(MultiTranslatorXYZ)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.lyt_coorhub = QVBoxLayout()
        self.lyt_coorhub.setObjectName(u"lyt_coorhub")

        self.main_layout.addLayout(self.lyt_coorhub)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(MultiTranslatorXYZ)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.label)

        self.spin_x_um = QDoubleSpinBox(MultiTranslatorXYZ)
        self.spin_x_um.setObjectName(u"spin_x_um")
        self.spin_x_um.setDecimals(1)
        self.spin_x_um.setMinimum(-1000000.000000000000000)
        self.spin_x_um.setMaximum(1000000.000000000000000)

        self.horizontalLayout_2.addWidget(self.spin_x_um)

        self.spin_y_um = QDoubleSpinBox(MultiTranslatorXYZ)
        self.spin_y_um.setObjectName(u"spin_y_um")
        self.spin_y_um.setDecimals(1)
        self.spin_y_um.setMinimum(-1000000.000000000000000)
        self.spin_y_um.setValue(0.000000000000000)

        self.horizontalLayout_2.addWidget(self.spin_y_um)

        self.spin_z_um = QDoubleSpinBox(MultiTranslatorXYZ)
        self.spin_z_um.setObjectName(u"spin_z_um")
        self.spin_z_um.setDecimals(1)
        self.spin_z_um.setMinimum(-1000000.000000000000000)
        self.spin_z_um.setMaximum(1000000.000000000000000)

        self.horizontalLayout_2.addWidget(self.spin_z_um)

        self.label_2 = QLabel(MultiTranslatorXYZ)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.label_2)


        self.main_layout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.chk_deleteori = QCheckBox(MultiTranslatorXYZ)
        self.chk_deleteori.setObjectName(u"chk_deleteori")
        sizePolicy.setHeightForWidth(self.chk_deleteori.sizePolicy().hasHeightForWidth())
        self.chk_deleteori.setSizePolicy(sizePolicy)
        self.chk_deleteori.setChecked(True)

        self.horizontalLayout.addWidget(self.chk_deleteori)

        self.btn_commit = QPushButton(MultiTranslatorXYZ)
        self.btn_commit.setObjectName(u"btn_commit")

        self.horizontalLayout.addWidget(self.btn_commit)


        self.main_layout.addLayout(self.horizontalLayout)

        self.btn_instruction = QPushButton(MultiTranslatorXYZ)
        self.btn_instruction.setObjectName(u"btn_instruction")

        self.main_layout.addWidget(self.btn_instruction)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(MultiTranslatorXYZ)

        QMetaObject.connectSlotsByName(MultiTranslatorXYZ)
    # setupUi

    def retranslateUi(self, MultiTranslatorXYZ):
        MultiTranslatorXYZ.setWindowTitle(QCoreApplication.translate("MultiTranslatorXYZ", u"Form", None))
        self.label.setText(QCoreApplication.translate("MultiTranslatorXYZ", u"Translate the coordinates by (x, y, z):", None))
        self.label_2.setText(QCoreApplication.translate("MultiTranslatorXYZ", u"\u00b5m", None))
        self.chk_deleteori.setText(QCoreApplication.translate("MultiTranslatorXYZ", u"Delete original ROIs", None))
        self.btn_commit.setText(QCoreApplication.translate("MultiTranslatorXYZ", u"Translate the selected ROIs", None))
        self.btn_instruction.setText(QCoreApplication.translate("MultiTranslatorXYZ", u"Show instructions", None))
    # retranslateUi

