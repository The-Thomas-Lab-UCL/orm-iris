# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gridify_setup_finetuning.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget)

class Ui_gridify_setup_finetuning(object):
    def setupUi(self, gridify_setup_finetuning):
        if not gridify_setup_finetuning.objectName():
            gridify_setup_finetuning.setObjectName(u"gridify_setup_finetuning")
        gridify_setup_finetuning.resize(1200, 726)
        self.centralwidget = QWidget(gridify_setup_finetuning)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lyt_video = QHBoxLayout()
        self.lyt_video.setObjectName(u"lyt_video")

        self.verticalLayout_3.addLayout(self.lyt_video)


        self.verticalLayout.addWidget(self.groupBox)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.tree_roi = QTreeWidget(self.groupBox_2)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_roi.setHeaderItem(__qtreewidgetitem)
        self.tree_roi.setObjectName(u"tree_roi")

        self.verticalLayout_8.addWidget(self.tree_roi)

        self.label = QLabel(self.groupBox_2)
        self.label.setObjectName(u"label")

        self.verticalLayout_8.addWidget(self.label)


        self.horizontalLayout.addLayout(self.verticalLayout_8)

        self.groupBox_3 = QGroupBox(self.groupBox_2)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.combo_xy = QComboBox(self.groupBox_3)
        self.combo_xy.setObjectName(u"combo_xy")

        self.verticalLayout_5.addWidget(self.combo_xy)

        self.combo_z = QComboBox(self.groupBox_3)
        self.combo_z.setObjectName(u"combo_z")

        self.verticalLayout_5.addWidget(self.combo_z)

        self.btn_set_currcoor = QPushButton(self.groupBox_3)
        self.btn_set_currcoor.setObjectName(u"btn_set_currcoor")

        self.verticalLayout_5.addWidget(self.btn_set_currcoor)

        self.btn_nextROI = QPushButton(self.groupBox_3)
        self.btn_nextROI.setObjectName(u"btn_nextROI")

        self.verticalLayout_5.addWidget(self.btn_nextROI)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer)

        self.btn_cancel = QPushButton(self.groupBox_3)
        self.btn_cancel.setObjectName(u"btn_cancel")

        self.verticalLayout_5.addWidget(self.btn_cancel)

        self.btn_finish = QPushButton(self.groupBox_3)
        self.btn_finish.setObjectName(u"btn_finish")

        self.verticalLayout_5.addWidget(self.btn_finish)


        self.verticalLayout_6.addLayout(self.verticalLayout_5)


        self.horizontalLayout.addWidget(self.groupBox_3)


        self.verticalLayout_4.addLayout(self.horizontalLayout)


        self.verticalLayout.addWidget(self.groupBox_2)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        gridify_setup_finetuning.setCentralWidget(self.centralwidget)

        self.retranslateUi(gridify_setup_finetuning)

        QMetaObject.connectSlotsByName(gridify_setup_finetuning)
    # setupUi

    def retranslateUi(self, gridify_setup_finetuning):
        gridify_setup_finetuning.setWindowTitle(QCoreApplication.translate("gridify_setup_finetuning", u"Gridify - ROI coordinate finetuning", None))
        self.groupBox.setTitle(QCoreApplication.translate("gridify_setup_finetuning", u"Video feed", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("gridify_setup_finetuning", u"Fine-tune coordinates", None))
        self.label.setText(QCoreApplication.translate("gridify_setup_finetuning", u"Click on an ROI to modify it.\n"
"Double-click on an ROI to automatically go to its coordinate.", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("gridify_setup_finetuning", u"Parameters", None))
        self.btn_set_currcoor.setText(QCoreApplication.translate("gridify_setup_finetuning", u"Set current coordinate as reference", None))
        self.btn_nextROI.setText(QCoreApplication.translate("gridify_setup_finetuning", u"Go to the next ROI", None))
        self.btn_cancel.setText(QCoreApplication.translate("gridify_setup_finetuning", u"Cancel all modifications", None))
        self.btn_finish.setText(QCoreApplication.translate("gridify_setup_finetuning", u"Finish editing", None))
    # retranslateUi

