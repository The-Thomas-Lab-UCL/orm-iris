# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'zInterpolate.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_zInterpolate(object):
    def setupUi(self, zInterpolate):
        if not zInterpolate.objectName():
            zInterpolate.setObjectName(u"zInterpolate")
        zInterpolate.resize(1043, 700)
        self.verticalLayout_2 = QVBoxLayout(zInterpolate)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(zInterpolate)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.verticalLayout_3.addWidget(self.label_2)

        self.combo_target = QComboBox(self.groupBox)
        self.combo_target.setObjectName(u"combo_target")

        self.verticalLayout_3.addWidget(self.combo_target)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.verticalLayout_3.addWidget(self.label_3)

        self.combo_reference = QComboBox(self.groupBox)
        self.combo_reference.setObjectName(u"combo_reference")

        self.verticalLayout_3.addWidget(self.combo_reference)


        self.verticalLayout_4.addLayout(self.verticalLayout_3)


        self.main_layout.addWidget(self.groupBox)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(zInterpolate)
        self.label.setObjectName(u"label")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label)

        self.combo_interpMethod = QComboBox(zInterpolate)
        self.combo_interpMethod.setObjectName(u"combo_interpMethod")

        self.horizontalLayout.addWidget(self.combo_interpMethod)


        self.main_layout.addLayout(self.horizontalLayout)

        self.btn_performInterp = QPushButton(zInterpolate)
        self.btn_performInterp.setObjectName(u"btn_performInterp")

        self.main_layout.addWidget(self.btn_performInterp)

        self.btn_instruction = QPushButton(zInterpolate)
        self.btn_instruction.setObjectName(u"btn_instruction")

        self.main_layout.addWidget(self.btn_instruction)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(zInterpolate)

        QMetaObject.connectSlotsByName(zInterpolate)
    # setupUi

    def retranslateUi(self, zInterpolate):
        zInterpolate.setWindowTitle(QCoreApplication.translate("zInterpolate", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("zInterpolate", u"Region of Interest selections:", None))
        self.label_2.setText(QCoreApplication.translate("zInterpolate", u"Target (select the ROI which Z-coordinates are to be modified):", None))
        self.label_3.setText(QCoreApplication.translate("zInterpolate", u"Reference (select the ROI which Z-coordinates are to be used for the interpolation reference):", None))
        self.label.setText(QCoreApplication.translate("zInterpolate", u"Interpolation method:", None))
        self.btn_performInterp.setText(QCoreApplication.translate("zInterpolate", u"Perform interpolation", None))
        self.btn_instruction.setText(QCoreApplication.translate("zInterpolate", u"Show instructions", None))
    # retranslateUi

