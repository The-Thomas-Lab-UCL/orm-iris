# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tiling_method.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDockWidget,
    QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_tiling_method(object):
    def setupUi(self, tiling_method):
        if not tiling_method.objectName():
            tiling_method.setObjectName(u"tiling_method")
        tiling_method.resize(679, 656)
        self.verticalLayout_5 = QVBoxLayout(tiling_method)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.dockWidget = QDockWidget(tiling_method)
        self.dockWidget.setObjectName(u"dockWidget")
        self.dockWidget.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable|QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.dockWidget.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea)
        self.dockWidgetContents = QWidget()
        self.dockWidgetContents.setObjectName(u"dockWidgetContents")
        self.verticalLayout_4 = QVBoxLayout(self.dockWidgetContents)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.lyt_holder_img = QVBoxLayout()
        self.lyt_holder_img.setObjectName(u"lyt_holder_img")

        self.verticalLayout_4.addLayout(self.lyt_holder_img)

        self.dockWidget.setWidget(self.dockWidgetContents)

        self.verticalLayout_2.addWidget(self.dockWidget)

        self.chk_lres = QCheckBox(tiling_method)
        self.chk_lres.setObjectName(u"chk_lres")
        self.chk_lres.setChecked(True)

        self.verticalLayout_2.addWidget(self.chk_lres)

        self.combo_img = QComboBox(tiling_method)
        self.combo_img.setObjectName(u"combo_img")

        self.verticalLayout_2.addWidget(self.combo_img)


        self.horizontalLayout.addLayout(self.verticalLayout_2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lyt_holder_tree = QVBoxLayout()
        self.lyt_holder_tree.setObjectName(u"lyt_holder_tree")

        self.verticalLayout.addLayout(self.lyt_holder_tree)


        self.horizontalLayout.addLayout(self.verticalLayout)


        self.main_layout.addLayout(self.horizontalLayout)

        self.lyt_holder_controls = QVBoxLayout()
        self.lyt_holder_controls.setObjectName(u"lyt_holder_controls")

        self.main_layout.addLayout(self.lyt_holder_controls)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_capture = QPushButton(tiling_method)
        self.btn_capture.setObjectName(u"btn_capture")

        self.horizontalLayout_2.addWidget(self.btn_capture)

        self.btn_stop = QPushButton(tiling_method)
        self.btn_stop.setObjectName(u"btn_stop")
        self.btn_stop.setStyleSheet(u"background-color:red; color:white")

        self.horizontalLayout_2.addWidget(self.btn_stop)


        self.main_layout.addLayout(self.horizontalLayout_2)


        self.verticalLayout_5.addLayout(self.main_layout)

        QWidget.setTabOrder(self.chk_lres, self.combo_img)

        self.retranslateUi(tiling_method)

        QMetaObject.connectSlotsByName(tiling_method)
    # setupUi

    def retranslateUi(self, tiling_method):
        tiling_method.setWindowTitle(QCoreApplication.translate("tiling_method", u"Form", None))
        self.chk_lres.setText(QCoreApplication.translate("tiling_method", u"Show low-resolution image (faster processing)", None))
        self.btn_capture.setText(QCoreApplication.translate("tiling_method", u"Perform image tiling", None))
        self.btn_stop.setText(QCoreApplication.translate("tiling_method", u"Stop", None))
    # retranslateUi

