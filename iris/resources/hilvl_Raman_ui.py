# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'hilvl_Raman.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_Hilvl_Raman(object):
    def setupUi(self, Hilvl_Raman):
        if not Hilvl_Raman.objectName():
            Hilvl_Raman.setObjectName(u"Hilvl_Raman")
        Hilvl_Raman.resize(693, 612)
        self.verticalLayout_4 = QVBoxLayout(Hilvl_Raman)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.tab_main = QTabWidget(Hilvl_Raman)
        self.tab_main.setObjectName(u"tab_main")
        self.tab_mappingparams = QWidget()
        self.tab_mappingparams.setObjectName(u"tab_mappingparams")
        self.verticalLayout_3 = QVBoxLayout(self.tab_mappingparams)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lyt_coorHub_holder = QVBoxLayout()
        self.lyt_coorHub_holder.setObjectName(u"lyt_coorHub_holder")

        self.verticalLayout_3.addLayout(self.lyt_coorHub_holder)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tab_mappingoptions = QTabWidget(self.tab_mappingparams)
        self.tab_mappingoptions.setObjectName(u"tab_mappingoptions")
        self.tab_generaloptions = QWidget()
        self.tab_generaloptions.setObjectName(u"tab_generaloptions")
        self.verticalLayout_8 = QVBoxLayout(self.tab_generaloptions)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.groupBox_2 = QGroupBox(self.tab_generaloptions)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_9 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.chk_contMap_autoAdjustSpeed = QCheckBox(self.groupBox_2)
        self.chk_contMap_autoAdjustSpeed.setObjectName(u"chk_contMap_autoAdjustSpeed")
        self.chk_contMap_autoAdjustSpeed.setChecked(True)

        self.gridLayout.addWidget(self.chk_contMap_autoAdjustSpeed, 3, 0, 1, 2)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.horizontalSpacer, 0, 1, 1, 1)

        self.groupbox_scanpattern = QGroupBox(self.groupBox_2)
        self.groupbox_scanpattern.setObjectName(u"groupbox_scanpattern")
        self.horizontalLayout_3 = QHBoxLayout(self.groupbox_scanpattern)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.rb_raster = QRadioButton(self.groupbox_scanpattern)
        self.rb_raster.setObjectName(u"rb_raster")
        self.rb_raster.setChecked(True)

        self.horizontalLayout_3.addWidget(self.rb_raster)

        self.rb_snake = QRadioButton(self.groupbox_scanpattern)
        self.rb_snake.setObjectName(u"rb_snake")

        self.horizontalLayout_3.addWidget(self.rb_snake)


        self.gridLayout.addWidget(self.groupbox_scanpattern, 0, 0, 1, 1)

        self.groupbox_scandir = QGroupBox(self.groupBox_2)
        self.groupbox_scandir.setObjectName(u"groupbox_scandir")
        self.horizontalLayout_2 = QHBoxLayout(self.groupbox_scandir)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.rb_xdir = QRadioButton(self.groupbox_scandir)
        self.rb_xdir.setObjectName(u"rb_xdir")
        self.rb_xdir.setChecked(True)

        self.horizontalLayout_2.addWidget(self.rb_xdir)

        self.rb_ydir = QRadioButton(self.groupbox_scandir)
        self.rb_ydir.setObjectName(u"rb_ydir")
        self.rb_ydir.setAutoExclusive(True)

        self.horizontalLayout_2.addWidget(self.rb_ydir)


        self.gridLayout.addWidget(self.groupbox_scandir, 1, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName(u"label_2")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_2)

        self.spin_continuousSpeedMod = QDoubleSpinBox(self.groupBox_2)
        self.spin_continuousSpeedMod.setObjectName(u"spin_continuousSpeedMod")
        self.spin_continuousSpeedMod.setValue(1.000000000000000)

        self.horizontalLayout.addWidget(self.spin_continuousSpeedMod)

        self.label_3 = QLabel(self.groupBox_2)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_3)


        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 2)


        self.verticalLayout_9.addLayout(self.gridLayout)


        self.verticalLayout_8.addWidget(self.groupBox_2)

        self.tab_mappingoptions.addTab(self.tab_generaloptions, "")
        self.tab_additionaloptions = QWidget()
        self.tab_additionaloptions.setObjectName(u"tab_additionaloptions")
        self.verticalLayout_11 = QVBoxLayout(self.tab_additionaloptions)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_10 = QVBoxLayout()
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.chk_randomise = QCheckBox(self.tab_additionaloptions)
        self.chk_randomise.setObjectName(u"chk_randomise")

        self.verticalLayout_10.addWidget(self.chk_randomise)

        self.chk_skipover = QCheckBox(self.tab_additionaloptions)
        self.chk_skipover.setObjectName(u"chk_skipover")

        self.verticalLayout_10.addWidget(self.chk_skipover)

        self.label = QLabel(self.tab_additionaloptions)
        self.label.setObjectName(u"label")

        self.verticalLayout_10.addWidget(self.label)

        self.spin_skipover = QSpinBox(self.tab_additionaloptions)
        self.spin_skipover.setObjectName(u"spin_skipover")
        self.spin_skipover.setMaximum(1000000)

        self.verticalLayout_10.addWidget(self.spin_skipover)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_10.addItem(self.verticalSpacer_2)


        self.verticalLayout_11.addLayout(self.verticalLayout_10)

        self.tab_mappingoptions.addTab(self.tab_additionaloptions, "")

        self.verticalLayout_2.addWidget(self.tab_mappingoptions)


        self.verticalLayout_3.addLayout(self.verticalLayout_2)

        self.groupBox = QGroupBox(self.tab_mappingparams)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.btn_discrete = QPushButton(self.groupBox)
        self.btn_discrete.setObjectName(u"btn_discrete")

        self.horizontalLayout_4.addWidget(self.btn_discrete)

        self.btn_continuous = QPushButton(self.groupBox)
        self.btn_continuous.setObjectName(u"btn_continuous")

        self.horizontalLayout_4.addWidget(self.btn_continuous)

        self.btn_stop = QPushButton(self.groupBox)
        self.btn_stop.setObjectName(u"btn_stop")
        self.btn_stop.setEnabled(False)
        font = QFont()
        font.setBold(True)
        self.btn_stop.setFont(font)
        self.btn_stop.setAutoFillBackground(False)
        self.btn_stop.setStyleSheet(u"background-color:red")
        self.btn_stop.setCheckable(False)

        self.horizontalLayout_4.addWidget(self.btn_stop)


        self.verticalLayout_3.addWidget(self.groupBox)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_3)

        self.tab_main.addTab(self.tab_mappingparams, "")
        self.tab_heatmap = QWidget()
        self.tab_heatmap.setObjectName(u"tab_heatmap")
        self.verticalLayout_5 = QVBoxLayout(self.tab_heatmap)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.lyt_heatmap_holder = QVBoxLayout()
        self.lyt_heatmap_holder.setObjectName(u"lyt_heatmap_holder")

        self.verticalLayout_5.addLayout(self.lyt_heatmap_holder)

        self.tab_main.addTab(self.tab_heatmap, "")

        self.main_layout.addWidget(self.tab_main)


        self.verticalLayout_4.addLayout(self.main_layout)

        QWidget.setTabOrder(self.tab_main, self.tab_mappingoptions)
        QWidget.setTabOrder(self.tab_mappingoptions, self.rb_raster)
        QWidget.setTabOrder(self.rb_raster, self.rb_snake)
        QWidget.setTabOrder(self.rb_snake, self.rb_xdir)
        QWidget.setTabOrder(self.rb_xdir, self.rb_ydir)
        QWidget.setTabOrder(self.rb_ydir, self.btn_discrete)
        QWidget.setTabOrder(self.btn_discrete, self.btn_continuous)
        QWidget.setTabOrder(self.btn_continuous, self.btn_stop)
        QWidget.setTabOrder(self.btn_stop, self.chk_randomise)
        QWidget.setTabOrder(self.chk_randomise, self.chk_skipover)
        QWidget.setTabOrder(self.chk_skipover, self.spin_skipover)

        self.retranslateUi(Hilvl_Raman)

        self.tab_main.setCurrentIndex(0)
        self.tab_mappingoptions.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Hilvl_Raman)
    # setupUi

    def retranslateUi(self, Hilvl_Raman):
        Hilvl_Raman.setWindowTitle(QCoreApplication.translate("Hilvl_Raman", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Hilvl_Raman", u"Imaging options", None))
        self.chk_contMap_autoAdjustSpeed.setText(QCoreApplication.translate("Hilvl_Raman", u"Automatically adjust the continuous mapping speed (only applicable for 'Continuous imaging')", None))
        self.groupbox_scanpattern.setTitle(QCoreApplication.translate("Hilvl_Raman", u"Scan pattern options", None))
        self.rb_raster.setText(QCoreApplication.translate("Hilvl_Raman", u"Raster", None))
        self.rb_snake.setText(QCoreApplication.translate("Hilvl_Raman", u"Snake", None))
        self.groupbox_scandir.setTitle(QCoreApplication.translate("Hilvl_Raman", u"Continuous scan options", None))
        self.rb_xdir.setText(QCoreApplication.translate("Hilvl_Raman", u"Horizontal line scan", None))
        self.rb_ydir.setText(QCoreApplication.translate("Hilvl_Raman", u"Vertical line scan", None))
        self.label_2.setText(QCoreApplication.translate("Hilvl_Raman", u"Continuous scan speed modifier:", None))
        self.label_3.setText(QCoreApplication.translate("Hilvl_Raman", u"%", None))
        self.tab_mappingoptions.setTabText(self.tab_mappingoptions.indexOf(self.tab_generaloptions), QCoreApplication.translate("Hilvl_Raman", u"General imaging options", None))
        self.chk_randomise.setText(QCoreApplication.translate("Hilvl_Raman", u"Randomise sampling points", None))
        self.chk_skipover.setText(QCoreApplication.translate("Hilvl_Raman", u"Skip over sampling points\n"
"(and comes around later to scan the skipped points)", None))
        self.label.setText(QCoreApplication.translate("Hilvl_Raman", u"Number of skipped sampling points", None))
        self.tab_mappingoptions.setTabText(self.tab_mappingoptions.indexOf(self.tab_additionaloptions), QCoreApplication.translate("Hilvl_Raman", u"Additional imaging options", None))
        self.groupBox.setTitle(QCoreApplication.translate("Hilvl_Raman", u"Perform imaging", None))
        self.btn_discrete.setText(QCoreApplication.translate("Hilvl_Raman", u"Perform discrete imaging", None))
        self.btn_continuous.setText(QCoreApplication.translate("Hilvl_Raman", u"Perform continuous imaging", None))
        self.btn_stop.setText(QCoreApplication.translate("Hilvl_Raman", u"Stop", None))
        self.tab_main.setTabText(self.tab_main.indexOf(self.tab_mappingparams), QCoreApplication.translate("Hilvl_Raman", u"Mapping parameters", None))
        self.tab_main.setTabText(self.tab_main.indexOf(self.tab_heatmap), QCoreApplication.translate("Hilvl_Raman", u"Heatmap plotter", None))
    # retranslateUi

