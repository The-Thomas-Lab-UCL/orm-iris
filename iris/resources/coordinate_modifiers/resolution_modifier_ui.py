# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'resolution_modifier.ui'
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
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_ResolutionModifier(object):
    def setupUi(self, ResolutionModifier):
        if not ResolutionModifier.objectName():
            ResolutionModifier.setObjectName(u"ResolutionModifier")
        ResolutionModifier.resize(400, 300)
        self.verticalLayout = QVBoxLayout(ResolutionModifier)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.lyt_coorHub = QVBoxLayout()
        self.lyt_coorHub.setObjectName(u"lyt_coorHub")

        self.gridLayout.addLayout(self.lyt_coorHub, 0, 0, 1, 2)

        self.label_2 = QLabel(ResolutionModifier)
        self.label_2.setObjectName(u"label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)

        self.btn_commit = QPushButton(ResolutionModifier)
        self.btn_commit.setObjectName(u"btn_commit")

        self.gridLayout.addWidget(self.btn_commit, 4, 0, 1, 2)

        self.spin_yresUm = QDoubleSpinBox(ResolutionModifier)
        self.spin_yresUm.setObjectName(u"spin_yresUm")
        self.spin_yresUm.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_yresUm, 2, 1, 1, 1)

        self.spin_xresUm = QDoubleSpinBox(ResolutionModifier)
        self.spin_xresUm.setObjectName(u"spin_xresUm")
        self.spin_xresUm.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_xresUm, 1, 1, 1, 1)

        self.label = QLabel(ResolutionModifier)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)

        self.chk_deleteOri = QCheckBox(ResolutionModifier)
        self.chk_deleteOri.setObjectName(u"chk_deleteOri")
        self.chk_deleteOri.setChecked(True)

        self.gridLayout.addWidget(self.chk_deleteOri, 3, 0, 1, 2)


        self.verticalLayout.addLayout(self.gridLayout)

        QWidget.setTabOrder(self.spin_xresUm, self.spin_yresUm)
        QWidget.setTabOrder(self.spin_yresUm, self.chk_deleteOri)
        QWidget.setTabOrder(self.chk_deleteOri, self.btn_commit)

        self.retranslateUi(ResolutionModifier)

        QMetaObject.connectSlotsByName(ResolutionModifier)
    # setupUi

    def retranslateUi(self, ResolutionModifier):
        ResolutionModifier.setWindowTitle(QCoreApplication.translate("ResolutionModifier", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("ResolutionModifier", u"y-resolution:", None))
        self.btn_commit.setText(QCoreApplication.translate("ResolutionModifier", u"Perform resolution modification", None))
        self.spin_yresUm.setSuffix(QCoreApplication.translate("ResolutionModifier", u" \u03bcm", None))
        self.spin_xresUm.setSuffix(QCoreApplication.translate("ResolutionModifier", u" \u03bcm", None))
        self.label.setText(QCoreApplication.translate("ResolutionModifier", u"x-resolution:", None))
        self.chk_deleteOri.setText(QCoreApplication.translate("ResolutionModifier", u"Delete original ROIs", None))
    # retranslateUi

