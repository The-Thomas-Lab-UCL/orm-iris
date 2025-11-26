# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'objectives.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QHBoxLayout, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_wdg_objectives(object):
    def setupUi(self, wdg_objectives):
        if not wdg_objectives.objectName():
            wdg_objectives.setObjectName(u"wdg_objectives")
        wdg_objectives.resize(669, 278)
        self.horizontalLayout = QHBoxLayout(wdg_objectives)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(wdg_objectives)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.btn_load = QPushButton(self.groupBox)
        self.btn_load.setObjectName(u"btn_load")

        self.gridLayout.addWidget(self.btn_load, 1, 0, 1, 1)

        self.btn_refresh = QPushButton(self.groupBox)
        self.btn_refresh.setObjectName(u"btn_refresh")

        self.gridLayout.addWidget(self.btn_refresh, 1, 1, 1, 1)

        self.combo_objective = QComboBox(self.groupBox)
        self.combo_objective.setObjectName(u"combo_objective")

        self.gridLayout.addWidget(self.combo_objective, 0, 0, 1, 2)


        self.gridLayout_2.addLayout(self.gridLayout, 0, 0, 1, 1)


        self.main_layout.addWidget(self.groupBox)


        self.horizontalLayout.addLayout(self.main_layout)


        self.retranslateUi(wdg_objectives)

        QMetaObject.connectSlotsByName(wdg_objectives)
    # setupUi

    def retranslateUi(self, wdg_objectives):
        wdg_objectives.setWindowTitle(QCoreApplication.translate("wdg_objectives", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("wdg_objectives", u"Objectives", None))
        self.btn_load.setText(QCoreApplication.translate("wdg_objectives", u"Load objective folder", None))
        self.btn_refresh.setText(QCoreApplication.translate("wdg_objectives", u"Refresh objective folder", None))
    # retranslateUi

