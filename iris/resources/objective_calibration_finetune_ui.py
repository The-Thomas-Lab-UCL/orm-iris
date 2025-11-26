# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'objective_calibration_finetune.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget)

class Ui_calibration_finetune(object):
    def setupUi(self, calibration_finetune):
        if not calibration_finetune.objectName():
            calibration_finetune.setObjectName(u"calibration_finetune")
        calibration_finetune.resize(650, 546)
        self.horizontalLayout_3 = QHBoxLayout(calibration_finetune)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(calibration_finetune)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.setObjectName(u"vertical_layout")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.spin_scaley = QDoubleSpinBox(self.groupBox)
        self.spin_scaley.setObjectName(u"spin_scaley")
        self.spin_scaley.setEnabled(False)

        self.gridLayout.addWidget(self.spin_scaley, 1, 1, 1, 1)

        self.label_5 = QLabel(self.groupBox)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_5, 4, 0, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)

        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 3, 0, 1, 1)

        self.spin_offsetx = QDoubleSpinBox(self.groupBox)
        self.spin_offsetx.setObjectName(u"spin_offsetx")
        self.spin_offsetx.setEnabled(False)

        self.gridLayout.addWidget(self.spin_offsetx, 2, 1, 1, 1)

        self.spin_offsety = QDoubleSpinBox(self.groupBox)
        self.spin_offsety.setObjectName(u"spin_offsety")
        self.spin_offsety.setEnabled(False)

        self.gridLayout.addWidget(self.spin_offsety, 3, 1, 1, 1)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.spin_rotdeg = QDoubleSpinBox(self.groupBox)
        self.spin_rotdeg.setObjectName(u"spin_rotdeg")
        self.spin_rotdeg.setEnabled(False)

        self.gridLayout.addWidget(self.spin_rotdeg, 4, 1, 1, 1)

        self.spin_scalex = QDoubleSpinBox(self.groupBox)
        self.spin_scalex.setObjectName(u"spin_scalex")
        self.spin_scalex.setEnabled(False)

        self.gridLayout.addWidget(self.spin_scalex, 0, 1, 1, 1)

        self.label_6 = QLabel(self.groupBox)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout.addWidget(self.label_6, 0, 2, 1, 1)

        self.label_7 = QLabel(self.groupBox)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout.addWidget(self.label_7, 1, 2, 1, 1)

        self.label_8 = QLabel(self.groupBox)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout.addWidget(self.label_8, 2, 2, 1, 1)

        self.label_9 = QLabel(self.groupBox)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout.addWidget(self.label_9, 3, 2, 1, 1)

        self.label_10 = QLabel(self.groupBox)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout.addWidget(self.label_10, 4, 2, 1, 1)


        self.vertical_layout.addLayout(self.gridLayout)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_perform_finetune = QPushButton(self.groupBox)
        self.btn_perform_finetune.setObjectName(u"btn_perform_finetune")

        self.horizontalLayout.addWidget(self.btn_perform_finetune)

        self.btn_commit_finetune = QPushButton(self.groupBox)
        self.btn_commit_finetune.setObjectName(u"btn_commit_finetune")
        self.btn_commit_finetune.setEnabled(False)

        self.horizontalLayout.addWidget(self.btn_commit_finetune)


        self.vertical_layout.addLayout(self.horizontalLayout)


        self.horizontalLayout_2.addLayout(self.vertical_layout)


        self.main_layout.addWidget(self.groupBox)


        self.horizontalLayout_3.addLayout(self.main_layout)


        self.retranslateUi(calibration_finetune)

        QMetaObject.connectSlotsByName(calibration_finetune)
    # setupUi

    def retranslateUi(self, calibration_finetune):
        calibration_finetune.setWindowTitle(QCoreApplication.translate("calibration_finetune", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("calibration_finetune", u"Fine-tune objective parameters", None))
        self.label_5.setText(QCoreApplication.translate("calibration_finetune", u"Rotation:", None))
        self.label_2.setText(QCoreApplication.translate("calibration_finetune", u"Scale-Y:", None))
        self.label.setText(QCoreApplication.translate("calibration_finetune", u"Scale-X:", None))
        self.label_4.setText(QCoreApplication.translate("calibration_finetune", u"Offset-Y:", None))
        self.label_3.setText(QCoreApplication.translate("calibration_finetune", u"Offset-X:", None))
        self.label_6.setText(QCoreApplication.translate("calibration_finetune", u"%", None))
        self.label_7.setText(QCoreApplication.translate("calibration_finetune", u"%", None))
        self.label_8.setText(QCoreApplication.translate("calibration_finetune", u"%", None))
        self.label_9.setText(QCoreApplication.translate("calibration_finetune", u"%", None))
        self.label_10.setText(QCoreApplication.translate("calibration_finetune", u"degree", None))
        self.btn_perform_finetune.setText(QCoreApplication.translate("calibration_finetune", u"Perform fine-tuning", None))
        self.btn_commit_finetune.setText(QCoreApplication.translate("calibration_finetune", u"Commit fine-tuning", None))
    # retranslateUi

