# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'tiling_method_control.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_tiling_method_control(object):
    def setupUi(self, tiling_method_control):
        if not tiling_method_control.objectName():
            tiling_method_control.setObjectName(u"tiling_method_control")
        tiling_method_control.resize(679, 656)
        self.verticalLayoutWidget = QWidget(tiling_method_control)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(20, 10, 645, 631))
        self.main_layout = QVBoxLayout(self.verticalLayoutWidget)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.chk_ZOverride = QCheckBox(self.verticalLayoutWidget)
        self.chk_ZOverride.setObjectName(u"chk_ZOverride")

        self.main_layout.addWidget(self.chk_ZOverride)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(self.verticalLayoutWidget)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.label)

        self.ent_zcoor = QLineEdit(self.verticalLayoutWidget)
        self.ent_zcoor.setObjectName(u"ent_zcoor")

        self.horizontalLayout_2.addWidget(self.ent_zcoor)

        self.label_5 = QLabel(self.verticalLayoutWidget)
        self.label_5.setObjectName(u"label_5")
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.label_5)

        self.btn_currZCoor = QPushButton(self.verticalLayoutWidget)
        self.btn_currZCoor.setObjectName(u"btn_currZCoor")
        sizePolicy.setHeightForWidth(self.btn_currZCoor.sizePolicy().hasHeightForWidth())
        self.btn_currZCoor.setSizePolicy(sizePolicy)

        self.horizontalLayout_2.addWidget(self.btn_currZCoor)


        self.main_layout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_2 = QLabel(self.verticalLayoutWidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.label_2)

        self.spin_cropx = QDoubleSpinBox(self.verticalLayoutWidget)
        self.spin_cropx.setObjectName(u"spin_cropx")

        self.horizontalLayout_3.addWidget(self.spin_cropx)

        self.label_4 = QLabel(self.verticalLayoutWidget)
        self.label_4.setObjectName(u"label_4")
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.label_4)

        self.label_3 = QLabel(self.verticalLayoutWidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_3.addWidget(self.label_3)

        self.spin_cropy = QDoubleSpinBox(self.verticalLayoutWidget)
        self.spin_cropy.setObjectName(u"spin_cropy")

        self.horizontalLayout_3.addWidget(self.spin_cropy)

        self.label_6 = QLabel(self.verticalLayoutWidget)
        self.label_6.setObjectName(u"label_6")
        sizePolicy.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.label_6)


        self.main_layout.addLayout(self.horizontalLayout_3)

        QWidget.setTabOrder(self.chk_ZOverride, self.ent_zcoor)
        QWidget.setTabOrder(self.ent_zcoor, self.btn_currZCoor)
        QWidget.setTabOrder(self.btn_currZCoor, self.spin_cropx)
        QWidget.setTabOrder(self.spin_cropx, self.spin_cropy)

        self.retranslateUi(tiling_method_control)

        QMetaObject.connectSlotsByName(tiling_method_control)
    # setupUi

    def retranslateUi(self, tiling_method_control):
        tiling_method_control.setWindowTitle(QCoreApplication.translate("tiling_method_control", u"Form", None))
        self.chk_ZOverride.setText(QCoreApplication.translate("tiling_method_control", u"Override Z-coordinate for the tiling process", None))
        self.label.setText(QCoreApplication.translate("tiling_method_control", u"Z-coordinate:", None))
        self.label_5.setText(QCoreApplication.translate("tiling_method_control", u"\u00b5m", None))
        self.btn_currZCoor.setText(QCoreApplication.translate("tiling_method_control", u"Set current Z-coordinate", None))
        self.label_2.setText(QCoreApplication.translate("tiling_method_control", u"Crop-X:", None))
        self.label_4.setText(QCoreApplication.translate("tiling_method_control", u"%", None))
        self.label_3.setText(QCoreApplication.translate("tiling_method_control", u"Crop-Y:", None))
        self.label_6.setText(QCoreApplication.translate("tiling_method_control", u"%", None))
    # retranslateUi

