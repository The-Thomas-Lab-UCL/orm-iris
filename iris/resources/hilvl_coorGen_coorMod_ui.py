# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hilvl_coorGen_coorMod.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_coorMod(object):
    def setupUi(self, coorMod):
        if not coorMod.objectName():
            coorMod.setObjectName(u"coorMod")
        coorMod.resize(400, 300)
        self.verticalLayout_2 = QVBoxLayout(coorMod)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.combo_methods = QComboBox(coorMod)
        self.combo_methods.setObjectName(u"combo_methods")

        self.main_layout.addWidget(self.combo_methods)

        self.lyt_holder_modifiers = QVBoxLayout()
        self.lyt_holder_modifiers.setObjectName(u"lyt_holder_modifiers")

        self.main_layout.addLayout(self.lyt_holder_modifiers)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(coorMod)

        QMetaObject.connectSlotsByName(coorMod)
    # setupUi

    def retranslateUi(self, coorMod):
        coorMod.setWindowTitle(QCoreApplication.translate("coorMod", u"Form", None))
    # retranslateUi

