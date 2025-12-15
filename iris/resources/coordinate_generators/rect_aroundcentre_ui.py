# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rect_aroundcentre.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QGridLayout, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QWidget)

class Ui_meaCoor_Rect_StartEnd(object):
    def setupUi(self, meaCoor_Rect_StartEnd):
        if not meaCoor_Rect_StartEnd.objectName():
            meaCoor_Rect_StartEnd.setObjectName(u"meaCoor_Rect_StartEnd")
        meaCoor_Rect_StartEnd.resize(673, 422)
        self.gridLayoutWidget = QWidget(meaCoor_Rect_StartEnd)
        self.gridLayoutWidget.setObjectName(u"gridLayoutWidget")
        self.gridLayoutWidget.setGeometry(QRect(20, 10, 623, 381))
        self.main_layout = QGridLayout(self.gridLayoutWidget)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.label_11 = QLabel(self.gridLayoutWidget)
        self.label_11.setObjectName(u"label_11")

        self.main_layout.addWidget(self.label_11, 10, 0, 1, 1)

        self.btn_storecentre = QPushButton(self.gridLayoutWidget)
        self.btn_storecentre.setObjectName(u"btn_storecentre")

        self.main_layout.addWidget(self.btn_storecentre, 2, 0, 1, 6)

        self.label_10 = QLabel(self.gridLayoutWidget)
        self.label_10.setObjectName(u"label_10")

        self.main_layout.addWidget(self.label_10, 4, 5, 1, 1)

        self.label_3 = QLabel(self.gridLayoutWidget)
        self.label_3.setObjectName(u"label_3")

        self.main_layout.addWidget(self.label_3, 1, 2, 1, 1)

        self.label_18 = QLabel(self.gridLayoutWidget)
        self.label_18.setObjectName(u"label_18")

        self.main_layout.addWidget(self.label_18, 10, 2, 1, 1)

        self.label_15 = QLabel(self.gridLayoutWidget)
        self.label_15.setObjectName(u"label_15")

        self.main_layout.addWidget(self.label_15, 9, 2, 1, 1)

        self.label_22 = QLabel(self.gridLayoutWidget)
        self.label_22.setObjectName(u"label_22")

        self.main_layout.addWidget(self.label_22, 10, 5, 1, 1)

        self.label_4 = QLabel(self.gridLayoutWidget)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(self.label_4, 1, 3, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer, 11, 1, 1, 1)

        self.label_13 = QLabel(self.gridLayoutWidget)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label_13, 5, 0, 1, 3)

        self.label_2 = QLabel(self.gridLayoutWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label_16 = QLabel(self.gridLayoutWidget)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label_16, 8, 0, 1, 3)

        self.label_9 = QLabel(self.gridLayoutWidget)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(self.label_9, 4, 0, 1, 1)

        self.label_17 = QLabel(self.gridLayoutWidget)
        self.label_17.setObjectName(u"label_17")

        self.main_layout.addWidget(self.label_17, 9, 0, 1, 1)

        self.label_7 = QLabel(self.gridLayoutWidget)
        self.label_7.setObjectName(u"label_7")

        self.main_layout.addWidget(self.label_7, 4, 2, 1, 1)

        self.label_6 = QLabel(self.gridLayoutWidget)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(self.label_6, 4, 3, 1, 1)

        self.label_19 = QLabel(self.gridLayoutWidget)
        self.label_19.setObjectName(u"label_19")

        self.main_layout.addWidget(self.label_19, 9, 5, 1, 1)

        self.label_20 = QLabel(self.gridLayoutWidget)
        self.label_20.setObjectName(u"label_20")

        self.main_layout.addWidget(self.label_20, 10, 3, 1, 1)

        self.label_8 = QLabel(self.gridLayoutWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label_8, 3, 0, 1, 3)

        self.label = QLabel(self.gridLayoutWidget)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label, 0, 0, 1, 3)

        self.label_14 = QLabel(self.gridLayoutWidget)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.main_layout.addWidget(self.label_14, 6, 0, 1, 1)

        self.btn_storez = QPushButton(self.gridLayoutWidget)
        self.btn_storez.setObjectName(u"btn_storez")

        self.main_layout.addWidget(self.btn_storez, 7, 0, 1, 6)

        self.label_12 = QLabel(self.gridLayoutWidget)
        self.label_12.setObjectName(u"label_12")

        self.main_layout.addWidget(self.label_12, 6, 2, 1, 1)

        self.label_5 = QLabel(self.gridLayoutWidget)
        self.label_5.setObjectName(u"label_5")

        self.main_layout.addWidget(self.label_5, 1, 5, 1, 1)

        self.label_21 = QLabel(self.gridLayoutWidget)
        self.label_21.setObjectName(u"label_21")

        self.main_layout.addWidget(self.label_21, 9, 3, 1, 1)

        self.spin_centrex = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_centrex.setObjectName(u"spin_centrex")
        self.spin_centrex.setDecimals(1)
        self.spin_centrex.setMinimum(-1000000.000000000000000)
        self.spin_centrex.setMaximum(1000000.000000000000000)

        self.main_layout.addWidget(self.spin_centrex, 1, 1, 1, 1)

        self.spin_centrey = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_centrey.setObjectName(u"spin_centrey")
        self.spin_centrey.setDecimals(1)
        self.spin_centrey.setMinimum(-1000000.000000000000000)
        self.spin_centrey.setMaximum(1000000.000000000000000)

        self.main_layout.addWidget(self.spin_centrey, 1, 4, 1, 1)

        self.spin_widx = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_widx.setObjectName(u"spin_widx")
        self.spin_widx.setDecimals(1)
        self.spin_widx.setMinimum(1.000000000000000)
        self.spin_widx.setMaximum(1000000.000000000000000)

        self.main_layout.addWidget(self.spin_widx, 4, 1, 1, 1)

        self.spin_heiy = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_heiy.setObjectName(u"spin_heiy")
        self.spin_heiy.setDecimals(1)
        self.spin_heiy.setMinimum(1.000000000000000)
        self.spin_heiy.setMaximum(1000000.000000000000000)

        self.main_layout.addWidget(self.spin_heiy, 4, 4, 1, 1)

        self.spin_z = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_z.setObjectName(u"spin_z")
        self.spin_z.setDecimals(1)
        self.spin_z.setMinimum(-1000000.000000000000000)
        self.spin_z.setMaximum(1000000.000000000000000)

        self.main_layout.addWidget(self.spin_z, 6, 1, 1, 1)

        self.spin_resxpt = QSpinBox(self.gridLayoutWidget)
        self.spin_resxpt.setObjectName(u"spin_resxpt")
        self.spin_resxpt.setMinimum(1)
        self.spin_resxpt.setMaximum(1000000)

        self.main_layout.addWidget(self.spin_resxpt, 9, 1, 1, 1)

        self.spin_resypt = QSpinBox(self.gridLayoutWidget)
        self.spin_resypt.setObjectName(u"spin_resypt")
        self.spin_resypt.setMinimum(1)
        self.spin_resypt.setMaximum(1000000)

        self.main_layout.addWidget(self.spin_resypt, 9, 4, 1, 1)

        self.spin_resxum = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_resxum.setObjectName(u"spin_resxum")
        self.spin_resxum.setDecimals(1)
        self.spin_resxum.setMinimum(-1000000.000000000000000)
        self.spin_resxum.setMaximum(1000000.000000000000000)
        self.spin_resxum.setValue(1.000000000000000)

        self.main_layout.addWidget(self.spin_resxum, 10, 1, 1, 1)

        self.spin_resyum = QDoubleSpinBox(self.gridLayoutWidget)
        self.spin_resyum.setObjectName(u"spin_resyum")
        self.spin_resyum.setDecimals(1)
        self.spin_resyum.setMinimum(-1000000.000000000000000)
        self.spin_resyum.setMaximum(1000000.000000000000000)
        self.spin_resyum.setValue(1.000000000000000)

        self.main_layout.addWidget(self.spin_resyum, 10, 4, 1, 1)


        self.retranslateUi(meaCoor_Rect_StartEnd)

        QMetaObject.connectSlotsByName(meaCoor_Rect_StartEnd)
    # setupUi

    def retranslateUi(self, meaCoor_Rect_StartEnd):
        meaCoor_Rect_StartEnd.setWindowTitle(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Form", None))
        self.label_11.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.btn_storecentre.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Centre coordinate: Insert current XY coordinates", None))
        self.label_10.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_3.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_18.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_15.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"points", None))
        self.label_22.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_4.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
        self.label_13.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Z coordinate:", None))
        self.label_2.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.label_16.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Imaging resolution:", None))
        self.label_9.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Width (X):", None))
        self.label_17.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"X:", None))
        self.label_7.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_6.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Height (Y):", None))
        self.label_19.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"points", None))
        self.label_20.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
        self.label_8.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"ROI rectangle parameters", None))
        self.label.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Centre XY coordinate:", None))
        self.label_14.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Z:", None))
        self.btn_storez.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Insert current Z-coordinate", None))
        self.label_12.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_5.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"\u00b5m", None))
        self.label_21.setText(QCoreApplication.translate("meaCoor_Rect_StartEnd", u"Y:", None))
    # retranslateUi

