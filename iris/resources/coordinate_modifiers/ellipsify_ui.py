# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ellipsify.ui'
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

class Ui_Ellipsify(object):
    def setupUi(self, Ellipsify):
        if not Ellipsify.objectName():
            Ellipsify.setObjectName(u"Ellipsify")
        Ellipsify.resize(1229, 787)
        self.verticalLayout_2 = QVBoxLayout(Ellipsify)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.lyt_coorhub = QVBoxLayout()
        self.lyt_coorhub.setObjectName(u"lyt_coorhub")

        self.main_layout.addLayout(self.lyt_coorhub)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.chk_deleteori = QCheckBox(Ellipsify)
        self.chk_deleteori.setObjectName(u"chk_deleteori")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.chk_deleteori.sizePolicy().hasHeightForWidth())
        self.chk_deleteori.setSizePolicy(sizePolicy)
        self.chk_deleteori.setChecked(True)

        self.horizontalLayout.addWidget(self.chk_deleteori)

        self.btn_commit = QPushButton(Ellipsify)
        self.btn_commit.setObjectName(u"btn_commit")

        self.horizontalLayout.addWidget(self.btn_commit)


        self.main_layout.addLayout(self.horizontalLayout)

        self.btn_instruction = QPushButton(Ellipsify)
        self.btn_instruction.setObjectName(u"btn_instruction")

        self.main_layout.addWidget(self.btn_instruction)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(Ellipsify)

        QMetaObject.connectSlotsByName(Ellipsify)
    # setupUi

    def retranslateUi(self, Ellipsify):
        Ellipsify.setWindowTitle(QCoreApplication.translate("Ellipsify", u"Form", None))
        self.chk_deleteori.setText(QCoreApplication.translate("Ellipsify", u"Delete original ROIs", None))
        self.btn_commit.setText(QCoreApplication.translate("Ellipsify", u"Convert selected ROI into ellipses", None))
        self.btn_instruction.setText(QCoreApplication.translate("Ellipsify", u"Show instructions", None))
    # retranslateUi

