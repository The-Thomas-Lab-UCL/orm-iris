# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gridify_setup_naming.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_gridify_setup_naming(object):
    def setupUi(self, gridify_setup_naming):
        if not gridify_setup_naming.objectName():
            gridify_setup_naming.setObjectName(u"gridify_setup_naming")
        gridify_setup_naming.resize(1089, 639)
        self.centralwidget = QWidget(gridify_setup_naming)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_5 = QVBoxLayout(self.groupBox)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.lyt_row = QFormLayout()
        self.lyt_row.setObjectName(u"lyt_row")

        self.verticalLayout_5.addLayout(self.lyt_row)


        self.horizontalLayout_2.addWidget(self.groupBox)

        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.lyt_col = QFormLayout()
        self.lyt_col.setObjectName(u"lyt_col")

        self.verticalLayout_6.addLayout(self.lyt_col)


        self.horizontalLayout_2.addWidget(self.groupBox_3)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.rad_rowcol = QRadioButton(self.groupBox_2)
        self.rad_rowcol.setObjectName(u"rad_rowcol")
        self.rad_rowcol.setChecked(True)

        self.verticalLayout_3.addWidget(self.rad_rowcol)

        self.rad_colrow = QRadioButton(self.groupBox_2)
        self.rad_colrow.setObjectName(u"rad_colrow")

        self.verticalLayout_3.addWidget(self.rad_colrow)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label = QLabel(self.groupBox_2)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.horizontalLayout_5.addWidget(self.label)

        self.ent_separator = QLineEdit(self.groupBox_2)
        self.ent_separator.setObjectName(u"ent_separator")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.ent_separator.sizePolicy().hasHeightForWidth())
        self.ent_separator.setSizePolicy(sizePolicy1)

        self.horizontalLayout_5.addWidget(self.ent_separator)

        self.btn_example = QPushButton(self.groupBox_2)
        self.btn_example.setObjectName(u"btn_example")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.btn_example.sizePolicy().hasHeightForWidth())
        self.btn_example.setSizePolicy(sizePolicy2)

        self.horizontalLayout_5.addWidget(self.btn_example)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)


        self.verticalLayout_4.addLayout(self.verticalLayout_3)


        self.verticalLayout.addWidget(self.groupBox_2)

        self.btn_finalise = QPushButton(self.centralwidget)
        self.btn_finalise.setObjectName(u"btn_finalise")

        self.verticalLayout.addWidget(self.btn_finalise)

        self.btn_cancel = QPushButton(self.centralwidget)
        self.btn_cancel.setObjectName(u"btn_cancel")

        self.verticalLayout.addWidget(self.btn_cancel)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.horizontalLayout_2.addLayout(self.verticalLayout)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        gridify_setup_naming.setCentralWidget(self.centralwidget)

        self.retranslateUi(gridify_setup_naming)

        QMetaObject.connectSlotsByName(gridify_setup_naming)
    # setupUi

    def retranslateUi(self, gridify_setup_naming):
        gridify_setup_naming.setWindowTitle(QCoreApplication.translate("gridify_setup_naming", u"Gridify - ROI name setup", None))
        self.groupBox.setTitle(QCoreApplication.translate("gridify_setup_naming", u"Row name setup (top to bottom)", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("gridify_setup_naming", u"Column name setup (left to right)", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("gridify_setup_naming", u"Naming scheme setup", None))
        self.rad_rowcol.setText(QCoreApplication.translate("gridify_setup_naming", u"Row, Column", None))
        self.rad_colrow.setText(QCoreApplication.translate("gridify_setup_naming", u"Column, Row", None))
        self.label.setText(QCoreApplication.translate("gridify_setup_naming", u"Separator:", None))
        self.ent_separator.setText(QCoreApplication.translate("gridify_setup_naming", u"_", None))
        self.btn_example.setText(QCoreApplication.translate("gridify_setup_naming", u"Show example", None))
        self.btn_finalise.setText(QCoreApplication.translate("gridify_setup_naming", u"Finalise the names and proceed to grid fine-tuning", None))
        self.btn_cancel.setText(QCoreApplication.translate("gridify_setup_naming", u"Cancel", None))
    # retranslateUi

