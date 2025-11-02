# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hilvl_coorGen.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_hilvl_coorGen(object):
    def setupUi(self, hilvl_coorGen):
        if not hilvl_coorGen.objectName():
            hilvl_coorGen.setObjectName(u"hilvl_coorGen")
        hilvl_coorGen.resize(683, 519)
        self.tab_coorGenMod = QTabWidget(hilvl_coorGen)
        self.tab_coorGenMod.setObjectName(u"tab_coorGenMod")
        self.tab_coorGenMod.setGeometry(QRect(20, 0, 641, 281))
        self.tab_coorGen = QWidget()
        self.tab_coorGen.setObjectName(u"tab_coorGen")
        self.verticalLayout_2 = QVBoxLayout(self.tab_coorGen)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.combo_coorGen = QComboBox(self.tab_coorGen)
        self.combo_coorGen.setObjectName(u"combo_coorGen")

        self.verticalLayout_2.addWidget(self.combo_coorGen)

        self.wdg_coorGen_holder = QWidget(self.tab_coorGen)
        self.wdg_coorGen_holder.setObjectName(u"wdg_coorGen_holder")

        self.verticalLayout_2.addWidget(self.wdg_coorGen_holder)

        self.tab_coorGenMod.addTab(self.tab_coorGen, "")
        self.tab_coorMod = QWidget()
        self.tab_coorMod.setObjectName(u"tab_coorMod")
        self.verticalLayout = QVBoxLayout(self.tab_coorMod)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.combo_coorMod = QComboBox(self.tab_coorMod)
        self.combo_coorMod.setObjectName(u"combo_coorMod")

        self.verticalLayout.addWidget(self.combo_coorMod)

        self.wdg_coorMod_holder = QWidget(self.tab_coorMod)
        self.wdg_coorMod_holder.setObjectName(u"wdg_coorMod_holder")

        self.verticalLayout.addWidget(self.wdg_coorMod_holder)

        self.tab_coorGenMod.addTab(self.tab_coorMod, "")
        self.wdg_coorHub_holder = QWidget(hilvl_coorGen)
        self.wdg_coorHub_holder.setObjectName(u"wdg_coorHub_holder")
        self.wdg_coorHub_holder.setGeometry(QRect(20, 290, 401, 211))
        self.wdg_3Dmod_holder = QWidget(hilvl_coorGen)
        self.wdg_3Dmod_holder.setObjectName(u"wdg_3Dmod_holder")
        self.wdg_3Dmod_holder.setGeometry(QRect(430, 290, 231, 211))

        self.retranslateUi(hilvl_coorGen)

        self.tab_coorGenMod.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(hilvl_coorGen)
    # setupUi

    def retranslateUi(self, hilvl_coorGen):
        hilvl_coorGen.setWindowTitle(QCoreApplication.translate("hilvl_coorGen", u"Form", None))
        self.tab_coorGenMod.setTabText(self.tab_coorGenMod.indexOf(self.tab_coorGen), QCoreApplication.translate("hilvl_coorGen", u"Basic", None))
        self.tab_coorGenMod.setTabText(self.tab_coorGenMod.indexOf(self.tab_coorMod), QCoreApplication.translate("hilvl_coorGen", u"Advanced (modifier)", None))
    # retranslateUi

