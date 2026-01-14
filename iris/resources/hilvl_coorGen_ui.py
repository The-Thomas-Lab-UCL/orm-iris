# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hilvl_coorGen.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QPushButton, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_hilvl_coorGen(object):
    def setupUi(self, hilvl_coorGen):
        if not hilvl_coorGen.objectName():
            hilvl_coorGen.setObjectName(u"hilvl_coorGen")
        hilvl_coorGen.resize(501, 348)
        self.verticalLayout_5 = QVBoxLayout(hilvl_coorGen)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.tab_coorGenMod = QTabWidget(hilvl_coorGen)
        self.tab_coorGenMod.setObjectName(u"tab_coorGenMod")
        self.tab_coorGen = QWidget()
        self.tab_coorGen.setObjectName(u"tab_coorGen")
        self.verticalLayout_2 = QVBoxLayout(self.tab_coorGen)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.combo_coorGen = QComboBox(self.tab_coorGen)
        self.combo_coorGen.setObjectName(u"combo_coorGen")

        self.verticalLayout_2.addWidget(self.combo_coorGen)

        self.wdg_coorGen_holder = QWidget(self.tab_coorGen)
        self.wdg_coorGen_holder.setObjectName(u"wdg_coorGen_holder")
        self.gridLayout = QGridLayout(self.wdg_coorGen_holder)
        self.gridLayout.setObjectName(u"gridLayout")
        self.lyt_coorGen_holder = QVBoxLayout()
        self.lyt_coorGen_holder.setObjectName(u"lyt_coorGen_holder")

        self.gridLayout.addLayout(self.lyt_coorGen_holder, 0, 0, 1, 1)


        self.verticalLayout_2.addWidget(self.wdg_coorGen_holder)

        self.wdg_3Dmod_holder = QGroupBox(self.tab_coorGen)
        self.wdg_3Dmod_holder.setObjectName(u"wdg_3Dmod_holder")
        self.verticalLayout_8 = QVBoxLayout(self.wdg_3Dmod_holder)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.lyt_3Dmod_holder = QVBoxLayout()
        self.lyt_3Dmod_holder.setObjectName(u"lyt_3Dmod_holder")

        self.verticalLayout_8.addLayout(self.lyt_3Dmod_holder)


        self.verticalLayout_2.addWidget(self.wdg_3Dmod_holder)

        self.tab_coorGenMod.addTab(self.tab_coorGen, "")
        self.tab_coorMod = QWidget()
        self.tab_coorMod.setObjectName(u"tab_coorMod")
        self.verticalLayout = QVBoxLayout(self.tab_coorMod)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lyt_coorMod_holder = QVBoxLayout()
        self.lyt_coorMod_holder.setObjectName(u"lyt_coorMod_holder")

        self.verticalLayout.addLayout(self.lyt_coorMod_holder)

        self.tab_coorGenMod.addTab(self.tab_coorMod, "")

        self.verticalLayout_4.addWidget(self.tab_coorGenMod)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_gen_2Dcoor = QPushButton(hilvl_coorGen)
        self.btn_gen_2Dcoor.setObjectName(u"btn_gen_2Dcoor")

        self.horizontalLayout.addWidget(self.btn_gen_2Dcoor)

        self.btn_gen_3Dcoor = QPushButton(hilvl_coorGen)
        self.btn_gen_3Dcoor.setObjectName(u"btn_gen_3Dcoor")

        self.horizontalLayout.addWidget(self.btn_gen_3Dcoor)


        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.wdg_coorHub_holder = QWidget(hilvl_coorGen)
        self.wdg_coorHub_holder.setObjectName(u"wdg_coorHub_holder")
        self.verticalLayout_7 = QVBoxLayout(self.wdg_coorHub_holder)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.lyt_coorHub_holder = QVBoxLayout()
        self.lyt_coorHub_holder.setObjectName(u"lyt_coorHub_holder")

        self.verticalLayout_7.addLayout(self.lyt_coorHub_holder)


        self.verticalLayout_4.addWidget(self.wdg_coorHub_holder)


        self.verticalLayout_5.addLayout(self.verticalLayout_4)


        self.retranslateUi(hilvl_coorGen)

        self.tab_coorGenMod.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(hilvl_coorGen)
    # setupUi

    def retranslateUi(self, hilvl_coorGen):
        hilvl_coorGen.setWindowTitle(QCoreApplication.translate("hilvl_coorGen", u"Form", None))
        self.wdg_3Dmod_holder.setTitle(QCoreApplication.translate("hilvl_coorGen", u"2D to 3D ROI conversion parameters", None))
        self.tab_coorGenMod.setTabText(self.tab_coorGenMod.indexOf(self.tab_coorGen), QCoreApplication.translate("hilvl_coorGen", u"Basic", None))
        self.tab_coorGenMod.setTabText(self.tab_coorGenMod.indexOf(self.tab_coorMod), QCoreApplication.translate("hilvl_coorGen", u"Advanced (modifier)", None))
        self.btn_gen_2Dcoor.setText(QCoreApplication.translate("hilvl_coorGen", u"Generate 2D ROI", None))
        self.btn_gen_3Dcoor.setText(QCoreApplication.translate("hilvl_coorGen", u"Generate 3D ROI", None))
    # retranslateUi

