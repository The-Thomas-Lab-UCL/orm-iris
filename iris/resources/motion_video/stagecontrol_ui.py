# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'stagecontrol.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFormLayout, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
    QWidget)

class Ui_stagecontrol(object):
    def setupUi(self, stagecontrol):
        if not stagecontrol.objectName():
            stagecontrol.setObjectName(u"stagecontrol")
        stagecontrol.resize(828, 628)
        self.verticalLayoutWidget_4 = QWidget(stagecontrol)
        self.verticalLayoutWidget_4.setObjectName(u"verticalLayoutWidget_4")
        self.verticalLayoutWidget_4.setGeometry(QRect(30, 10, 325, 294))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget_4)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_16 = QLabel(self.verticalLayoutWidget_4)
        self.label_16.setObjectName(u"label_16")

        self.horizontalLayout.addWidget(self.label_16)

        self.lbl_coor_um = QLabel(self.verticalLayoutWidget_4)
        self.lbl_coor_um.setObjectName(u"lbl_coor_um")

        self.horizontalLayout.addWidget(self.lbl_coor_um)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tab_controls = QTabWidget(self.verticalLayoutWidget_4)
        self.tab_controls.setObjectName(u"tab_controls")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tab_controls.sizePolicy().hasHeightForWidth())
        self.tab_controls.setSizePolicy(sizePolicy)
        self.tab_basic = QWidget()
        self.tab_basic.setObjectName(u"tab_basic")
        self.formLayout = QFormLayout(self.tab_basic)
        self.formLayout.setObjectName(u"formLayout")
        self.lyt_main = QVBoxLayout()
        self.lyt_main.setObjectName(u"lyt_main")
        self.lyt_param = QGridLayout()
        self.lyt_param.setObjectName(u"lyt_param")
        self.label_3 = QLabel(self.tab_basic)
        self.label_3.setObjectName(u"label_3")

        self.lyt_param.addWidget(self.label_3, 0, 2, 1, 1)

        self.lbl_stepsizexy = QLabel(self.tab_basic)
        self.lbl_stepsizexy.setObjectName(u"lbl_stepsizexy")

        self.lyt_param.addWidget(self.lbl_stepsizexy, 2, 1, 1, 1)

        self.label_9 = QLabel(self.tab_basic)
        self.label_9.setObjectName(u"label_9")

        self.lyt_param.addWidget(self.label_9, 2, 2, 1, 1)

        self.label_7 = QLabel(self.tab_basic)
        self.label_7.setObjectName(u"label_7")

        self.lyt_param.addWidget(self.label_7, 2, 0, 1, 1)

        self.ent_speedxy = QLineEdit(self.tab_basic)
        self.ent_speedxy.setObjectName(u"ent_speedxy")

        self.lyt_param.addWidget(self.ent_speedxy, 0, 3, 1, 1)

        self.label_4 = QLabel(self.tab_basic)
        self.label_4.setObjectName(u"label_4")

        self.lyt_param.addWidget(self.label_4, 1, 0, 1, 1)

        self.label = QLabel(self.tab_basic)
        self.label.setObjectName(u"label")

        self.lyt_param.addWidget(self.label, 0, 0, 1, 1)

        self.lbl_speedxy = QLabel(self.tab_basic)
        self.lbl_speedxy.setObjectName(u"lbl_speedxy")

        self.lyt_param.addWidget(self.lbl_speedxy, 0, 1, 1, 1)

        self.lbl_speedz = QLabel(self.tab_basic)
        self.lbl_speedz.setObjectName(u"lbl_speedz")

        self.lyt_param.addWidget(self.lbl_speedz, 1, 1, 1, 1)

        self.label_6 = QLabel(self.tab_basic)
        self.label_6.setObjectName(u"label_6")

        self.lyt_param.addWidget(self.label_6, 1, 2, 1, 1)

        self.label_10 = QLabel(self.tab_basic)
        self.label_10.setObjectName(u"label_10")

        self.lyt_param.addWidget(self.label_10, 3, 0, 1, 1)

        self.lbl_stepsizez = QLabel(self.tab_basic)
        self.lbl_stepsizez.setObjectName(u"lbl_stepsizez")

        self.lyt_param.addWidget(self.lbl_stepsizez, 3, 1, 1, 1)

        self.label_12 = QLabel(self.tab_basic)
        self.label_12.setObjectName(u"label_12")

        self.lyt_param.addWidget(self.label_12, 3, 2, 1, 1)

        self.ent_speedz = QLineEdit(self.tab_basic)
        self.ent_speedz.setObjectName(u"ent_speedz")

        self.lyt_param.addWidget(self.ent_speedz, 1, 3, 1, 1)

        self.ent_stepxy_um = QLineEdit(self.tab_basic)
        self.ent_stepxy_um.setObjectName(u"ent_stepxy_um")

        self.lyt_param.addWidget(self.ent_stepxy_um, 2, 3, 1, 1)

        self.ent_stepz_um = QLineEdit(self.tab_basic)
        self.ent_stepz_um.setObjectName(u"ent_stepz_um")

        self.lyt_param.addWidget(self.ent_stepz_um, 3, 3, 1, 1)


        self.lyt_main.addLayout(self.lyt_param)

        self.lyt_motion = QHBoxLayout()
        self.lyt_motion.setObjectName(u"lyt_motion")
        self.lyt_xy = QGridLayout()
        self.lyt_xy.setObjectName(u"lyt_xy")

        self.lyt_motion.addLayout(self.lyt_xy)

        self.lyt_z = QVBoxLayout()
        self.lyt_z.setObjectName(u"lyt_z")

        self.lyt_motion.addLayout(self.lyt_z)


        self.lyt_main.addLayout(self.lyt_motion)

        self.lyt_stepmode = QVBoxLayout()
        self.lyt_stepmode.setObjectName(u"lyt_stepmode")
        self.chk_stepmode = QCheckBox(self.tab_basic)
        self.chk_stepmode.setObjectName(u"chk_stepmode")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.chk_stepmode.sizePolicy().hasHeightForWidth())
        self.chk_stepmode.setSizePolicy(sizePolicy1)

        self.lyt_stepmode.addWidget(self.chk_stepmode)

        self.label_2 = QLabel(self.tab_basic)
        self.label_2.setObjectName(u"label_2")

        self.lyt_stepmode.addWidget(self.label_2)


        self.lyt_main.addLayout(self.lyt_stepmode)


        self.formLayout.setLayout(0, QFormLayout.ItemRole.LabelRole, self.lyt_main)

        self.tab_controls.addTab(self.tab_basic, "")
        self.tab_advanced = QWidget()
        self.tab_advanced.setObjectName(u"tab_advanced")
        self.gridLayoutWidget_3 = QWidget(self.tab_advanced)
        self.gridLayoutWidget_3.setObjectName(u"gridLayoutWidget_3")
        self.gridLayoutWidget_3.setGeometry(QRect(10, 10, 288, 541))
        self.lyt_main_grid = QGridLayout(self.gridLayoutWidget_3)
        self.lyt_main_grid.setObjectName(u"lyt_main_grid")
        self.lyt_main_grid.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Minimum)

        self.lyt_main_grid.addItem(self.horizontalSpacer_6, 4, 0, 1, 3)

        self.ent_goto_x_um = QLineEdit(self.gridLayoutWidget_3)
        self.ent_goto_x_um.setObjectName(u"ent_goto_x_um")

        self.lyt_main_grid.addWidget(self.ent_goto_x_um, 0, 1, 1, 1)

        self.label_13 = QLabel(self.gridLayoutWidget_3)
        self.label_13.setObjectName(u"label_13")

        self.lyt_main_grid.addWidget(self.label_13, 2, 2, 1, 1)

        self.label_14 = QLabel(self.gridLayoutWidget_3)
        self.label_14.setObjectName(u"label_14")

        self.lyt_main_grid.addWidget(self.label_14, 1, 2, 1, 1)

        self.label_15 = QLabel(self.gridLayoutWidget_3)
        self.label_15.setObjectName(u"label_15")

        self.lyt_main_grid.addWidget(self.label_15, 0, 2, 1, 1)

        self.label_8 = QLabel(self.gridLayoutWidget_3)
        self.label_8.setObjectName(u"label_8")

        self.lyt_main_grid.addWidget(self.label_8, 1, 0, 1, 1)

        self.ent_goto_y_um = QLineEdit(self.gridLayoutWidget_3)
        self.ent_goto_y_um.setObjectName(u"ent_goto_y_um")

        self.lyt_main_grid.addWidget(self.ent_goto_y_um, 1, 1, 1, 1)

        self.ent_goto_z_um = QLineEdit(self.gridLayoutWidget_3)
        self.ent_goto_z_um.setObjectName(u"ent_goto_z_um")

        self.lyt_main_grid.addWidget(self.ent_goto_z_um, 2, 1, 1, 1)

        self.btn_goto = QPushButton(self.gridLayoutWidget_3)
        self.btn_goto.setObjectName(u"btn_goto")

        self.lyt_main_grid.addWidget(self.btn_goto, 3, 0, 1, 3)

        self.label_5 = QLabel(self.gridLayoutWidget_3)
        self.label_5.setObjectName(u"label_5")

        self.lyt_main_grid.addWidget(self.label_5, 0, 0, 1, 1)

        self.label_11 = QLabel(self.gridLayoutWidget_3)
        self.label_11.setObjectName(u"label_11")

        self.lyt_main_grid.addWidget(self.label_11, 2, 0, 1, 1)

        self.lyt_home = QHBoxLayout()
        self.lyt_home.setObjectName(u"lyt_home")
        self.btn_home_xy = QPushButton(self.gridLayoutWidget_3)
        self.btn_home_xy.setObjectName(u"btn_home_xy")

        self.lyt_home.addWidget(self.btn_home_xy)

        self.btn_home_z = QPushButton(self.gridLayoutWidget_3)
        self.btn_home_z.setObjectName(u"btn_home_z")

        self.lyt_home.addWidget(self.btn_home_z)


        self.lyt_main_grid.addLayout(self.lyt_home, 5, 0, 1, 3)

        self.tab_controls.addTab(self.tab_advanced, "")

        self.verticalLayout.addWidget(self.tab_controls)


        self.retranslateUi(stagecontrol)

        self.tab_controls.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(stagecontrol)
    # setupUi

    def retranslateUi(self, stagecontrol):
        stagecontrol.setWindowTitle(QCoreApplication.translate("stagecontrol", u"Form", None))
        self.label_16.setText(QCoreApplication.translate("stagecontrol", u"Stage coordinate [\u00b5m]:", None))
        self.lbl_coor_um.setText(QCoreApplication.translate("stagecontrol", u"(NA,NA,NA)", None))
        self.label_3.setText(QCoreApplication.translate("stagecontrol", u"%", None))
        self.lbl_stepsizexy.setText(QCoreApplication.translate("stagecontrol", u"NA", None))
        self.label_9.setText(QCoreApplication.translate("stagecontrol", u"\u00b5m", None))
        self.label_7.setText(QCoreApplication.translate("stagecontrol", u"XY step size:", None))
        self.label_4.setText(QCoreApplication.translate("stagecontrol", u"Z speed:", None))
        self.label.setText(QCoreApplication.translate("stagecontrol", u"XY speed:", None))
        self.lbl_speedxy.setText(QCoreApplication.translate("stagecontrol", u"NA", None))
        self.lbl_speedz.setText(QCoreApplication.translate("stagecontrol", u"NA", None))
        self.label_6.setText(QCoreApplication.translate("stagecontrol", u"%", None))
        self.label_10.setText(QCoreApplication.translate("stagecontrol", u"Z step size:", None))
        self.lbl_stepsizez.setText(QCoreApplication.translate("stagecontrol", u"NA", None))
        self.label_12.setText(QCoreApplication.translate("stagecontrol", u"\u00b5m", None))
        self.chk_stepmode.setText(QCoreApplication.translate("stagecontrol", u"Step motion mode", None))
        self.label_2.setText(QCoreApplication.translate("stagecontrol", u"Or RIGHT CLICK on the direction\n"
"buttons to move in steps", None))
        self.tab_controls.setTabText(self.tab_controls.indexOf(self.tab_basic), QCoreApplication.translate("stagecontrol", u"Basic", None))
        self.label_13.setText(QCoreApplication.translate("stagecontrol", u"\u00b5m", None))
        self.label_14.setText(QCoreApplication.translate("stagecontrol", u"\u00b5m", None))
        self.label_15.setText(QCoreApplication.translate("stagecontrol", u"\u00b5m", None))
        self.label_8.setText(QCoreApplication.translate("stagecontrol", u"Y-coordinate:", None))
        self.btn_goto.setText(QCoreApplication.translate("stagecontrol", u"Go to coordinate", None))
        self.label_5.setText(QCoreApplication.translate("stagecontrol", u"X-coordinate :", None))
        self.label_11.setText(QCoreApplication.translate("stagecontrol", u"Z-coordinate:", None))
        self.btn_home_xy.setText(QCoreApplication.translate("stagecontrol", u"Home XY", None))
        self.btn_home_z.setText(QCoreApplication.translate("stagecontrol", u"Home Z", None))
        self.tab_controls.setTabText(self.tab_controls.indexOf(self.tab_advanced), QCoreApplication.translate("stagecontrol", u"Advanced", None))
    # retranslateUi

