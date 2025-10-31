# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'raman.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

class Ui_Raman(object):
    def setupUi(self, Raman):
        if not Raman.objectName():
            Raman.setObjectName(u"Raman")
        Raman.resize(719, 757)
        self.groupBox_plt = QGroupBox(Raman)
        self.groupBox_plt.setObjectName(u"groupBox_plt")
        self.groupBox_plt.setGeometry(QRect(50, 20, 424, 321))
        self.gridLayout = QGridLayout(self.groupBox_plt)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_3 = QLabel(self.groupBox_plt)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)

        self.label = QLabel(self.groupBox_plt)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label, 2, 0, 1, 1)

        self.ent_plt_xmin = QLineEdit(self.groupBox_plt)
        self.ent_plt_xmin.setObjectName(u"ent_plt_xmin")

        self.gridLayout.addWidget(self.ent_plt_xmin, 2, 1, 1, 1)

        self.ent_plt_xmax = QLineEdit(self.groupBox_plt)
        self.ent_plt_xmax.setObjectName(u"ent_plt_xmax")

        self.gridLayout.addWidget(self.ent_plt_xmax, 2, 3, 1, 1)

        self.label_2 = QLabel(self.groupBox_plt)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_2, 2, 2, 1, 1)

        self.ent_plt_ymin = QLineEdit(self.groupBox_plt)
        self.ent_plt_ymin.setObjectName(u"ent_plt_ymin")

        self.gridLayout.addWidget(self.ent_plt_ymin, 3, 1, 1, 1)

        self.label_4 = QLabel(self.groupBox_plt)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_4, 3, 2, 1, 1)

        self.ent_plt_ymax = QLineEdit(self.groupBox_plt)
        self.ent_plt_ymax.setObjectName(u"ent_plt_ymax")

        self.gridLayout.addWidget(self.ent_plt_ymax, 3, 3, 1, 1)

        self.btn_reset_plot_limits = QPushButton(self.groupBox_plt)
        self.btn_reset_plot_limits.setObjectName(u"btn_reset_plot_limits")

        self.gridLayout.addWidget(self.btn_reset_plot_limits, 2, 4, 2, 1)

        self.lyt_plot = QVBoxLayout()
        self.lyt_plot.setObjectName(u"lyt_plot")

        self.gridLayout.addLayout(self.lyt_plot, 0, 0, 1, 5)

        self.chk_ramanshift = QCheckBox(self.groupBox_plt)
        self.chk_ramanshift.setObjectName(u"chk_ramanshift")

        self.gridLayout.addWidget(self.chk_ramanshift, 1, 0, 1, 5)

        self.groupBox_params = QGroupBox(Raman)
        self.groupBox_params.setObjectName(u"groupBox_params")
        self.groupBox_params.setGeometry(QRect(50, 350, 421, 271))
        self.gridLayout_2 = QGridLayout(self.groupBox_params)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_9 = QLabel(self.groupBox_params)
        self.label_9.setObjectName(u"label_9")
        font = QFont()
        font.setBold(False)
        font.setItalic(True)
        self.label_9.setFont(font)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_9, 2, 0, 1, 1)

        self.lbl_laserpower_mW = QLabel(self.groupBox_params)
        self.lbl_laserpower_mW.setObjectName(u"lbl_laserpower_mW")

        self.gridLayout_2.addWidget(self.lbl_laserpower_mW, 6, 1, 1, 1)

        self.lbl_laserwavelength_nm = QLabel(self.groupBox_params)
        self.lbl_laserwavelength_nm.setObjectName(u"lbl_laserwavelength_nm")

        self.gridLayout_2.addWidget(self.lbl_laserwavelength_nm, 5, 1, 1, 1)

        self.lbl_accum = QLabel(self.groupBox_params)
        self.lbl_accum.setObjectName(u"lbl_accum")

        self.gridLayout_2.addWidget(self.lbl_accum, 4, 1, 1, 1)

        self.label_12 = QLabel(self.groupBox_params)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_12, 5, 0, 1, 1)

        self.lbl_inttime_ms = QLabel(self.groupBox_params)
        self.lbl_inttime_ms.setObjectName(u"lbl_inttime_ms")

        self.gridLayout_2.addWidget(self.lbl_inttime_ms, 3, 1, 1, 1)

        self.btn_savetomanager = QPushButton(self.groupBox_params)
        self.btn_savetomanager.setObjectName(u"btn_savetomanager")

        self.gridLayout_2.addWidget(self.btn_savetomanager, 7, 0, 1, 3)

        self.label_15 = QLabel(self.groupBox_params)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setFont(font)

        self.gridLayout_2.addWidget(self.label_15, 2, 2, 1, 1)

        self.label_14 = QLabel(self.groupBox_params)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_14, 6, 0, 1, 1)

        self.label_10 = QLabel(self.groupBox_params)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setFont(font)

        self.gridLayout_2.addWidget(self.label_10, 2, 1, 1, 1)

        self.ent_laserwavelength_nm = QLineEdit(self.groupBox_params)
        self.ent_laserwavelength_nm.setObjectName(u"ent_laserwavelength_nm")

        self.gridLayout_2.addWidget(self.ent_laserwavelength_nm, 5, 2, 1, 1)

        self.label_7 = QLabel(self.groupBox_params)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_7, 4, 0, 1, 1)

        self.label_5 = QLabel(self.groupBox_params)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_5, 3, 0, 1, 1)

        self.ent_laserpower_mW = QLineEdit(self.groupBox_params)
        self.ent_laserpower_mW.setObjectName(u"ent_laserpower_mW")

        self.gridLayout_2.addWidget(self.ent_laserpower_mW, 6, 2, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btn_snglmea = QPushButton(self.groupBox_params)
        self.btn_snglmea.setObjectName(u"btn_snglmea")

        self.horizontalLayout.addWidget(self.btn_snglmea)

        self.btn_contmea = QPushButton(self.groupBox_params)
        self.btn_contmea.setObjectName(u"btn_contmea")

        self.horizontalLayout.addWidget(self.btn_contmea)


        self.gridLayout_2.addLayout(self.horizontalLayout, 0, 0, 1, 3)

        self.spin_inttime_ms = QSpinBox(self.groupBox_params)
        self.spin_inttime_ms.setObjectName(u"spin_inttime_ms")
        self.spin_inttime_ms.setMinimum(1)
        self.spin_inttime_ms.setMaximum(1000000)

        self.gridLayout_2.addWidget(self.spin_inttime_ms, 3, 2, 1, 1)

        self.spin_accum = QSpinBox(self.groupBox_params)
        self.spin_accum.setObjectName(u"spin_accum")
        self.spin_accum.setMinimum(1)
        self.spin_accum.setMaximum(1000)

        self.gridLayout_2.addWidget(self.spin_accum, 4, 2, 1, 1)


        self.retranslateUi(Raman)

        QMetaObject.connectSlotsByName(Raman)
    # setupUi

    def retranslateUi(self, Raman):
        Raman.setWindowTitle(QCoreApplication.translate("Raman", u"Form", None))
        self.groupBox_plt.setTitle(QCoreApplication.translate("Raman", u"Spectra readout", None))
        self.label_3.setText(QCoreApplication.translate("Raman", u"y-min:", None))
        self.label.setText(QCoreApplication.translate("Raman", u"x-min:", None))
        self.label_2.setText(QCoreApplication.translate("Raman", u"x-max:", None))
        self.label_4.setText(QCoreApplication.translate("Raman", u"y-max:", None))
        self.btn_reset_plot_limits.setText(QCoreApplication.translate("Raman", u"Reset\n"
"plot limits", None))
        self.chk_ramanshift.setText(QCoreApplication.translate("Raman", u"Plot Raman wavenumber", None))
        self.groupBox_params.setTitle(QCoreApplication.translate("Raman", u"Acquisition parameters", None))
        self.label_9.setText(QCoreApplication.translate("Raman", u"Parameter", None))
        self.lbl_laserpower_mW.setText(QCoreApplication.translate("Raman", u"NA", None))
        self.lbl_laserwavelength_nm.setText(QCoreApplication.translate("Raman", u"NA", None))
        self.lbl_accum.setText(QCoreApplication.translate("Raman", u"NA", None))
        self.label_12.setText(QCoreApplication.translate("Raman", u"Laser wavelength [nm]:", None))
        self.lbl_inttime_ms.setText(QCoreApplication.translate("Raman", u"NA", None))
        self.btn_savetomanager.setText(QCoreApplication.translate("Raman", u"Save 'single measurement' to data manager", None))
        self.label_15.setText(QCoreApplication.translate("Raman", u"New value\n"
"(Enter to confirm)", None))
        self.label_14.setText(QCoreApplication.translate("Raman", u"Laser power [mW]:", None))
        self.label_10.setText(QCoreApplication.translate("Raman", u"Device value", None))
        self.label_7.setText(QCoreApplication.translate("Raman", u"Accumulation:", None))
        self.label_5.setText(QCoreApplication.translate("Raman", u"Integration time [ms]:", None))
        self.btn_snglmea.setText(QCoreApplication.translate("Raman", u"Single measurement", None))
        self.btn_contmea.setText(QCoreApplication.translate("Raman", u"Continuous measurement", None))
    # retranslateUi

