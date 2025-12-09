# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'every_z.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_every_z(object):
    def setupUi(self, every_z):
        if not every_z.objectName():
            every_z.setObjectName(u"every_z")
        every_z.resize(677, 636)
        self.verticalLayout_2 = QVBoxLayout(every_z)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox_2 = QGroupBox(every_z)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_5 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.lyt_selector = QVBoxLayout()
        self.lyt_selector.setObjectName(u"lyt_selector")
        self.combo_mappingCoor = QComboBox(self.groupBox_2)
        self.combo_mappingCoor.setObjectName(u"combo_mappingCoor")

        self.lyt_selector.addWidget(self.combo_mappingCoor)

        self.btn_start = QPushButton(self.groupBox_2)
        self.btn_start.setObjectName(u"btn_start")

        self.lyt_selector.addWidget(self.btn_start)


        self.verticalLayout_5.addLayout(self.lyt_selector)


        self.main_layout.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(every_z)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.lyt_modifications = QGridLayout()
        self.lyt_modifications.setObjectName(u"lyt_modifications")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_goToNext = QPushButton(self.groupBox)
        self.btn_goToNext.setObjectName(u"btn_goToNext")

        self.horizontalLayout_2.addWidget(self.btn_goToNext)

        self.btn_goToPrev = QPushButton(self.groupBox)
        self.btn_goToPrev.setObjectName(u"btn_goToPrev")

        self.horizontalLayout_2.addWidget(self.btn_goToPrev)


        self.lyt_modifications.addLayout(self.horizontalLayout_2, 5, 0, 1, 3)

        self.lbl_prevZ = QLabel(self.groupBox)
        self.lbl_prevZ.setObjectName(u"lbl_prevZ")

        self.lyt_modifications.addWidget(self.lbl_prevZ, 1, 1, 1, 1)

        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_modifications.addWidget(self.label_2, 2, 0, 1, 1)

        self.lbl_coorLeft = QLabel(self.groupBox)
        self.lbl_coorLeft.setObjectName(u"lbl_coorLeft")

        self.lyt_modifications.addWidget(self.lbl_coorLeft, 0, 1, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_cancel = QPushButton(self.groupBox)
        self.btn_cancel.setObjectName(u"btn_cancel")

        self.horizontalLayout.addWidget(self.btn_cancel)

        self.btn_finishAndSave = QPushButton(self.groupBox)
        self.btn_finishAndSave.setObjectName(u"btn_finishAndSave")

        self.horizontalLayout.addWidget(self.btn_finishAndSave)


        self.lyt_modifications.addLayout(self.horizontalLayout, 6, 0, 1, 3)

        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_modifications.addWidget(self.label, 0, 0, 1, 1)

        self.chk_autoNextCoor = QCheckBox(self.groupBox)
        self.chk_autoNextCoor.setObjectName(u"chk_autoNextCoor")
        self.chk_autoNextCoor.setChecked(True)

        self.lyt_modifications.addWidget(self.chk_autoNextCoor, 3, 0, 1, 3)

        self.btn_storeZ = QPushButton(self.groupBox)
        self.btn_storeZ.setObjectName(u"btn_storeZ")

        self.lyt_modifications.addWidget(self.btn_storeZ, 2, 2, 1, 1)

        self.spin_newZUm = QDoubleSpinBox(self.groupBox)
        self.spin_newZUm.setObjectName(u"spin_newZUm")
        self.spin_newZUm.setMinimum(-1000000.000000000000000)
        self.spin_newZUm.setMaximum(1000000.000000000000000)

        self.lyt_modifications.addWidget(self.spin_newZUm, 2, 1, 1, 1)

        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_modifications.addWidget(self.label_3, 1, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.groupBox)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.rad_lastFilled = QRadioButton(self.groupBox_3)
        self.rad_lastFilled.setObjectName(u"rad_lastFilled")
        self.rad_lastFilled.setChecked(True)

        self.horizontalLayout_3.addWidget(self.rad_lastFilled)

        self.rad_originalZ = QRadioButton(self.groupBox_3)
        self.rad_originalZ.setObjectName(u"rad_originalZ")

        self.horizontalLayout_3.addWidget(self.rad_originalZ)


        self.horizontalLayout_4.addLayout(self.horizontalLayout_3)


        self.lyt_modifications.addWidget(self.groupBox_3, 4, 0, 1, 3)


        self.verticalLayout_4.addLayout(self.lyt_modifications)


        self.main_layout.addWidget(self.groupBox)

        self.btn_showInstructions = QPushButton(every_z)
        self.btn_showInstructions.setObjectName(u"btn_showInstructions")

        self.main_layout.addWidget(self.btn_showInstructions)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(every_z)

        QMetaObject.connectSlotsByName(every_z)
    # setupUi

    def retranslateUi(self, every_z):
        every_z.setWindowTitle(QCoreApplication.translate("every_z", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("every_z", u"Coordinate selection (to be modified)", None))
        self.btn_start.setText(QCoreApplication.translate("every_z", u"Start modification", None))
        self.groupBox.setTitle(QCoreApplication.translate("every_z", u"Coordinate modifications", None))
        self.btn_goToNext.setText(QCoreApplication.translate("every_z", u"Next coordinate", None))
        self.btn_goToPrev.setText(QCoreApplication.translate("every_z", u"Previous coordinate", None))
        self.lbl_prevZ.setText(QCoreApplication.translate("every_z", u"None", None))
        self.label_2.setText(QCoreApplication.translate("every_z", u"New Z-coordinate (\u00b5m):", None))
        self.lbl_coorLeft.setText(QCoreApplication.translate("every_z", u"None", None))
        self.btn_cancel.setText(QCoreApplication.translate("every_z", u"Cancel modification", None))
        self.btn_finishAndSave.setText(QCoreApplication.translate("every_z", u"Finish and save modification", None))
        self.label.setText(QCoreApplication.translate("every_z", u"Number of coordinates left to modify:", None))
        self.chk_autoNextCoor.setText(QCoreApplication.translate("every_z", u"Automove: Automatically go to the next coordinate after pressing \"Insert the current Z-coor\"", None))
        self.btn_storeZ.setText(QCoreApplication.translate("every_z", u"Insert current Z-coor", None))
        self.label_3.setText(QCoreApplication.translate("every_z", u"Original Z-coordinate (\u00b5m):", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("every_z", u"New Z-coordinate autofill", None))
        self.rad_lastFilled.setText(QCoreApplication.translate("every_z", u"Use the last filled coordinate", None))
        self.rad_originalZ.setText(QCoreApplication.translate("every_z", u"Use the original Z-coordinate", None))
        self.btn_showInstructions.setText(QCoreApplication.translate("every_z", u"Show instructions", None))
    # retranslateUi

