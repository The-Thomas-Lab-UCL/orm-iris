# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'objective_calibration_controls.ui'
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
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSpacerItem, QVBoxLayout, QWidget)

class Ui_calibration_controls(object):
    def setupUi(self, calibration_controls):
        if not calibration_controls.objectName():
            calibration_controls.setObjectName(u"calibration_controls")
        calibration_controls.resize(650, 546)
        self.horizontalLayout_3 = QHBoxLayout(calibration_controls)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox_2 = QGroupBox(calibration_controls)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout = QVBoxLayout(self.groupBox_2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.btn_calibrate = QPushButton(self.groupBox_2)
        self.btn_calibrate.setObjectName(u"btn_calibrate")

        self.verticalLayout_3.addWidget(self.btn_calibrate)

        self.btn_savecal = QPushButton(self.groupBox_2)
        self.btn_savecal.setObjectName(u"btn_savecal")

        self.verticalLayout_3.addWidget(self.btn_savecal)

        self.btn_loadcal = QPushButton(self.groupBox_2)
        self.btn_loadcal.setObjectName(u"btn_loadcal")

        self.verticalLayout_3.addWidget(self.btn_loadcal)

        self.lbl_calfile = QLabel(self.groupBox_2)
        self.lbl_calfile.setObjectName(u"lbl_calfile")

        self.verticalLayout_3.addWidget(self.lbl_calfile)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.MinimumExpanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)


        self.verticalLayout.addLayout(self.verticalLayout_3)


        self.main_layout.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(calibration_controls)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.vertical_layout = QVBoxLayout()
        self.vertical_layout.setObjectName(u"vertical_layout")
        self.lyt_finetune_spins = QGridLayout()
        self.lyt_finetune_spins.setObjectName(u"lyt_finetune_spins")
        self.spin_scalex = QDoubleSpinBox(self.groupBox)
        self.spin_scalex.setObjectName(u"spin_scalex")
        self.spin_scalex.setEnabled(False)

        self.lyt_finetune_spins.addWidget(self.spin_scalex, 0, 1, 1, 1)

        self.label_9 = QLabel(self.groupBox)
        self.label_9.setObjectName(u"label_9")

        self.lyt_finetune_spins.addWidget(self.label_9, 3, 2, 1, 1)

        self.spin_offsety = QDoubleSpinBox(self.groupBox)
        self.spin_offsety.setObjectName(u"spin_offsety")
        self.spin_offsety.setEnabled(False)

        self.lyt_finetune_spins.addWidget(self.spin_offsety, 3, 1, 1, 1)

        self.label_6 = QLabel(self.groupBox)
        self.label_6.setObjectName(u"label_6")

        self.lyt_finetune_spins.addWidget(self.label_6, 0, 2, 1, 1)

        self.label_10 = QLabel(self.groupBox)
        self.label_10.setObjectName(u"label_10")

        self.lyt_finetune_spins.addWidget(self.label_10, 4, 2, 1, 1)

        self.spin_rotdeg = QDoubleSpinBox(self.groupBox)
        self.spin_rotdeg.setObjectName(u"spin_rotdeg")
        self.spin_rotdeg.setEnabled(False)

        self.lyt_finetune_spins.addWidget(self.spin_rotdeg, 4, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_finetune_spins.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_finetune_spins.addWidget(self.label, 0, 0, 1, 1)

        self.label_5 = QLabel(self.groupBox)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_finetune_spins.addWidget(self.label_5, 4, 0, 1, 1)

        self.label_4 = QLabel(self.groupBox)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_finetune_spins.addWidget(self.label_4, 3, 0, 1, 1)

        self.spin_scaley = QDoubleSpinBox(self.groupBox)
        self.spin_scaley.setObjectName(u"spin_scaley")
        self.spin_scaley.setEnabled(False)

        self.lyt_finetune_spins.addWidget(self.spin_scaley, 1, 1, 1, 1)

        self.spin_offsetx = QDoubleSpinBox(self.groupBox)
        self.spin_offsetx.setObjectName(u"spin_offsetx")
        self.spin_offsetx.setEnabled(False)

        self.lyt_finetune_spins.addWidget(self.spin_offsetx, 2, 1, 1, 1)

        self.label_8 = QLabel(self.groupBox)
        self.label_8.setObjectName(u"label_8")

        self.lyt_finetune_spins.addWidget(self.label_8, 2, 2, 1, 1)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_finetune_spins.addWidget(self.label_3, 2, 0, 1, 1)

        self.label_7 = QLabel(self.groupBox)
        self.label_7.setObjectName(u"label_7")

        self.lyt_finetune_spins.addWidget(self.label_7, 1, 2, 1, 1)


        self.vertical_layout.addLayout(self.lyt_finetune_spins)

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


        self.retranslateUi(calibration_controls)

        QMetaObject.connectSlotsByName(calibration_controls)
    # setupUi

    def retranslateUi(self, calibration_controls):
        calibration_controls.setWindowTitle(QCoreApplication.translate("calibration_controls", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("calibration_controls", u"Calibration control panel", None))
        self.btn_calibrate.setText(QCoreApplication.translate("calibration_controls", u"Perform objective calibration", None))
        self.btn_savecal.setText(QCoreApplication.translate("calibration_controls", u"Save objective calibration", None))
        self.btn_loadcal.setText(QCoreApplication.translate("calibration_controls", u"Load objective calibration", None))
        self.lbl_calfile.setText(QCoreApplication.translate("calibration_controls", u"Calibration file: N/A", None))
        self.groupBox.setTitle(QCoreApplication.translate("calibration_controls", u"Fine-tune objective parameters", None))
        self.label_9.setText(QCoreApplication.translate("calibration_controls", u"%", None))
        self.label_6.setText(QCoreApplication.translate("calibration_controls", u"%", None))
        self.label_10.setText(QCoreApplication.translate("calibration_controls", u"degree", None))
        self.label_2.setText(QCoreApplication.translate("calibration_controls", u"Scale-Y:", None))
        self.label.setText(QCoreApplication.translate("calibration_controls", u"Scale-X:", None))
        self.label_5.setText(QCoreApplication.translate("calibration_controls", u"Rotation:", None))
        self.label_4.setText(QCoreApplication.translate("calibration_controls", u"Offset-Y:", None))
        self.label_8.setText(QCoreApplication.translate("calibration_controls", u"%", None))
        self.label_3.setText(QCoreApplication.translate("calibration_controls", u"Offset-X:", None))
        self.label_7.setText(QCoreApplication.translate("calibration_controls", u"%", None))
        self.btn_perform_finetune.setText(QCoreApplication.translate("calibration_controls", u"Perform fine-tuning", None))
        self.btn_commit_finetune.setText(QCoreApplication.translate("calibration_controls", u"Commit fine-tuning", None))
    # retranslateUi

