# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'topology_visuliser.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_topology_visualiser(object):
    def setupUi(self, topology_visualiser):
        if not topology_visualiser.objectName():
            topology_visualiser.setObjectName(u"topology_visualiser")
        topology_visualiser.resize(1054, 825)
        self.verticalLayout = QVBoxLayout(topology_visualiser)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label_2 = QLabel(topology_visualiser)
        self.label_2.setObjectName(u"label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.verticalLayout_2.addWidget(self.label_2)

        self.combo_meaCoor = QComboBox(topology_visualiser)
        self.combo_meaCoor.setObjectName(u"combo_meaCoor")

        self.verticalLayout_2.addWidget(self.combo_meaCoor)

        self.chk_edges = QCheckBox(topology_visualiser)
        self.chk_edges.setObjectName(u"chk_edges")

        self.verticalLayout_2.addWidget(self.chk_edges)


        self.horizontalLayout.addLayout(self.verticalLayout_2)

        self.lyt_plot = QVBoxLayout()
        self.lyt_plot.setObjectName(u"lyt_plot")

        self.horizontalLayout.addLayout(self.lyt_plot)


        self.main_layout.addLayout(self.horizontalLayout)

        self.btn_instructions = QPushButton(topology_visualiser)
        self.btn_instructions.setObjectName(u"btn_instructions")

        self.main_layout.addWidget(self.btn_instructions)


        self.verticalLayout.addLayout(self.main_layout)


        self.retranslateUi(topology_visualiser)

        QMetaObject.connectSlotsByName(topology_visualiser)
    # setupUi

    def retranslateUi(self, topology_visualiser):
        topology_visualiser.setWindowTitle(QCoreApplication.translate("topology_visualiser", u"Form", None))
        self.label_2.setText(QCoreApplication.translate("topology_visualiser", u"Select the Region of Interest to visualise its topology:", None))
        self.chk_edges.setText(QCoreApplication.translate("topology_visualiser", u"Show edges", None))
        self.btn_instructions.setText(QCoreApplication.translate("topology_visualiser", u"Show instructions", None))
    # retranslateUi

