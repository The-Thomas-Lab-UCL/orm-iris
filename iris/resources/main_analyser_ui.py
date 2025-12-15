# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_analyser.ui'
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

class Ui_main_analyser(object):
    def setupUi(self, main_analyser):
        if not main_analyser.objectName():
            main_analyser.setObjectName(u"main_analyser")
        main_analyser.resize(1088, 785)
        self.centralwidget = QWidget(main_analyser)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout = QVBoxLayout(self.tab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.lyt_dataholder = QVBoxLayout()
        self.lyt_dataholder.setObjectName(u"lyt_dataholder")

        self.horizontalLayout_2.addLayout(self.lyt_dataholder)

        self.lyt_heatmap = QVBoxLayout()
        self.lyt_heatmap.setObjectName(u"lyt_heatmap")

        self.horizontalLayout_2.addLayout(self.lyt_heatmap)

        self.lyt_peakfinder = QVBoxLayout()
        self.lyt_peakfinder.setObjectName(u"lyt_peakfinder")

        self.horizontalLayout_2.addLayout(self.lyt_peakfinder)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.tabWidget.addTab(self.tab, "")

        self.main_layout.addWidget(self.tabWidget)


        self.verticalLayout_2.addLayout(self.main_layout)

        main_analyser.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(main_analyser)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1088, 30))
        main_analyser.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(main_analyser)
        self.statusbar.setObjectName(u"statusbar")
        main_analyser.setStatusBar(self.statusbar)

        self.retranslateUi(main_analyser)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(main_analyser)
    # setupUi

    def retranslateUi(self, main_analyser):
        main_analyser.setWindowTitle(QCoreApplication.translate("main_analyser", u"MainWindow", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("main_analyser", u"Data visualiser", None))
    # retranslateUi

