# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rect_startend.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSpacerItem, QWidget)

class Ui_meaCoor_Rect_StartEnd(object):
    def setupUi(self, meaCoor_Rect_StartEnd):
        if not meaCoor_Rect_StartEnd.objectName():
            meaCoor_Rect_StartEnd.setObjectName(u"meaCoor_Rect_StartEnd")
        meaCoor_Rect_StartEnd.resize(673, 422)
        self.gridLayoutWidget = QWidget(meaCoor_Rect_StartEnd)
        self.gridLayoutWidget.setObjectName(u"gridLayoutWidget")
        self.gridLayoutWidget.setGeometry(QRect(20, 10, 623, 381))
        self.gridLayout = QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label_4 = QLabel(self.gridLayoutWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 1, 3, 1, 1)

        self.label_17 = QLabel(self.gridLayoutWidget)
        self.label_17.setObjectName(u"label_17")

        self.gridLayout.addWidget(self.label_17, 10, 0, 1, 1)

        self.ent_res_pt_x = QLineEdit(self.gridLayoutWidget)
        self.ent_res_pt_x.setObjectName(u"ent_res_pt_x")

        self.gridLayout.addWidget(self.ent_res_pt_x, 10, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 12, 1, 1, 1)

        self.label_10 = QLabel(self.gridLayoutWidget)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout.addWidget(self.label_10, 4, 5, 1, 1)

        self.ent_res_pt_y = QLineEdit(self.gridLayoutWidget)
        self.ent_res_pt_y.setObjectName(u"ent_res_pt_y")

        self.gridLayout.addWidget(self.ent_res_pt_y, 10, 4, 1, 1)

        self.label_12 = QLabel(self.gridLayoutWidget)
        self.label_12.setObjectName(u"label_12")

        self.gridLayout.addWidget(self.label_12, 7, 2, 1, 1)

        self.label_8 = QLabel(self.gridLayoutWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.gridLayout.addWidget(self.label_8, 3, 0, 1, 3)

        self.label_3 = QLabel(self.gridLayoutWidget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 1, 2, 1, 1)

        self.label_9 = QLabel(self.gridLayoutWidget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_9, 4, 0, 1, 1)

        self.label_21 = QLabel(self.gridLayoutWidget)
        self.label_21.setObjectName(u"label_21")

        self.gridLayout.addWidget(self.label_21, 10, 3, 1, 1)

        self.label_11 = QLabel(self.gridLayoutWidget)
        self.label_11.setObjectName(u"label_11")

        self.gridLayout.addWidget(self.label_11, 11, 0, 1, 1)

        self.label_20 = QLabel(self.gridLayoutWidget)
        self.label_20.setObjectName(u"label_20")

        self.gridLayout.addWidget(self.label_20, 11, 3, 1, 1)

        self.ent_z_um = QLineEdit(self.gridLayoutWidget)
        self.ent_z_um.setObjectName(u"ent_z_um")

        self.gridLayout.addWidget(self.ent_z_um, 7, 1, 1, 1)

        self.label_14 = QLabel(self.gridLayoutWidget)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_14, 7, 0, 1, 1)

        self.ent_res_um_x = QLineEdit(self.gridLayoutWidget)
        self.ent_res_um_x.setObjectName(u"ent_res_um_x")

        self.gridLayout.addWidget(self.ent_res_um_x, 11, 1, 1, 1)

        self.label_15 = QLabel(self.gridLayoutWidget)
        self.label_15.setObjectName(u"label_15")

        self.gridLayout.addWidget(self.label_15, 10, 2, 1, 1)

        self.ent_starty_um = QLineEdit(self.gridLayoutWidget)
        self.ent_starty_um.setObjectName(u"ent_starty_um")

        self.gridLayout.addWidget(self.ent_starty_um, 1, 4, 1, 1)

        self.label_6 = QLabel(self.gridLayoutWidget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_6, 4, 3, 1, 1)

        self.ent_endy_um = QLineEdit(self.gridLayoutWidget)
        self.ent_endy_um.setObjectName(u"ent_endy_um")

        self.gridLayout.addWidget(self.ent_endy_um, 4, 4, 1, 1)

        self.label_7 = QLabel(self.gridLayoutWidget)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout.addWidget(self.label_7, 4, 2, 1, 1)

        self.ent_startx_um = QLineEdit(self.gridLayoutWidget)
        self.ent_startx_um.setObjectName(u"ent_startx_um")

        self.gridLayout.addWidget(self.ent_startx_um, 1, 1, 1, 1)

        self.ent_res_um_y = QLineEdit(self.gridLayoutWidget)
        self.ent_res_um_y.setObjectName(u"ent_res_um_y")

        self.gridLayout.addWidget(self.ent_res_um_y, 11, 4, 1, 1)

        self.label_16 = QLabel(self.gridLayoutWidget)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.gridLayout.addWidget(self.label_16, 9, 0, 1, 3)

        self.label = QLabel(self.gridLayoutWidget)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)

        self.ent_endx_um = QLineEdit(self.gridLayoutWidget)
        self.ent_endx_um.setObjectName(u"ent_endx_um")

        self.gridLayout.addWidget(self.ent_endx_um, 4, 1, 1, 1)

        self.label_2 = QLabel(self.gridLayoutWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label_5 = QLabel(self.gridLayoutWidget)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 1, 5, 1, 1)

        self.label_19 = QLabel(self.gridLayoutWidget)
        self.label_19.setObjectName(u"label_19")

        self.gridLayout.addWidget(self.label_19, 10, 5, 1, 1)

        self.label_18 = QLabel(self.gridLayoutWidget)
        self.label_18.setObjectName(u"label_18")

        self.gridLayout.addWidget(self.label_18, 11, 2, 1, 1)

        self.label_13 = QLabel(self.gridLayoutWidget)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.gridLayout.addWidget(self.label_13, 6, 0, 1, 3)

        self.label_22 = QLabel(self.gridLayoutWidget)
        self.label_22.setObjectName(u"label_22")

        self.gridLayout.addWidget(self.label_22, 11, 5, 1, 1)

        self.btn_curr_start_xy = QPushButton(self.gridLayoutWidget)
        self.btn_curr_start_xy.setObjectName(u"btn_curr_start_xy")

        self.gridLayout.addWidget(self.btn_curr_start_xy, 2, 0, 1, 6)

        self.btn_curr_end_xy = QPushButton(self.gridLayoutWidget)
        self.btn_curr_end_xy.setObjectName(u"btn_curr_end_xy")

        self.gridLayout.addWidget(self.btn_curr_end_xy, 5, 0, 1, 6)

        self.btn_curr_z = QPushButton(self.gridLayoutWidget)
        self.btn_curr_z.setObjectName(u"btn_curr_z")

        self.gridLayout.addWidget(self.btn_curr_z, 8, 0, 1, 6)

        QWidget.setTabOrder(self.ent_startx_um, self.ent_starty_um)
        QWidget.setTabOrder(self.ent_starty_um, self.ent_endx_um)
        QWidget.setTabOrder(self.ent_endx_um, self.ent_endy_um)
        QWidget.setTabOrder(self.ent_endy_um, self.ent_z_um)
        QWidget.setTabOrder(self.ent_z_um, self.ent_res_pt_x)
        QWidget.setTabOrder(self.ent_res_pt_x, self.ent_res_pt_y)
        QWidget.setTabOrder(self.ent_res_pt_y, self.ent_res_um_x)
        QWidget.setTabOrder(self.ent_res_um_x, self.ent_res_um_y)

        self.retranslateUi(meaCoor_Rect_StartEnd)

        QMetaObject.connectSlotsByName(meaCoor_Rect_StartEnd)
    # setupUi

    def retranslateUi(self, meaCoor_Rect_StartEnd):
        meaCoor_Rect_StartEnd.setWindowTitle(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Form", None))
        self.label_4.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
        self.label_17.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.label_10.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_12.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_8.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"End XY coordinate:", None))
        self.label_3.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_9.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.label_21.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
        self.label_11.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.label_20.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
        self.label_14.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Z:", None))
        self.label_15.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"points", None))
        self.label_6.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
        self.label_7.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_16.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Imaging resolution:", None))
        self.label.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Start XY coordinate:", None))
        self.label_2.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.label_5.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_19.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"points", None))
        self.label_18.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_13.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Z coordinate:", None))
        self.label_22.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.btn_curr_start_xy.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Start coordinate: Insert current XY coordinates", None))
        self.btn_curr_end_xy.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"End coordinate: Insert current XY coordinates", None))
        self.btn_curr_z.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Insert current Z-coordinate", None))
    # retranslateUi

