# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'bf_sersSubstrate_coorGen.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFormLayout, QHBoxLayout,
    QHeaderView, QMainWindow, QPushButton, QSizePolicy,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_bf_sresSubstrate_coorGen(object):
    def setupUi(self, bf_sresSubstrate_coorGen):
        if not bf_sresSubstrate_coorGen.objectName():
            bf_sresSubstrate_coorGen.setObjectName(u"bf_sresSubstrate_coorGen")
        bf_sresSubstrate_coorGen.resize(896, 761)
        self.centralwidget = QWidget(bf_sresSubstrate_coorGen)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab_setup = QWidget()
        self.tab_setup.setObjectName(u"tab_setup")
        self.verticalLayout_3 = QVBoxLayout(self.tab_setup)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lyt_coorHub = QVBoxLayout()
        self.lyt_coorHub.setObjectName(u"lyt_coorHub")
        self.tree_img = QTreeWidget(self.tab_setup)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_img.setHeaderItem(__qtreewidgetitem)
        self.tree_img.setObjectName(u"tree_img")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tree_img.sizePolicy().hasHeightForWidth())
        self.tree_img.setSizePolicy(sizePolicy)
        self.tree_img.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.lyt_coorHub.addWidget(self.tree_img)


        self.horizontalLayout.addLayout(self.lyt_coorHub)

        self.lyt = QVBoxLayout()
        self.lyt.setObjectName(u"lyt")
        self.lyt_params = QFormLayout()
        self.lyt_params.setObjectName(u"lyt_params")

        self.lyt.addLayout(self.lyt_params)

        self.btn_process = QPushButton(self.tab_setup)
        self.btn_process.setObjectName(u"btn_process")

        self.lyt.addWidget(self.btn_process)


        self.horizontalLayout.addLayout(self.lyt)


        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.tabWidget.addTab(self.tab_setup, "")
        self.tab_result = QWidget()
        self.tab_result.setObjectName(u"tab_result")
        self.verticalLayout_4 = QVBoxLayout(self.tab_result)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.tree_result = QTreeWidget(self.tab_result)
        __qtreewidgetitem1 = QTreeWidgetItem()
        __qtreewidgetitem1.setText(0, u"1");
        self.tree_result.setHeaderItem(__qtreewidgetitem1)
        self.tree_result.setObjectName(u"tree_result")
        sizePolicy.setHeightForWidth(self.tree_result.sizePolicy().hasHeightForWidth())
        self.tree_result.setSizePolicy(sizePolicy)
        self.tree_result.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.verticalLayout_7.addWidget(self.tree_result)

        self.btn_remove = QPushButton(self.tab_result)
        self.btn_remove.setObjectName(u"btn_remove")

        self.verticalLayout_7.addWidget(self.btn_remove)

        self.btn_saveall = QPushButton(self.tab_result)
        self.btn_saveall.setObjectName(u"btn_saveall")

        self.verticalLayout_7.addWidget(self.btn_saveall)


        self.horizontalLayout_2.addLayout(self.verticalLayout_7)

        self.lyt_result = QVBoxLayout()
        self.lyt_result.setObjectName(u"lyt_result")

        self.horizontalLayout_2.addLayout(self.lyt_result)


        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.tabWidget.addTab(self.tab_result, "")

        self.verticalLayout.addWidget(self.tabWidget)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        bf_sresSubstrate_coorGen.setCentralWidget(self.centralwidget)

        self.retranslateUi(bf_sresSubstrate_coorGen)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(bf_sresSubstrate_coorGen)
    # setupUi

    def retranslateUi(self, bf_sresSubstrate_coorGen):
        bf_sresSubstrate_coorGen.setWindowTitle(QCoreApplication.translate("bf_sresSubstrate_coorGen", u"MainWindow", None))
        self.btn_process.setText(QCoreApplication.translate("bf_sresSubstrate_coorGen", u"Process all selected ROI pictures", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_setup), QCoreApplication.translate("bf_sresSubstrate_coorGen", u"Setup", None))
        self.btn_remove.setText(QCoreApplication.translate("bf_sresSubstrate_coorGen", u"Remove selected", None))
        self.btn_saveall.setText(QCoreApplication.translate("bf_sresSubstrate_coorGen", u"Save selected", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_result), QCoreApplication.translate("bf_sresSubstrate_coorGen", u"Result", None))
    # retranslateUi

