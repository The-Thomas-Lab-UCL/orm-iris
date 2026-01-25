# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'translator_xyz.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_translator_xyz(object):
    def setupUi(self, translator_xyz):
        if not translator_xyz.objectName():
            translator_xyz.setObjectName(u"translator_xyz")
        translator_xyz.resize(1033, 739)
        self.verticalLayout_2 = QVBoxLayout(translator_xyz)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.label = QLabel(translator_xyz)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.main_layout.addWidget(self.label)

        self.combo_meaCoor = QComboBox(translator_xyz)
        self.combo_meaCoor.setObjectName(u"combo_meaCoor")

        self.main_layout.addWidget(self.combo_meaCoor)

        self.groupBox = QGroupBox(translator_xyz)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_5 = QVBoxLayout(self.groupBox)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.groupBox_4 = QGroupBox(self.groupBox)
        self.groupBox_4.setObjectName(u"groupBox_4")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.groupBox_4.sizePolicy().hasHeightForWidth())
        self.groupBox_4.setSizePolicy(sizePolicy1)
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_4)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.btn_xy_centreright = QRadioButton(self.groupBox_4)
        self.btn_xy_centreright.setObjectName(u"btn_xy_centreright")

        self.gridLayout_2.addWidget(self.btn_xy_centreright, 1, 2, 1, 1)

        self.btn_xy_centrecentre = QRadioButton(self.groupBox_4)
        self.btn_xy_centrecentre.setObjectName(u"btn_xy_centrecentre")
        self.btn_xy_centrecentre.setChecked(True)

        self.gridLayout_2.addWidget(self.btn_xy_centrecentre, 1, 1, 1, 1)

        self.btn_xy_topright = QRadioButton(self.groupBox_4)
        self.btn_xy_topright.setObjectName(u"btn_xy_topright")

        self.gridLayout_2.addWidget(self.btn_xy_topright, 0, 2, 1, 1)

        self.btn_xy_bottomright = QRadioButton(self.groupBox_4)
        self.btn_xy_bottomright.setObjectName(u"btn_xy_bottomright")

        self.gridLayout_2.addWidget(self.btn_xy_bottomright, 2, 2, 1, 1)

        self.btn_xy_centreleft = QRadioButton(self.groupBox_4)
        self.btn_xy_centreleft.setObjectName(u"btn_xy_centreleft")

        self.gridLayout_2.addWidget(self.btn_xy_centreleft, 1, 0, 1, 1)

        self.btn_xy_topleft = QRadioButton(self.groupBox_4)
        self.btn_xy_topleft.setObjectName(u"btn_xy_topleft")

        self.gridLayout_2.addWidget(self.btn_xy_topleft, 0, 0, 1, 1)

        self.btn_xy_bottomleft = QRadioButton(self.groupBox_4)
        self.btn_xy_bottomleft.setObjectName(u"btn_xy_bottomleft")

        self.gridLayout_2.addWidget(self.btn_xy_bottomleft, 2, 0, 1, 1)

        self.btn_xy_bottomcentre = QRadioButton(self.groupBox_4)
        self.btn_xy_bottomcentre.setObjectName(u"btn_xy_bottomcentre")

        self.gridLayout_2.addWidget(self.btn_xy_bottomcentre, 2, 1, 1, 1)

        self.btn_xy_topcentre = QRadioButton(self.groupBox_4)
        self.btn_xy_topcentre.setObjectName(u"btn_xy_topcentre")

        self.gridLayout_2.addWidget(self.btn_xy_topcentre, 0, 1, 1, 1)


        self.verticalLayout_6.addLayout(self.gridLayout_2)


        self.horizontalLayout.addWidget(self.groupBox_4)

        self.groupBox_3 = QGroupBox(self.groupBox)
        self.groupBox_3.setObjectName(u"groupBox_3")
        sizePolicy1.setHeightForWidth(self.groupBox_3.sizePolicy().hasHeightForWidth())
        self.groupBox_3.setSizePolicy(sizePolicy1)
        self.verticalLayout_7 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.gridLayout_3 = QGridLayout()
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.btn_z_bottom = QRadioButton(self.groupBox_3)
        self.btn_z_bottom.setObjectName(u"btn_z_bottom")
        self.btn_z_bottom.setChecked(True)

        self.gridLayout_3.addWidget(self.btn_z_bottom, 2, 0, 1, 1)

        self.btn_z_centre = QRadioButton(self.groupBox_3)
        self.btn_z_centre.setObjectName(u"btn_z_centre")

        self.gridLayout_3.addWidget(self.btn_z_centre, 1, 0, 1, 1)

        self.btn_z_top = QRadioButton(self.groupBox_3)
        self.btn_z_top.setObjectName(u"btn_z_top")

        self.gridLayout_3.addWidget(self.btn_z_top, 0, 0, 1, 1)


        self.verticalLayout_7.addLayout(self.gridLayout_3)


        self.horizontalLayout.addWidget(self.groupBox_3)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.btn_goto_refLoc = QPushButton(self.groupBox)
        self.btn_goto_refLoc.setObjectName(u"btn_goto_refLoc")

        self.verticalLayout_4.addWidget(self.btn_goto_refLoc)

        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)

        self.btn_commit = QPushButton(self.groupBox)
        self.btn_commit.setObjectName(u"btn_commit")

        self.gridLayout.addWidget(self.btn_commit, 2, 0, 1, 5)

        self.spin_coorYUm = QDoubleSpinBox(self.groupBox)
        self.spin_coorYUm.setObjectName(u"spin_coorYUm")
        self.spin_coorYUm.setMinimum(-1000000.000000000000000)
        self.spin_coorYUm.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coorYUm, 1, 2, 1, 1)

        self.btn_storeCoor = QPushButton(self.groupBox)
        self.btn_storeCoor.setObjectName(u"btn_storeCoor")

        self.gridLayout.addWidget(self.btn_storeCoor, 1, 4, 1, 1)

        self.lbl_prevCoor = QLabel(self.groupBox)
        self.lbl_prevCoor.setObjectName(u"lbl_prevCoor")

        self.gridLayout.addWidget(self.lbl_prevCoor, 0, 1, 1, 1)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        sizePolicy1.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy1)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)

        self.spin_coorXUm = QDoubleSpinBox(self.groupBox)
        self.spin_coorXUm.setObjectName(u"spin_coorXUm")
        self.spin_coorXUm.setMinimum(-1000000.000000000000000)
        self.spin_coorXUm.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coorXUm, 1, 1, 1, 1)

        self.spin_coorZUm = QDoubleSpinBox(self.groupBox)
        self.spin_coorZUm.setObjectName(u"spin_coorZUm")
        self.spin_coorZUm.setMinimum(-1000000.000000000000000)
        self.spin_coorZUm.setMaximum(1000000.000000000000000)

        self.gridLayout.addWidget(self.spin_coorZUm, 1, 3, 1, 1)


        self.verticalLayout_4.addLayout(self.gridLayout)


        self.verticalLayout_5.addLayout(self.verticalLayout_4)


        self.main_layout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(translator_xyz)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_5 = QGroupBox(self.groupBox_2)
        self.groupBox_5.setObjectName(u"groupBox_5")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.groupBox_5.sizePolicy().hasHeightForWidth())
        self.groupBox_5.setSizePolicy(sizePolicy2)
        self.verticalLayout_9 = QVBoxLayout(self.groupBox_5)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.rad_autoSel_lastModified = QRadioButton(self.groupBox_5)
        self.rad_autoSel_lastModified.setObjectName(u"rad_autoSel_lastModified")
        self.rad_autoSel_lastModified.setChecked(True)

        self.verticalLayout_8.addWidget(self.rad_autoSel_lastModified)

        self.rad_autoSel_next = QRadioButton(self.groupBox_5)
        self.rad_autoSel_next.setObjectName(u"rad_autoSel_next")

        self.verticalLayout_8.addWidget(self.rad_autoSel_next)


        self.verticalLayout_9.addLayout(self.verticalLayout_8)


        self.verticalLayout.addWidget(self.groupBox_5)

        self.chk_autoMove = QCheckBox(self.groupBox_2)
        self.chk_autoMove.setObjectName(u"chk_autoMove")
        self.chk_autoMove.setChecked(False)

        self.verticalLayout.addWidget(self.chk_autoMove)

        self.chk_automove_xyonly = QCheckBox(self.groupBox_2)
        self.chk_automove_xyonly.setObjectName(u"chk_automove_xyonly")
        self.chk_automove_xyonly.setChecked(True)

        self.verticalLayout.addWidget(self.chk_automove_xyonly)


        self.verticalLayout_3.addLayout(self.verticalLayout)


        self.main_layout.addWidget(self.groupBox_2)

        self.btn_instructions = QPushButton(translator_xyz)
        self.btn_instructions.setObjectName(u"btn_instructions")

        self.main_layout.addWidget(self.btn_instructions)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.combo_meaCoor, self.btn_xy_topleft)
        QWidget.setTabOrder(self.btn_xy_topleft, self.btn_xy_topcentre)
        QWidget.setTabOrder(self.btn_xy_topcentre, self.btn_xy_topright)
        QWidget.setTabOrder(self.btn_xy_topright, self.btn_xy_centreleft)
        QWidget.setTabOrder(self.btn_xy_centreleft, self.btn_xy_centrecentre)
        QWidget.setTabOrder(self.btn_xy_centrecentre, self.btn_xy_centreright)
        QWidget.setTabOrder(self.btn_xy_centreright, self.btn_xy_bottomleft)
        QWidget.setTabOrder(self.btn_xy_bottomleft, self.btn_xy_bottomcentre)
        QWidget.setTabOrder(self.btn_xy_bottomcentre, self.btn_xy_bottomright)
        QWidget.setTabOrder(self.btn_xy_bottomright, self.btn_z_top)
        QWidget.setTabOrder(self.btn_z_top, self.btn_z_centre)
        QWidget.setTabOrder(self.btn_z_centre, self.btn_z_bottom)
        QWidget.setTabOrder(self.btn_z_bottom, self.btn_goto_refLoc)
        QWidget.setTabOrder(self.btn_goto_refLoc, self.spin_coorXUm)
        QWidget.setTabOrder(self.spin_coorXUm, self.spin_coorYUm)
        QWidget.setTabOrder(self.spin_coorYUm, self.spin_coorZUm)
        QWidget.setTabOrder(self.spin_coorZUm, self.btn_storeCoor)
        QWidget.setTabOrder(self.btn_storeCoor, self.btn_commit)
        QWidget.setTabOrder(self.btn_commit, self.chk_autoMove)
        QWidget.setTabOrder(self.chk_autoMove, self.btn_instructions)

        self.retranslateUi(translator_xyz)

        QMetaObject.connectSlotsByName(translator_xyz)
    # setupUi

    def retranslateUi(self, translator_xyz):
        translator_xyz.setWindowTitle(QCoreApplication.translate("translator_xyz", u"Form", None))
        self.label.setText(QCoreApplication.translate("translator_xyz", u"Select the Region of Interest to translate:", None))
        self.groupBox.setTitle("")
        self.groupBox_4.setTitle(QCoreApplication.translate("translator_xyz", u"XY-reference location", None))
        self.btn_xy_centreright.setText(QCoreApplication.translate("translator_xyz", u"Centre right", None))
        self.btn_xy_centrecentre.setText(QCoreApplication.translate("translator_xyz", u"Centre centre", None))
        self.btn_xy_topright.setText(QCoreApplication.translate("translator_xyz", u"Top right", None))
        self.btn_xy_bottomright.setText(QCoreApplication.translate("translator_xyz", u"Bottom right", None))
        self.btn_xy_centreleft.setText(QCoreApplication.translate("translator_xyz", u"Centre left", None))
        self.btn_xy_topleft.setText(QCoreApplication.translate("translator_xyz", u"Top left", None))
        self.btn_xy_bottomleft.setText(QCoreApplication.translate("translator_xyz", u"Bottom left", None))
        self.btn_xy_bottomcentre.setText(QCoreApplication.translate("translator_xyz", u"Bottom centre", None))
        self.btn_xy_topcentre.setText(QCoreApplication.translate("translator_xyz", u"Top centre", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("translator_xyz", u"Z-reference location", None))
        self.btn_z_bottom.setText(QCoreApplication.translate("translator_xyz", u"Bottom", None))
        self.btn_z_centre.setText(QCoreApplication.translate("translator_xyz", u"Centre", None))
        self.btn_z_top.setText(QCoreApplication.translate("translator_xyz", u"Top", None))
        self.btn_goto_refLoc.setText(QCoreApplication.translate("translator_xyz", u"Move stage to the reference location", None))
        self.label_2.setText(QCoreApplication.translate("translator_xyz", u"Previous coordinate (\u00b5m):", None))
        self.btn_commit.setText(QCoreApplication.translate("translator_xyz", u"Perform XYZ translation", None))
        self.btn_storeCoor.setText(QCoreApplication.translate("translator_xyz", u"Insert current coordinate", None))
        self.lbl_prevCoor.setText(QCoreApplication.translate("translator_xyz", u"None", None))
        self.label_3.setText(QCoreApplication.translate("translator_xyz", u"New coordinate (\u00b5m):", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("translator_xyz", u"Options", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("translator_xyz", u"Auto-select", None))
        self.rad_autoSel_lastModified.setText(QCoreApplication.translate("translator_xyz", u"The last modified (translated) ROI", None))
        self.rad_autoSel_next.setText(QCoreApplication.translate("translator_xyz", u"The next ROI", None))
        self.chk_autoMove.setText(QCoreApplication.translate("translator_xyz", u"Auto-move the stage using the last modified translation", None))
        self.chk_automove_xyonly.setText(QCoreApplication.translate("translator_xyz", u"Auto-move only in the XY-direction (exclude Z)", None))
        self.btn_instructions.setText(QCoreApplication.translate("translator_xyz", u"Show instructions", None))
    # retranslateUi

