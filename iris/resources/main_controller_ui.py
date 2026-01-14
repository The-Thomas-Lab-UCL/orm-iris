# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_controller.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow, QMenuBar,
    QSizePolicy, QStatusBar, QTabWidget, QVBoxLayout,
    QWidget)

class Ui_main_controller(object):
    def setupUi(self, main_controller):
        if not main_controller.objectName():
            main_controller.setObjectName(u"main_controller")
        main_controller.resize(800, 600)
        self.centralwidget = QWidget(main_controller)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QHBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lytObjCalHub = QVBoxLayout()
        self.lytObjCalHub.setObjectName(u"lytObjCalHub")

        self.verticalLayout_3.addLayout(self.lytObjCalHub)

        self.lytMotionVideo = QVBoxLayout()
        self.lytMotionVideo.setObjectName(u"lytMotionVideo")

        self.verticalLayout_3.addLayout(self.lytMotionVideo)


        self.main_layout.addLayout(self.verticalLayout_3)

        self.lytRaman = QVBoxLayout()
        self.lytRaman.setObjectName(u"lytRaman")

        self.main_layout.addLayout(self.lytRaman)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_8 = QVBoxLayout(self.tab)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.lytCoorGen = QVBoxLayout()
        self.lytCoorGen.setObjectName(u"lytCoorGen")

        self.verticalLayout_8.addLayout(self.lytCoorGen)

        self.tabWidget.addTab(self.tab, "")
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.verticalLayout_9 = QVBoxLayout(self.tab_3)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.lytRamanMapping = QVBoxLayout()
        self.lytRamanMapping.setObjectName(u"lytRamanMapping")

        self.verticalLayout_9.addLayout(self.lytRamanMapping)

        self.tabWidget.addTab(self.tab_3, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.verticalLayout_10 = QVBoxLayout(self.tab_4)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.lytBrightfield = QVBoxLayout()
        self.lytBrightfield.setObjectName(u"lytBrightfield")

        self.verticalLayout_10.addLayout(self.lytBrightfield)

        self.tabWidget.addTab(self.tab_4, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.verticalLayout_11 = QVBoxLayout(self.tab_2)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout7 = QVBoxLayout()
        self.verticalLayout7.setObjectName(u"verticalLayout7")
        self.lytDataHubMap = QVBoxLayout()
        self.lytDataHubMap.setObjectName(u"lytDataHubMap")

        self.verticalLayout7.addLayout(self.lytDataHubMap)

        self.lytDataHubImg = QVBoxLayout()
        self.lytDataHubImg.setObjectName(u"lytDataHubImg")

        self.verticalLayout7.addLayout(self.lytDataHubImg)


        self.verticalLayout_11.addLayout(self.verticalLayout7)

        self.tabWidget.addTab(self.tab_2, "")

        self.verticalLayout.addWidget(self.tabWidget)


        self.main_layout.addLayout(self.verticalLayout)


        self.verticalLayout_2.addLayout(self.main_layout)

        main_controller.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(main_controller)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menubar.setDefaultUp(False)
        main_controller.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(main_controller)
        self.statusbar.setObjectName(u"statusbar")
        main_controller.setStatusBar(self.statusbar)

        self.retranslateUi(main_controller)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(main_controller)
    # setupUi

    def retranslateUi(self, main_controller):
        main_controller.setWindowTitle(QCoreApplication.translate("main_controller", u"MainWindow", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("main_controller", u"Region of Interest (ROI)", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), QCoreApplication.translate("main_controller", u"Raman imaging", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_4), QCoreApplication.translate("main_controller", u"Brightfield", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("main_controller", u"Data saving/loading", None))
    # retranslateUi

