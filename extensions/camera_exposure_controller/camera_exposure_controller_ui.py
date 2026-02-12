# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'camera_exposure_controller.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QFrame,
    QGridLayout, QLabel, QMainWindow, QPushButton,
    QSizePolicy, QSlider, QSpacerItem, QVBoxLayout,
    QWidget)

class Ui_camera_exposure_controller(object):
    def setupUi(self, camera_exposure_controller):
        if not camera_exposure_controller.objectName():
            camera_exposure_controller.setObjectName(u"camera_exposure_controller")
        camera_exposure_controller.resize(149, 445)
        self.centralwidget = QWidget(camera_exposure_controller)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.main_layout = QGridLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label, 0, 1, 1, 1)

        self.spin_curr_ms = QDoubleSpinBox(self.centralwidget)
        self.spin_curr_ms.setObjectName(u"spin_curr_ms")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.spin_curr_ms.sizePolicy().hasHeightForWidth())
        self.spin_curr_ms.setSizePolicy(sizePolicy1)
        self.spin_curr_ms.setDecimals(2)
        self.spin_curr_ms.setMaximum(100000.000000000000000)
        self.spin_curr_ms.setValue(0.500000000000000)

        self.main_layout.addWidget(self.spin_curr_ms, 3, 1, 1, 1)

        self.spin_min_ms = QDoubleSpinBox(self.centralwidget)
        self.spin_min_ms.setObjectName(u"spin_min_ms")
        sizePolicy1.setHeightForWidth(self.spin_min_ms.sizePolicy().hasHeightForWidth())
        self.spin_min_ms.setSizePolicy(sizePolicy1)
        self.spin_min_ms.setDecimals(2)
        self.spin_min_ms.setMaximum(100000.000000000000000)
        self.spin_min_ms.setValue(0.010000000000000)

        self.main_layout.addWidget(self.spin_min_ms, 5, 1, 1, 1)

        self.label_5 = QLabel(self.centralwidget)
        self.label_5.setObjectName(u"label_5")

        self.main_layout.addWidget(self.label_5, 12, 1, 1, 1)

        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")

        self.main_layout.addWidget(self.label_4, 9, 1, 1, 1)

        self.slider_relative = QSlider(self.centralwidget)
        self.slider_relative.setObjectName(u"slider_relative")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.slider_relative.sizePolicy().hasHeightForWidth())
        self.slider_relative.setSizePolicy(sizePolicy2)
        font = QFont()
        font.setKerning(True)
        self.slider_relative.setFont(font)
        self.slider_relative.setMaximum(100)
        self.slider_relative.setOrientation(Qt.Orientation.Vertical)
        self.slider_relative.setInvertedAppearance(False)
        self.slider_relative.setTickPosition(QSlider.TickPosition.TicksAbove)
        self.slider_relative.setTickInterval(10)

        self.main_layout.addWidget(self.slider_relative, 0, 0, 15, 1)

        self.btn_instruction = QPushButton(self.centralwidget)
        self.btn_instruction.setObjectName(u"btn_instruction")

        self.main_layout.addWidget(self.btn_instruction, 16, 0, 1, 2)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label_2, 2, 1, 1, 1)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer_2, 8, 1, 1, 1)

        self.spin_preset2_ms = QDoubleSpinBox(self.centralwidget)
        self.spin_preset2_ms.setObjectName(u"spin_preset2_ms")
        self.spin_preset2_ms.setMaximum(100000.000000000000000)
        self.spin_preset2_ms.setValue(500.000000000000000)

        self.main_layout.addWidget(self.spin_preset2_ms, 13, 1, 1, 1)

        self.btn_preset2 = QPushButton(self.centralwidget)
        self.btn_preset2.setObjectName(u"btn_preset2")

        self.main_layout.addWidget(self.btn_preset2, 14, 1, 1, 1)

        self.line = QFrame(self.centralwidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.main_layout.addWidget(self.line, 7, 1, 1, 1)

        self.spin_max_ms = QDoubleSpinBox(self.centralwidget)
        self.spin_max_ms.setObjectName(u"spin_max_ms")
        sizePolicy1.setHeightForWidth(self.spin_max_ms.sizePolicy().hasHeightForWidth())
        self.spin_max_ms.setSizePolicy(sizePolicy1)
        self.spin_max_ms.setDecimals(1)
        self.spin_max_ms.setMaximum(100000.000000000000000)
        self.spin_max_ms.setValue(2000.000000000000000)

        self.main_layout.addWidget(self.spin_max_ms, 1, 1, 1, 1)

        self.spin_preset1_ms = QDoubleSpinBox(self.centralwidget)
        self.spin_preset1_ms.setObjectName(u"spin_preset1_ms")
        self.spin_preset1_ms.setMaximum(100000.000000000000000)
        self.spin_preset1_ms.setValue(50.000000000000000)

        self.main_layout.addWidget(self.spin_preset1_ms, 10, 1, 1, 1)

        self.btn_preset1 = QPushButton(self.centralwidget)
        self.btn_preset1.setObjectName(u"btn_preset1")

        self.main_layout.addWidget(self.btn_preset1, 11, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer, 6, 1, 1, 1)

        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)
        self.label_3.setAlignment(Qt.AlignmentFlag.AlignBottom|Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addWidget(self.label_3, 4, 1, 1, 1)

        self.chk_stayOnTop = QCheckBox(self.centralwidget)
        self.chk_stayOnTop.setObjectName(u"chk_stayOnTop")
        self.chk_stayOnTop.setChecked(True)

        self.main_layout.addWidget(self.chk_stayOnTop, 15, 0, 1, 2)


        self.verticalLayout.addLayout(self.main_layout)

        camera_exposure_controller.setCentralWidget(self.centralwidget)

        self.retranslateUi(camera_exposure_controller)

        QMetaObject.connectSlotsByName(camera_exposure_controller)
    # setupUi

    def retranslateUi(self, camera_exposure_controller):
        camera_exposure_controller.setWindowTitle(QCoreApplication.translate("camera_exposure_controller", u"MainWindow", None))
        self.label.setText(QCoreApplication.translate("camera_exposure_controller", u"Max [ms]:", None))
        self.label_5.setText(QCoreApplication.translate("camera_exposure_controller", u"Preset 2 [ms]:", None))
        self.label_4.setText(QCoreApplication.translate("camera_exposure_controller", u"Preset 1 [ms]:", None))
        self.btn_instruction.setText(QCoreApplication.translate("camera_exposure_controller", u"Instruction", None))
        self.label_2.setText(QCoreApplication.translate("camera_exposure_controller", u"Current [ms]:", None))
        self.btn_preset2.setText(QCoreApplication.translate("camera_exposure_controller", u"Set 2", None))
        self.btn_preset1.setText(QCoreApplication.translate("camera_exposure_controller", u"Set 1", None))
        self.label_3.setText(QCoreApplication.translate("camera_exposure_controller", u"Min [ms]:", None))
        self.chk_stayOnTop.setText(QCoreApplication.translate("camera_exposure_controller", u"Stay on top", None))
    # retranslateUi

