# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gridify_setup.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

class Ui_gridify_setup(object):
    def setupUi(self, gridify_setup):
        if not gridify_setup.objectName():
            gridify_setup.setObjectName(u"gridify_setup")
        gridify_setup.resize(1074, 727)
        self.verticalLayout_2 = QVBoxLayout(gridify_setup)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.label = QLabel(gridify_setup)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.main_layout.addWidget(self.label)

        self.combo_roi = QComboBox(gridify_setup)
        self.combo_roi.setObjectName(u"combo_roi")

        self.main_layout.addWidget(self.combo_roi)

        self.groupBox = QGroupBox(gridify_setup)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout = QVBoxLayout(self.groupBox)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_4 = QGroupBox(self.groupBox)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.verticalLayout_11 = QVBoxLayout(self.groupBox_4)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_10 = QLabel(self.groupBox_4)
        self.label_10.setObjectName(u"label_10")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_10.sizePolicy().hasHeightForWidth())
        self.label_10.setSizePolicy(sizePolicy1)
        self.label_10.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_6.addWidget(self.label_10)

        self.spin_br_x = QDoubleSpinBox(self.groupBox_4)
        self.spin_br_x.setObjectName(u"spin_br_x")
        self.spin_br_x.setDecimals(1)
        self.spin_br_x.setMinimum(-1000000.000000000000000)
        self.spin_br_x.setMaximum(1000000.000000000000000)

        self.horizontalLayout_6.addWidget(self.spin_br_x)

        self.spin_br_y = QDoubleSpinBox(self.groupBox_4)
        self.spin_br_y.setObjectName(u"spin_br_y")
        self.spin_br_y.setDecimals(1)
        self.spin_br_y.setMinimum(-1000000.000000000000000)
        self.spin_br_y.setMaximum(1000000.000000000000000)

        self.horizontalLayout_6.addWidget(self.spin_br_y)

        self.spin_br_z = QDoubleSpinBox(self.groupBox_4)
        self.spin_br_z.setObjectName(u"spin_br_z")
        self.spin_br_z.setDecimals(1)
        self.spin_br_z.setMinimum(-1000000.000000000000000)
        self.spin_br_z.setMaximum(1000000.000000000000000)

        self.horizontalLayout_6.addWidget(self.spin_br_z)


        self.verticalLayout_7.addLayout(self.horizontalLayout_6)

        self.btn_currcoor_br = QPushButton(self.groupBox_4)
        self.btn_currcoor_br.setObjectName(u"btn_currcoor_br")

        self.verticalLayout_7.addWidget(self.btn_currcoor_br)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_11 = QLabel(self.groupBox_4)
        self.label_11.setObjectName(u"label_11")

        self.horizontalLayout_8.addWidget(self.label_11)

        self.combo_br_xy = QComboBox(self.groupBox_4)
        self.combo_br_xy.setObjectName(u"combo_br_xy")

        self.horizontalLayout_8.addWidget(self.combo_br_xy)

        self.combo_br_z = QComboBox(self.groupBox_4)
        self.combo_br_z.setObjectName(u"combo_br_z")

        self.horizontalLayout_8.addWidget(self.combo_br_z)


        self.verticalLayout_7.addLayout(self.horizontalLayout_8)


        self.verticalLayout_11.addLayout(self.verticalLayout_7)


        self.gridLayout.addWidget(self.groupBox_4, 1, 1, 1, 1)

        self.groupBox_3 = QGroupBox(self.groupBox)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_9 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_9 = QLabel(self.groupBox_3)
        self.label_9.setObjectName(u"label_9")
        sizePolicy1.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy1)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.label_9)

        self.spin_bl_x = QDoubleSpinBox(self.groupBox_3)
        self.spin_bl_x.setObjectName(u"spin_bl_x")
        self.spin_bl_x.setDecimals(1)
        self.spin_bl_x.setMinimum(-1000000.000000000000000)
        self.spin_bl_x.setMaximum(1000000.000000000000000)

        self.horizontalLayout_3.addWidget(self.spin_bl_x)

        self.spin_bl_y = QDoubleSpinBox(self.groupBox_3)
        self.spin_bl_y.setObjectName(u"spin_bl_y")
        self.spin_bl_y.setDecimals(1)
        self.spin_bl_y.setMinimum(-1000000.000000000000000)
        self.spin_bl_y.setMaximum(1000000.000000000000000)

        self.horizontalLayout_3.addWidget(self.spin_bl_y)

        self.spin_bl_z = QDoubleSpinBox(self.groupBox_3)
        self.spin_bl_z.setObjectName(u"spin_bl_z")
        self.spin_bl_z.setDecimals(1)
        self.spin_bl_z.setMinimum(-1000000.000000000000000)
        self.spin_bl_z.setMaximum(1000000.000000000000000)

        self.horizontalLayout_3.addWidget(self.spin_bl_z)


        self.verticalLayout_5.addLayout(self.horizontalLayout_3)

        self.btn_currcoor_bl = QPushButton(self.groupBox_3)
        self.btn_currcoor_bl.setObjectName(u"btn_currcoor_bl")

        self.verticalLayout_5.addWidget(self.btn_currcoor_bl)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_8 = QLabel(self.groupBox_3)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_4.addWidget(self.label_8)

        self.combo_bl_xy = QComboBox(self.groupBox_3)
        self.combo_bl_xy.setObjectName(u"combo_bl_xy")

        self.horizontalLayout_4.addWidget(self.combo_bl_xy)

        self.combo_bl_z = QComboBox(self.groupBox_3)
        self.combo_bl_z.setObjectName(u"combo_bl_z")

        self.horizontalLayout_4.addWidget(self.combo_bl_z)


        self.verticalLayout_5.addLayout(self.horizontalLayout_4)


        self.verticalLayout_9.addLayout(self.verticalLayout_5)


        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)

        self.groupBox_5 = QGroupBox(self.groupBox)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.verticalLayout_8 = QVBoxLayout(self.groupBox_5)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_4 = QLabel(self.groupBox_5)
        self.label_4.setObjectName(u"label_4")
        sizePolicy1.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy1)
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout.addWidget(self.label_4)

        self.spin_tl_x = QDoubleSpinBox(self.groupBox_5)
        self.spin_tl_x.setObjectName(u"spin_tl_x")
        self.spin_tl_x.setDecimals(1)
        self.spin_tl_x.setMinimum(-1000000.000000000000000)
        self.spin_tl_x.setMaximum(1000000.000000000000000)

        self.horizontalLayout.addWidget(self.spin_tl_x)

        self.spin_tl_y = QDoubleSpinBox(self.groupBox_5)
        self.spin_tl_y.setObjectName(u"spin_tl_y")
        self.spin_tl_y.setDecimals(1)
        self.spin_tl_y.setMinimum(-1000000.000000000000000)
        self.spin_tl_y.setMaximum(1000000.000000000000000)

        self.horizontalLayout.addWidget(self.spin_tl_y)

        self.spin_tl_z = QDoubleSpinBox(self.groupBox_5)
        self.spin_tl_z.setObjectName(u"spin_tl_z")
        self.spin_tl_z.setDecimals(1)
        self.spin_tl_z.setMinimum(-1000000.000000000000000)
        self.spin_tl_z.setMaximum(1000000.000000000000000)

        self.horizontalLayout.addWidget(self.spin_tl_z)


        self.verticalLayout_4.addLayout(self.horizontalLayout)

        self.btn_currcoor_tl = QPushButton(self.groupBox_5)
        self.btn_currcoor_tl.setObjectName(u"btn_currcoor_tl")

        self.verticalLayout_4.addWidget(self.btn_currcoor_tl)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_5 = QLabel(self.groupBox_5)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_2.addWidget(self.label_5)

        self.combo_tl_xy = QComboBox(self.groupBox_5)
        self.combo_tl_xy.setObjectName(u"combo_tl_xy")

        self.horizontalLayout_2.addWidget(self.combo_tl_xy)

        self.combo_tl_z = QComboBox(self.groupBox_5)
        self.combo_tl_z.setObjectName(u"combo_tl_z")

        self.horizontalLayout_2.addWidget(self.combo_tl_z)


        self.verticalLayout_4.addLayout(self.horizontalLayout_2)


        self.verticalLayout_8.addLayout(self.verticalLayout_4)


        self.gridLayout.addWidget(self.groupBox_5, 0, 0, 1, 1)

        self.groupBox_6 = QGroupBox(self.groupBox)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.verticalLayout_10 = QVBoxLayout(self.groupBox_6)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_6 = QLabel(self.groupBox_6)
        self.label_6.setObjectName(u"label_6")
        sizePolicy1.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy1)
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_5.addWidget(self.label_6)

        self.spin_tr_x = QDoubleSpinBox(self.groupBox_6)
        self.spin_tr_x.setObjectName(u"spin_tr_x")
        self.spin_tr_x.setDecimals(1)
        self.spin_tr_x.setMinimum(-1000000.000000000000000)
        self.spin_tr_x.setMaximum(1000000.000000000000000)

        self.horizontalLayout_5.addWidget(self.spin_tr_x)

        self.spin_tr_y = QDoubleSpinBox(self.groupBox_6)
        self.spin_tr_y.setObjectName(u"spin_tr_y")
        self.spin_tr_y.setDecimals(1)
        self.spin_tr_y.setMinimum(-1000000.000000000000000)
        self.spin_tr_y.setMaximum(1000000.000000000000000)

        self.horizontalLayout_5.addWidget(self.spin_tr_y)

        self.spin_tr_z = QDoubleSpinBox(self.groupBox_6)
        self.spin_tr_z.setObjectName(u"spin_tr_z")
        self.spin_tr_z.setDecimals(1)
        self.spin_tr_z.setMinimum(-1000000.000000000000000)
        self.spin_tr_z.setMaximum(1000000.000000000000000)

        self.horizontalLayout_5.addWidget(self.spin_tr_z)


        self.verticalLayout_6.addLayout(self.horizontalLayout_5)

        self.btn_currcoor_tr = QPushButton(self.groupBox_6)
        self.btn_currcoor_tr.setObjectName(u"btn_currcoor_tr")

        self.verticalLayout_6.addWidget(self.btn_currcoor_tr)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_7 = QLabel(self.groupBox_6)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_7.addWidget(self.label_7)

        self.combo_tr_xy = QComboBox(self.groupBox_6)
        self.combo_tr_xy.setObjectName(u"combo_tr_xy")

        self.horizontalLayout_7.addWidget(self.combo_tr_xy)

        self.combo_tr_z = QComboBox(self.groupBox_6)
        self.combo_tr_z.setObjectName(u"combo_tr_z")

        self.horizontalLayout_7.addWidget(self.combo_tr_z)


        self.verticalLayout_6.addLayout(self.horizontalLayout_7)


        self.verticalLayout_10.addLayout(self.verticalLayout_6)


        self.gridLayout.addWidget(self.groupBox_6, 0, 1, 1, 1)


        self.verticalLayout.addLayout(self.gridLayout)


        self.main_layout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(gridify_setup)
        self.groupBox_2.setObjectName(u"groupBox_2")
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName(u"label_2")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy2)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_2, 1, 0, 1, 1)

        self.label_3 = QLabel(self.groupBox_2)
        self.label_3.setObjectName(u"label_3")
        sizePolicy2.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy2)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_3, 0, 0, 1, 1)

        self.spin_row = QSpinBox(self.groupBox_2)
        self.spin_row.setObjectName(u"spin_row")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.spin_row.sizePolicy().hasHeightForWidth())
        self.spin_row.setSizePolicy(sizePolicy3)
        self.spin_row.setMinimum(1)
        self.spin_row.setMaximum(1000000)
        self.spin_row.setValue(2)

        self.gridLayout_2.addWidget(self.spin_row, 0, 1, 1, 1)

        self.spin_col = QSpinBox(self.groupBox_2)
        self.spin_col.setObjectName(u"spin_col")
        sizePolicy3.setHeightForWidth(self.spin_col.sizePolicy().hasHeightForWidth())
        self.spin_col.setSizePolicy(sizePolicy3)
        self.spin_col.setMinimum(1)
        self.spin_col.setMaximum(1000000)
        self.spin_col.setValue(2)

        self.gridLayout_2.addWidget(self.spin_col, 1, 1, 1, 1)


        self.verticalLayout_3.addLayout(self.gridLayout_2)


        self.main_layout.addWidget(self.groupBox_2)

        self.btn_finalise = QPushButton(gridify_setup)
        self.btn_finalise.setObjectName(u"btn_finalise")

        self.main_layout.addWidget(self.btn_finalise)

        self.btn_instructions = QPushButton(gridify_setup)
        self.btn_instructions.setObjectName(u"btn_instructions")

        self.main_layout.addWidget(self.btn_instructions)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.combo_roi, self.spin_tl_x)
        QWidget.setTabOrder(self.spin_tl_x, self.spin_tl_y)
        QWidget.setTabOrder(self.spin_tl_y, self.spin_tl_z)
        QWidget.setTabOrder(self.spin_tl_z, self.btn_currcoor_tl)
        QWidget.setTabOrder(self.btn_currcoor_tl, self.combo_tl_xy)
        QWidget.setTabOrder(self.combo_tl_xy, self.combo_tl_z)
        QWidget.setTabOrder(self.combo_tl_z, self.spin_tr_x)
        QWidget.setTabOrder(self.spin_tr_x, self.spin_tr_y)
        QWidget.setTabOrder(self.spin_tr_y, self.spin_tr_z)
        QWidget.setTabOrder(self.spin_tr_z, self.btn_currcoor_tr)
        QWidget.setTabOrder(self.btn_currcoor_tr, self.combo_tr_xy)
        QWidget.setTabOrder(self.combo_tr_xy, self.combo_tr_z)
        QWidget.setTabOrder(self.combo_tr_z, self.spin_bl_x)
        QWidget.setTabOrder(self.spin_bl_x, self.spin_bl_y)
        QWidget.setTabOrder(self.spin_bl_y, self.spin_bl_z)
        QWidget.setTabOrder(self.spin_bl_z, self.btn_currcoor_bl)
        QWidget.setTabOrder(self.btn_currcoor_bl, self.combo_bl_xy)
        QWidget.setTabOrder(self.combo_bl_xy, self.combo_bl_z)
        QWidget.setTabOrder(self.combo_bl_z, self.spin_br_x)
        QWidget.setTabOrder(self.spin_br_x, self.spin_br_y)
        QWidget.setTabOrder(self.spin_br_y, self.spin_br_z)
        QWidget.setTabOrder(self.spin_br_z, self.btn_currcoor_br)
        QWidget.setTabOrder(self.btn_currcoor_br, self.combo_br_xy)
        QWidget.setTabOrder(self.combo_br_xy, self.combo_br_z)
        QWidget.setTabOrder(self.combo_br_z, self.spin_row)
        QWidget.setTabOrder(self.spin_row, self.spin_col)
        QWidget.setTabOrder(self.spin_col, self.btn_finalise)
        QWidget.setTabOrder(self.btn_finalise, self.btn_instructions)

        self.retranslateUi(gridify_setup)

        QMetaObject.connectSlotsByName(gridify_setup)
    # setupUi

    def retranslateUi(self, gridify_setup):
        gridify_setup.setWindowTitle(QCoreApplication.translate("gridify_setup", u"Form", None))
        self.label.setText(QCoreApplication.translate("gridify_setup", u"Select the Region of Interest to gridify:", None))
        self.groupBox.setTitle(QCoreApplication.translate("gridify_setup", u"Reference coordinates setup", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("gridify_setup", u"Bottom right", None))
        self.label_10.setText(QCoreApplication.translate("gridify_setup", u"Ref. coor (x,y,z) [\u00b5m]", None))
        self.btn_currcoor_br.setText(QCoreApplication.translate("gridify_setup", u"Insert current coordinate", None))
        self.label_11.setText(QCoreApplication.translate("gridify_setup", u"Location (xy,z)", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("gridify_setup", u"Bottom left", None))
        self.label_9.setText(QCoreApplication.translate("gridify_setup", u"Ref. coor (x,y,z) [\u00b5m]", None))
        self.btn_currcoor_bl.setText(QCoreApplication.translate("gridify_setup", u"Insert current coordinate", None))
        self.label_8.setText(QCoreApplication.translate("gridify_setup", u"Location (xy,z)", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("gridify_setup", u"Top left", None))
        self.label_4.setText(QCoreApplication.translate("gridify_setup", u"Ref. coor (x,y,z) [\u00b5m]", None))
        self.btn_currcoor_tl.setText(QCoreApplication.translate("gridify_setup", u"Insert current coordinate", None))
        self.label_5.setText(QCoreApplication.translate("gridify_setup", u"Location (xy,z)", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("gridify_setup", u"Top right", None))
        self.label_6.setText(QCoreApplication.translate("gridify_setup", u"Ref. coor (x,y,z) [\u00b5m]", None))
        self.btn_currcoor_tr.setText(QCoreApplication.translate("gridify_setup", u"Insert current coordinate", None))
        self.label_7.setText(QCoreApplication.translate("gridify_setup", u"Location (xy,z)", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("gridify_setup", u"Row and column setup", None))
        self.label_2.setText(QCoreApplication.translate("gridify_setup", u"Number of columns:", None))
        self.label_3.setText(QCoreApplication.translate("gridify_setup", u"Number of rows:", None))
        self.btn_finalise.setText(QCoreApplication.translate("gridify_setup", u"Finalise setup and proceed to gridify the setup", None))
        self.btn_instructions.setText(QCoreApplication.translate("gridify_setup", u"Show instructions", None))
    # retranslateUi

