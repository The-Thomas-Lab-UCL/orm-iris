# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'convert_2Dto3D.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QWidget)

class Ui_converter_2Dto3D(object):
    def setupUi(self, converter_2Dto3D):
        if not converter_2Dto3D.objectName():
            converter_2Dto3D.setObjectName(u"converter_2Dto3D")
        converter_2Dto3D.resize(801, 85)
        self.horizontalLayout = QHBoxLayout(converter_2Dto3D)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lyt_main = QGridLayout()
        self.lyt_main.setObjectName(u"lyt_main")
        self.ent_zstart_um = QLineEdit(converter_2Dto3D)
        self.ent_zstart_um.setObjectName(u"ent_zstart_um")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.ent_zstart_um.sizePolicy().hasHeightForWidth())
        self.ent_zstart_um.setSizePolicy(sizePolicy)

        self.lyt_main.addWidget(self.ent_zstart_um, 0, 1, 1, 1)

        self.label = QLabel(converter_2Dto3D)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_main.addWidget(self.label, 0, 0, 1, 1)

        self.ent_zend_um = QLineEdit(converter_2Dto3D)
        self.ent_zend_um.setObjectName(u"ent_zend_um")
        sizePolicy.setHeightForWidth(self.ent_zend_um.sizePolicy().hasHeightForWidth())
        self.ent_zend_um.setSizePolicy(sizePolicy)

        self.lyt_main.addWidget(self.ent_zend_um, 0, 4, 1, 1)

        self.label_2 = QLabel(converter_2Dto3D)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_main.addWidget(self.label_2, 0, 3, 1, 1)

        self.btn_currcoor_start = QPushButton(converter_2Dto3D)
        self.btn_currcoor_start.setObjectName(u"btn_currcoor_start")

        self.lyt_main.addWidget(self.btn_currcoor_start, 0, 2, 1, 1)

        self.btn_currcoor_end = QPushButton(converter_2Dto3D)
        self.btn_currcoor_end.setObjectName(u"btn_currcoor_end")

        self.lyt_main.addWidget(self.btn_currcoor_end, 0, 5, 1, 1)

        self.label_3 = QLabel(converter_2Dto3D)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_main.addWidget(self.label_3, 1, 0, 1, 1)

        self.ent_res_pt = QLineEdit(converter_2Dto3D)
        self.ent_res_pt.setObjectName(u"ent_res_pt")
        sizePolicy.setHeightForWidth(self.ent_res_pt.sizePolicy().hasHeightForWidth())
        self.ent_res_pt.setSizePolicy(sizePolicy)

        self.lyt_main.addWidget(self.ent_res_pt, 1, 1, 1, 1)

        self.label_4 = QLabel(converter_2Dto3D)
        self.label_4.setObjectName(u"label_4")

        self.lyt_main.addWidget(self.label_4, 1, 2, 1, 1)

        self.label_6 = QLabel(converter_2Dto3D)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_main.addWidget(self.label_6, 1, 3, 1, 1)

        self.ent_res_um = QLineEdit(converter_2Dto3D)
        self.ent_res_um.setObjectName(u"ent_res_um")
        sizePolicy.setHeightForWidth(self.ent_res_um.sizePolicy().hasHeightForWidth())
        self.ent_res_um.setSizePolicy(sizePolicy)

        self.lyt_main.addWidget(self.ent_res_um, 1, 4, 1, 1)

        self.label_5 = QLabel(converter_2Dto3D)
        self.label_5.setObjectName(u"label_5")

        self.lyt_main.addWidget(self.label_5, 1, 5, 1, 1)


        self.horizontalLayout.addLayout(self.lyt_main)

        QWidget.setTabOrder(self.ent_zstart_um, self.btn_currcoor_start)
        QWidget.setTabOrder(self.btn_currcoor_start, self.ent_zend_um)
        QWidget.setTabOrder(self.ent_zend_um, self.btn_currcoor_end)
        QWidget.setTabOrder(self.btn_currcoor_end, self.ent_res_pt)
        QWidget.setTabOrder(self.ent_res_pt, self.ent_res_um)

        self.retranslateUi(converter_2Dto3D)

        QMetaObject.connectSlotsByName(converter_2Dto3D)
    # setupUi

    def retranslateUi(self, converter_2Dto3D):
        converter_2Dto3D.setWindowTitle(QCoreApplication.translate("converter_2Dto3D", u"Form", None))
        self.label.setText(QCoreApplication.translate("converter_2Dto3D", u"Z-start (\u00b5m):", None))
        self.label_2.setText(QCoreApplication.translate("converter_2Dto3D", u"Z-end (\u00b5m):", None))
        self.btn_currcoor_start.setText(QCoreApplication.translate("converter_2Dto3D", u"Insert current location", None))
        self.btn_currcoor_end.setText(QCoreApplication.translate("converter_2Dto3D", u"Insert current location", None))
        self.label_3.setText(QCoreApplication.translate("converter_2Dto3D", u"Resolution:", None))
        self.ent_res_pt.setText(QCoreApplication.translate("converter_2Dto3D", u"2", None))
        self.label_4.setText(QCoreApplication.translate("converter_2Dto3D", u"points", None))
        self.label_6.setText(QCoreApplication.translate("converter_2Dto3D", u"Resolution:", None))
        self.label_5.setText(QCoreApplication.translate("converter_2Dto3D", u"\u00b5m", None))
    # retranslateUi

