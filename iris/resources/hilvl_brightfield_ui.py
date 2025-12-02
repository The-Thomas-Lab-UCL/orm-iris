# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hilvl_brightfield.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QSizePolicy, QTabWidget,
    QVBoxLayout, QWidget)

class Ui_Hilvl_Brightfield(object):
    def setupUi(self, Hilvl_Brightfield):
        if not Hilvl_Brightfield.objectName():
            Hilvl_Brightfield.setObjectName(u"Hilvl_Brightfield")
        Hilvl_Brightfield.resize(699, 561)
        self.verticalLayout_2 = QVBoxLayout(Hilvl_Brightfield)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.tabWidget = QTabWidget(Hilvl_Brightfield)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab_captureDisplay = QWidget()
        self.tab_captureDisplay.setObjectName(u"tab_captureDisplay")
        self.horizontalLayout = QHBoxLayout(self.tab_captureDisplay)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.wdg_holder_capDisp = QWidget(self.tab_captureDisplay)
        self.wdg_holder_capDisp.setObjectName(u"wdg_holder_capDisp")
        self.lyt_holder_imgCapDisp = QVBoxLayout(self.wdg_holder_capDisp)
        self.lyt_holder_imgCapDisp.setObjectName(u"lyt_holder_imgCapDisp")

        self.horizontalLayout.addWidget(self.wdg_holder_capDisp)

        self.tabWidget.addTab(self.tab_captureDisplay, "")
        self.tab_heatmapOverlay = QWidget()
        self.tab_heatmapOverlay.setObjectName(u"tab_heatmapOverlay")
        self.verticalLayout_5 = QVBoxLayout(self.tab_heatmapOverlay)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.wdg_holder_heatmapOverlay = QWidget(self.tab_heatmapOverlay)
        self.wdg_holder_heatmapOverlay.setObjectName(u"wdg_holder_heatmapOverlay")
        self.lyt_holder_heatmapOverlay = QVBoxLayout(self.wdg_holder_heatmapOverlay)
        self.lyt_holder_heatmapOverlay.setObjectName(u"lyt_holder_heatmapOverlay")

        self.verticalLayout_5.addWidget(self.wdg_holder_heatmapOverlay)

        self.tabWidget.addTab(self.tab_heatmapOverlay, "")
        self.tab_objectiveSetup = QWidget()
        self.tab_objectiveSetup.setObjectName(u"tab_objectiveSetup")
        self.verticalLayout_7 = QVBoxLayout(self.tab_objectiveSetup)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.lyt_holder_objSetup = QVBoxLayout()
        self.lyt_holder_objSetup.setObjectName(u"lyt_holder_objSetup")

        self.verticalLayout_7.addLayout(self.lyt_holder_objSetup)

        self.tabWidget.addTab(self.tab_objectiveSetup, "")

        self.main_layout.addWidget(self.tabWidget)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(Hilvl_Brightfield)

        self.tabWidget.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(Hilvl_Brightfield)
    # setupUi

    def retranslateUi(self, Hilvl_Brightfield):
        Hilvl_Brightfield.setWindowTitle(QCoreApplication.translate("Hilvl_Brightfield", u"Form", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_captureDisplay), QCoreApplication.translate("Hilvl_Brightfield", u"Image capture and display", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_heatmapOverlay), QCoreApplication.translate("Hilvl_Brightfield", u"Heatmap overlay", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_objectiveSetup), QCoreApplication.translate("Hilvl_Brightfield", u"Objective setup", None))
    # retranslateUi

