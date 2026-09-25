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
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QMainWindow,
    QMenuBar, QRadioButton, QSizePolicy, QStatusBar,
    QTabWidget, QVBoxLayout, QWidget)

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
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.horizontalLayout = QHBoxLayout(self.tab_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lyt_datahubImg = QVBoxLayout()
        self.lyt_datahubImg.setObjectName(u"lyt_datahubImg")

        self.verticalLayout_3.addLayout(self.lyt_datahubImg)

        self.lyt_datahubMap = QVBoxLayout()
        self.lyt_datahubMap.setObjectName(u"lyt_datahubMap")

        self.verticalLayout_3.addLayout(self.lyt_datahubMap)

        self.lyt_options = QVBoxLayout()
        self.lyt_options.setObjectName(u"lyt_options")
        self.groupBox = QGroupBox(self.tab_2)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.verticalLayout_4 = QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.rad_onlyImg = QRadioButton(self.groupBox)
        self.rad_onlyImg.setObjectName(u"rad_onlyImg")
        self.rad_onlyImg.setChecked(True)

        self.verticalLayout_4.addWidget(self.rad_onlyImg)

        self.rad_overlay = QRadioButton(self.groupBox)
        self.rad_overlay.setObjectName(u"rad_overlay")

        self.verticalLayout_4.addWidget(self.rad_overlay)


        self.lyt_options.addWidget(self.groupBox)


        self.verticalLayout_3.addLayout(self.lyt_options)


        self.horizontalLayout.addLayout(self.verticalLayout_3)

        self.lyt_plotter = QVBoxLayout()
        self.lyt_plotter.setObjectName(u"lyt_plotter")

        self.horizontalLayout.addLayout(self.lyt_plotter)

        self.tabWidget.addTab(self.tab_2, "")

        self.main_layout.addWidget(self.tabWidget)


        self.verticalLayout_2.addLayout(self.main_layout)

        main_analyser.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(main_analyser)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1088, 39))
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
        self.groupBox.setTitle(QCoreApplication.translate("main_analyser", u"Visualisation", None))
        self.rad_onlyImg.setText(QCoreApplication.translate("main_analyser", u"Only show image", None))
        self.rad_overlay.setText(QCoreApplication.translate("main_analyser", u"Overlay Raman mapping on the image", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("main_analyser", u"Image visualiser", None))
    # retranslateUi

