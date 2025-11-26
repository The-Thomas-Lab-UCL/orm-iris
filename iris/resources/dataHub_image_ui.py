# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dataHub_image.ui'
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QHeaderView,
    QPushButton, QSizePolicy, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_dataHub_image(object):
    def setupUi(self, dataHub_image):
        if not dataHub_image.objectName():
            dataHub_image.setObjectName(u"dataHub_image")
        dataHub_image.resize(870, 487)
        self.horizontalLayout = QHBoxLayout(dataHub_image)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(dataHub_image)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tree = QTreeWidget(self.groupBox)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree.setHeaderItem(__qtreewidgetitem)
        self.tree.setObjectName(u"tree")

        self.verticalLayout.addWidget(self.tree)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_save = QPushButton(self.groupBox)
        self.btn_save.setObjectName(u"btn_save")

        self.horizontalLayout_2.addWidget(self.btn_save)

        self.btn_load = QPushButton(self.groupBox)
        self.btn_load.setObjectName(u"btn_load")

        self.horizontalLayout_2.addWidget(self.btn_load)

        self.btn_remove = QPushButton(self.groupBox)
        self.btn_remove.setObjectName(u"btn_remove")

        self.horizontalLayout_2.addWidget(self.btn_remove)

        self.btn_save_png = QPushButton(self.groupBox)
        self.btn_save_png.setObjectName(u"btn_save_png")

        self.horizontalLayout_2.addWidget(self.btn_save_png)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.verticalLayout_2.addLayout(self.verticalLayout)


        self.main_layout.addWidget(self.groupBox)


        self.horizontalLayout.addLayout(self.main_layout)


        self.retranslateUi(dataHub_image)

        QMetaObject.connectSlotsByName(dataHub_image)
    # setupUi

    def retranslateUi(self, dataHub_image):
        dataHub_image.setWindowTitle(QCoreApplication.translate("dataHub_image", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("dataHub_image", u"Brightfield Image", None))
        self.btn_save.setText(QCoreApplication.translate("dataHub_image", u"Save all (.db)", None))
        self.btn_load.setText(QCoreApplication.translate("dataHub_image", u"Load (.db)", None))
        self.btn_remove.setText(QCoreApplication.translate("dataHub_image", u"Remove selected", None))
        self.btn_save_png.setText(QCoreApplication.translate("dataHub_image", u"Save selected units (.png)", None))
    # retranslateUi

