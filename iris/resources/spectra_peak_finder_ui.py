# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'spectra_peak_finder.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_spectra_peak_finder(object):
    def setupUi(self, spectra_peak_finder):
        if not spectra_peak_finder.objectName():
            spectra_peak_finder.setObjectName(u"spectra_peak_finder")
        spectra_peak_finder.resize(719, 639)
        self.verticalLayout_2 = QVBoxLayout(spectra_peak_finder)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.lyt_plot = QVBoxLayout()
        self.lyt_plot.setObjectName(u"lyt_plot")

        self.main_layout.addLayout(self.lyt_plot)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.btn_savePlotPng = QPushButton(spectra_peak_finder)
        self.btn_savePlotPng.setObjectName(u"btn_savePlotPng")

        self.horizontalLayout_4.addWidget(self.btn_savePlotPng)

        self.btn_savePlotTxt = QPushButton(spectra_peak_finder)
        self.btn_savePlotTxt.setObjectName(u"btn_savePlotTxt")

        self.horizontalLayout_4.addWidget(self.btn_savePlotTxt)


        self.main_layout.addLayout(self.horizontalLayout_4)

        self.lyt_limits = QGridLayout()
        self.lyt_limits.setObjectName(u"lyt_limits")
        self.btn_resetLimits = QPushButton(spectra_peak_finder)
        self.btn_resetLimits.setObjectName(u"btn_resetLimits")

        self.lyt_limits.addWidget(self.btn_resetLimits, 0, 4, 2, 1)

        self.chk_RamanShift = QCheckBox(spectra_peak_finder)
        self.chk_RamanShift.setObjectName(u"chk_RamanShift")
        self.chk_RamanShift.setChecked(True)

        self.lyt_limits.addWidget(self.chk_RamanShift, 2, 0, 1, 5)

        self.label_3 = QLabel(spectra_peak_finder)
        self.label_3.setObjectName(u"label_3")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_limits.addWidget(self.label_3, 0, 2, 1, 1)

        self.label_4 = QLabel(spectra_peak_finder)
        self.label_4.setObjectName(u"label_4")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy1)
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_limits.addWidget(self.label_4, 1, 2, 1, 1)

        self.label_2 = QLabel(spectra_peak_finder)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_limits.addWidget(self.label_2, 1, 0, 1, 1)

        self.label = QLabel(spectra_peak_finder)
        self.label.setObjectName(u"label")
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.lyt_limits.addWidget(self.label, 0, 0, 1, 1)

        self.ent_xmin = QLineEdit(spectra_peak_finder)
        self.ent_xmin.setObjectName(u"ent_xmin")

        self.lyt_limits.addWidget(self.ent_xmin, 0, 1, 1, 1)

        self.ent_xmax = QLineEdit(spectra_peak_finder)
        self.ent_xmax.setObjectName(u"ent_xmax")

        self.lyt_limits.addWidget(self.ent_xmax, 0, 3, 1, 1)

        self.ent_ymin = QLineEdit(spectra_peak_finder)
        self.ent_ymin.setObjectName(u"ent_ymin")

        self.lyt_limits.addWidget(self.ent_ymin, 1, 1, 1, 1)

        self.ent_ymax = QLineEdit(spectra_peak_finder)
        self.ent_ymax.setObjectName(u"ent_ymax")

        self.lyt_limits.addWidget(self.ent_ymax, 1, 3, 1, 1)


        self.main_layout.addLayout(self.lyt_limits)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.lyt_form_parmas = QFormLayout()
        self.lyt_form_parmas.setObjectName(u"lyt_form_parmas")

        self.horizontalLayout_2.addLayout(self.lyt_form_parmas)

        self.groupBox = QGroupBox(spectra_peak_finder)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_3 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tree_peaks = QTreeWidget(self.groupBox)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.tree_peaks.setHeaderItem(__qtreewidgetitem)
        self.tree_peaks.setObjectName(u"tree_peaks")

        self.verticalLayout.addWidget(self.tree_peaks)


        self.horizontalLayout_3.addLayout(self.verticalLayout)


        self.horizontalLayout_2.addWidget(self.groupBox)


        self.main_layout.addLayout(self.horizontalLayout_2)


        self.verticalLayout_2.addLayout(self.main_layout)

        QWidget.setTabOrder(self.btn_savePlotPng, self.btn_savePlotTxt)
        QWidget.setTabOrder(self.btn_savePlotTxt, self.ent_xmin)
        QWidget.setTabOrder(self.ent_xmin, self.ent_xmax)
        QWidget.setTabOrder(self.ent_xmax, self.ent_ymin)
        QWidget.setTabOrder(self.ent_ymin, self.ent_ymax)
        QWidget.setTabOrder(self.ent_ymax, self.btn_resetLimits)
        QWidget.setTabOrder(self.btn_resetLimits, self.chk_RamanShift)
        QWidget.setTabOrder(self.chk_RamanShift, self.tree_peaks)

        self.retranslateUi(spectra_peak_finder)

        QMetaObject.connectSlotsByName(spectra_peak_finder)
    # setupUi

    def retranslateUi(self, spectra_peak_finder):
        spectra_peak_finder.setWindowTitle(QCoreApplication.translate("spectra_peak_finder", u"Form", None))
        self.btn_savePlotPng.setText(QCoreApplication.translate("spectra_peak_finder", u"Save plot figure (.png)", None))
        self.btn_savePlotTxt.setText(QCoreApplication.translate("spectra_peak_finder", u"Save plot data (.txt)", None))
        self.btn_resetLimits.setText(QCoreApplication.translate("spectra_peak_finder", u"Reset plot limits", None))
        self.chk_RamanShift.setText(QCoreApplication.translate("spectra_peak_finder", u"Plot Raman-shift", None))
        self.label_3.setText(QCoreApplication.translate("spectra_peak_finder", u"X-max (mm):", None))
        self.label_4.setText(QCoreApplication.translate("spectra_peak_finder", u"Y-max (mm):", None))
        self.label_2.setText(QCoreApplication.translate("spectra_peak_finder", u"Y-min (mm):", None))
        self.label.setText(QCoreApplication.translate("spectra_peak_finder", u"X-min (mm):", None))
        self.groupBox.setTitle(QCoreApplication.translate("spectra_peak_finder", u"Peaks found", None))
    # retranslateUi

