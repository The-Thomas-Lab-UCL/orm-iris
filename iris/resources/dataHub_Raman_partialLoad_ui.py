# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dataHub_Raman_partialLoad.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QHeaderView, QLabel, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_dataHub_Raman_partialLoad(object):
    def setupUi(self, dataHub_Raman_partialLoad):
        if not dataHub_Raman_partialLoad.objectName():
            dataHub_Raman_partialLoad.setObjectName(u"dataHub_Raman_partialLoad")
        dataHub_Raman_partialLoad.resize(679, 505)
        self.verticalLayout_2 = QVBoxLayout(dataHub_Raman_partialLoad)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(dataHub_Raman_partialLoad)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.tree_viewer = QTreeWidget(dataHub_Raman_partialLoad)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_viewer.setHeaderItem(__qtreewidgetitem)
        self.tree_viewer.setObjectName(u"tree_viewer")

        self.verticalLayout.addWidget(self.tree_viewer)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.buttonBox = QDialogButtonBox(dataHub_Raman_partialLoad)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.buttonBox)


        self.retranslateUi(dataHub_Raman_partialLoad)
        self.buttonBox.accepted.connect(dataHub_Raman_partialLoad.accept)
        self.buttonBox.rejected.connect(dataHub_Raman_partialLoad.reject)

        QMetaObject.connectSlotsByName(dataHub_Raman_partialLoad)
    # setupUi

    def retranslateUi(self, dataHub_Raman_partialLoad):
        dataHub_Raman_partialLoad.setWindowTitle(QCoreApplication.translate("dataHub_Raman_partialLoad", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("dataHub_Raman_partialLoad", u"Select all the units to load:", None))
    # retranslateUi

