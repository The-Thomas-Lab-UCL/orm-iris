# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tiling_method.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_tiling_method(object):
    def setupUi(self, tiling_method):
        if not tiling_method.objectName():
            tiling_method.setObjectName(u"tiling_method")
        tiling_method.resize(679, 656)
        self.verticalLayoutWidget = QWidget(tiling_method)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(20, 10, 645, 631))
        self.main_layout = QVBoxLayout(self.verticalLayoutWidget)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.lyt_holder_img = QVBoxLayout()
        self.lyt_holder_img.setObjectName(u"lyt_holder_img")

        self.verticalLayout_2.addLayout(self.lyt_holder_img)

        self.chk_lres = QCheckBox(self.verticalLayoutWidget)
        self.chk_lres.setObjectName(u"chk_lres")

        self.verticalLayout_2.addWidget(self.chk_lres)

        self.combo_img = QComboBox(self.verticalLayoutWidget)
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

        self.btn_capture = QPushButton(self.verticalLayoutWidget)
        self.btn_capture.setObjectName(u"btn_capture")

        self.main_layout.addWidget(self.btn_capture)


        self.retranslateUi(tiling_method)

        QMetaObject.connectSlotsByName(tiling_method)
    # setupUi

    def retranslateUi(self, tiling_method):
        tiling_method.setWindowTitle(QCoreApplication.translate("tiling_method", u"Form", None))
        self.chk_lres.setText(QCoreApplication.translate("tiling_method", u"Use low-resolution image (faster processing)", None))
        self.btn_capture.setText(QCoreApplication.translate("tiling_method", u"Perform image tiling", None))
    # retranslateUi

