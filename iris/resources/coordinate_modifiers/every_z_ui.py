# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'every_z.ui'
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
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QRadioButton, QSizePolicy,
    QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
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

        self.tabWidget = QTabWidget(every_z)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout = QVBoxLayout(self.tab)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lyt_modifications = QGridLayout()
        self.lyt_modifications.setObjectName(u"lyt_modifications")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btn_goToNext = QPushButton(self.tab)
        self.btn_goToNext.setObjectName(u"btn_goToNext")

        self.horizontalLayout_2.addWidget(self.btn_goToNext)

        self.btn_goToPrev = QPushButton(self.tab)
        self.btn_goToPrev.setObjectName(u"btn_goToPrev")

        self.horizontalLayout_2.addWidget(self.btn_goToPrev)


        self.lyt_modifications.addLayout(self.horizontalLayout_2, 5, 0, 1, 3)

        self.spin_newZUm = QDoubleSpinBox(self.tab)
        self.spin_newZUm.setObjectName(u"spin_newZUm")
        self.spin_newZUm.setMinimum(-1000000.000000000000000)
        self.spin_newZUm.setMaximum(1000000.000000000000000)

        self.lyt_modifications.addWidget(self.spin_newZUm, 2, 1, 1, 1)

        self.label = QLabel(self.tab)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_modifications.addWidget(self.label, 0, 0, 1, 1)

        self.groupBox_3 = QGroupBox(self.tab)
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

        self.label_3 = QLabel(self.tab)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_modifications.addWidget(self.label_3, 1, 0, 1, 1)

        self.btn_storeZ = QPushButton(self.tab)
        self.btn_storeZ.setObjectName(u"btn_storeZ")

        self.lyt_modifications.addWidget(self.btn_storeZ, 2, 2, 1, 1)

        self.lbl_coorLeft = QLabel(self.tab)
        self.lbl_coorLeft.setObjectName(u"lbl_coorLeft")

        self.lyt_modifications.addWidget(self.lbl_coorLeft, 0, 1, 1, 1)

        self.chk_autoNextCoor = QCheckBox(self.tab)
        self.chk_autoNextCoor.setObjectName(u"chk_autoNextCoor")
        self.chk_autoNextCoor.setChecked(True)

        self.lyt_modifications.addWidget(self.chk_autoNextCoor, 3, 0, 1, 3)

        self.lbl_prevZ = QLabel(self.tab)
        self.lbl_prevZ.setObjectName(u"lbl_prevZ")

        self.lyt_modifications.addWidget(self.lbl_prevZ, 1, 1, 1, 1)

        self.label_2 = QLabel(self.tab)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_modifications.addWidget(self.label_2, 2, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_cancel = QPushButton(self.tab)
        self.btn_cancel.setObjectName(u"btn_cancel")

        self.horizontalLayout.addWidget(self.btn_cancel)

        self.btn_finishAndSave = QPushButton(self.tab)
        self.btn_finishAndSave.setObjectName(u"btn_finishAndSave")

        self.horizontalLayout.addWidget(self.btn_finishAndSave)


        self.lyt_modifications.addLayout(self.horizontalLayout, 6, 0, 1, 3)


        self.verticalLayout.addLayout(self.lyt_modifications)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.verticalLayout_3 = QVBoxLayout(self.tab_2)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.btn_autofocusAll = QPushButton(self.tab_2)
        self.btn_autofocusAll.setObjectName(u"btn_autofocusAll")

        self.gridLayout.addWidget(self.btn_autofocusAll, 0, 2, 1, 1)

        self.btn_autofocusSel = QPushButton(self.tab_2)
        self.btn_autofocusSel.setObjectName(u"btn_autofocusSel")

        self.gridLayout.addWidget(self.btn_autofocusSel, 1, 2, 1, 1)

        self.spin_autofocusRange = QDoubleSpinBox(self.tab_2)
        self.spin_autofocusRange.setObjectName(u"spin_autofocusRange")
        self.spin_autofocusRange.setMaximum(1000000.000000000000000)
        self.spin_autofocusRange.setValue(100.000000000000000)

        self.gridLayout.addWidget(self.spin_autofocusRange, 0, 1, 2, 1)

        self.label_4 = QLabel(self.tab_2)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 0, 0, 2, 1)

        self.tree_report = QTreeWidget(self.tab_2)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_report.setHeaderItem(__qtreewidgetitem)
        self.tree_report.setObjectName(u"tree_report")

        self.gridLayout.addWidget(self.tree_report, 2, 0, 1, 3)

        self.btn_AF_next = QPushButton(self.tab_2)
        self.btn_AF_next.setObjectName(u"btn_AF_next")

        self.gridLayout.addWidget(self.btn_AF_next, 3, 0, 1, 1)

        self.btn_AF_insertCoor = QPushButton(self.tab_2)
        self.btn_AF_insertCoor.setObjectName(u"btn_AF_insertCoor")

        self.gridLayout.addWidget(self.btn_AF_insertCoor, 3, 1, 1, 1)

        self.btn_AF_finish = QPushButton(self.tab_2)
        self.btn_AF_finish.setObjectName(u"btn_AF_finish")

        self.gridLayout.addWidget(self.btn_AF_finish, 3, 2, 1, 1)


        self.verticalLayout_3.addLayout(self.gridLayout)

        self.tabWidget.addTab(self.tab_2, "")

        self.main_layout.addWidget(self.tabWidget)

        self.btn_showInstructions = QPushButton(every_z)
        self.btn_showInstructions.setObjectName(u"btn_showInstructions")

        self.main_layout.addWidget(self.btn_showInstructions)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.combo_mappingCoor, self.btn_start)
        QWidget.setTabOrder(self.btn_start, self.spin_newZUm)
        QWidget.setTabOrder(self.spin_newZUm, self.btn_storeZ)
        QWidget.setTabOrder(self.btn_storeZ, self.chk_autoNextCoor)
        QWidget.setTabOrder(self.chk_autoNextCoor, self.rad_lastFilled)
        QWidget.setTabOrder(self.rad_lastFilled, self.rad_originalZ)
        QWidget.setTabOrder(self.rad_originalZ, self.btn_goToNext)
        QWidget.setTabOrder(self.btn_goToNext, self.btn_goToPrev)
        QWidget.setTabOrder(self.btn_goToPrev, self.btn_cancel)
        QWidget.setTabOrder(self.btn_cancel, self.btn_finishAndSave)
        QWidget.setTabOrder(self.btn_finishAndSave, self.btn_showInstructions)

        self.retranslateUi(every_z)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(every_z)
    # setupUi

    def retranslateUi(self, every_z):
        every_z.setWindowTitle(QCoreApplication.translate("every_z", u"Form", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("every_z", u"Coordinate selection (to be modified)", None))
        self.btn_start.setText(QCoreApplication.translate("every_z", u"Confirm selection", None))
        self.btn_goToNext.setText(QCoreApplication.translate("every_z", u"Next coordinate", None))
        self.btn_goToPrev.setText(QCoreApplication.translate("every_z", u"Previous coordinate", None))
        self.label.setText(QCoreApplication.translate("every_z", u"Number of coordinates left to modify:", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("every_z", u"New Z-coordinate autofill", None))
        self.rad_lastFilled.setText(QCoreApplication.translate("every_z", u"Use the last filled coordinate", None))
        self.rad_originalZ.setText(QCoreApplication.translate("every_z", u"Use the original Z-coordinate", None))
        self.label_3.setText(QCoreApplication.translate("every_z", u"Original Z-coordinate (\u00b5m):", None))
        self.btn_storeZ.setText(QCoreApplication.translate("every_z", u"Insert current Z-coor", None))
        self.lbl_coorLeft.setText(QCoreApplication.translate("every_z", u"None", None))
        self.chk_autoNextCoor.setText(QCoreApplication.translate("every_z", u"Automove: Automatically go to the next coordinate after pressing \"Insert the current Z-coor\"", None))
        self.lbl_prevZ.setText(QCoreApplication.translate("every_z", u"None", None))
        self.label_2.setText(QCoreApplication.translate("every_z", u"New Z-coordinate (\u00b5m):", None))
        self.btn_cancel.setText(QCoreApplication.translate("every_z", u"Cancel modification", None))
        self.btn_finishAndSave.setText(QCoreApplication.translate("every_z", u"Finish and save modification", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("every_z", u"Manual coordinate modifications", None))
        self.btn_autofocusAll.setText(QCoreApplication.translate("every_z", u"Perform autofocus on all", None))
        self.btn_autofocusSel.setText(QCoreApplication.translate("every_z", u"Perform autofocus on selected", None))
        self.label_4.setText(QCoreApplication.translate("every_z", u"Autofocus range (\u00b5m):", None))
        self.btn_AF_next.setText(QCoreApplication.translate("every_z", u"Go to next", None))
        self.btn_AF_insertCoor.setText(QCoreApplication.translate("every_z", u"Insert current coordinate to the selected", None))
        self.btn_AF_finish.setText(QCoreApplication.translate("every_z", u"Finish and save", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("every_z", u"Autofocus coordinate modifications", None))
        self.btn_showInstructions.setText(QCoreApplication.translate("every_z", u"Show instructions", None))
    # retranslateUi

