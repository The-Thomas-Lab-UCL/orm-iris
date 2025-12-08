# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'rect_image.ui'
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
    QPushButton, QSizePolicy, QSpacerItem, QSpinBox,
    QVBoxLayout, QWidget)

class Ui_Rect_Image(object):
    def setupUi(self, Rect_Image):
        if not Rect_Image.objectName():
            Rect_Image.setObjectName(u"Rect_Image")
        Rect_Image.resize(685, 653)
        self.verticalLayout_2 = QVBoxLayout(Rect_Image)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.main_layout = QVBoxLayout()
        self.main_layout.setObjectName(u"main_layout")
        self.groupBox = QGroupBox(Rect_Image)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gridLayout = QGridLayout()
        self.gridLayout.setObjectName(u"gridLayout")
        self.combo_image = QComboBox(self.groupBox)
        self.combo_image.setObjectName(u"combo_image")

        self.gridLayout.addWidget(self.combo_image, 1, 0, 1, 1)

        self.btn_defineROI = QPushButton(self.groupBox)
        self.btn_defineROI.setObjectName(u"btn_defineROI")

        self.gridLayout.addWidget(self.btn_defineROI, 1, 1, 1, 1)

        self.lyt_canvas = QVBoxLayout()
        self.lyt_canvas.setObjectName(u"lyt_canvas")

        self.gridLayout.addLayout(self.lyt_canvas, 0, 0, 1, 2)

        self.chk_lres = QCheckBox(self.groupBox)
        self.chk_lres.setObjectName(u"chk_lres")
        self.chk_lres.setChecked(True)

        self.gridLayout.addWidget(self.chk_lres, 2, 0, 1, 2)


        self.verticalLayout_3.addLayout(self.gridLayout)


        self.main_layout.addWidget(self.groupBox)

        self.label_2 = QLabel(Rect_Image)
        self.label_2.setObjectName(u"label_2")

        self.main_layout.addWidget(self.label_2)

        self.lbl_selectedCoors = QLabel(Rect_Image)
        self.lbl_selectedCoors.setObjectName(u"lbl_selectedCoors")

        self.main_layout.addWidget(self.lbl_selectedCoors)

        self.label = QLabel(Rect_Image)
        self.label.setObjectName(u"label")

        self.main_layout.addWidget(self.label)

        self.gridLayout_2 = QGridLayout()
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.label_11 = QLabel(Rect_Image)
        self.label_11.setObjectName(u"label_11")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_11.sizePolicy().hasHeightForWidth())
        self.label_11.setSizePolicy(sizePolicy)
        self.label_11.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_11, 6, 0, 1, 1)

        self.label_9 = QLabel(Rect_Image)
        self.label_9.setObjectName(u"label_9")
        sizePolicy.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_9, 5, 0, 1, 1)

        self.spin_resXum = QDoubleSpinBox(Rect_Image)
        self.spin_resXum.setObjectName(u"spin_resXum")
        self.spin_resXum.setMinimum(-1000000.000000000000000)
        self.spin_resXum.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_resXum, 6, 1, 1, 1)

        self.label_5 = QLabel(Rect_Image)
        self.label_5.setObjectName(u"label_5")
        sizePolicy.setHeightForWidth(self.label_5.sizePolicy().hasHeightForWidth())
        self.label_5.setSizePolicy(sizePolicy)
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_5, 3, 0, 1, 1)

        self.spin_resXPt = QSpinBox(Rect_Image)
        self.spin_resXPt.setObjectName(u"spin_resXPt")
        self.spin_resXPt.setMinimum(1)
        self.spin_resXPt.setMaximum(1000000)

        self.gridLayout_2.addWidget(self.spin_resXPt, 5, 1, 1, 1)

        self.spin_z = QDoubleSpinBox(Rect_Image)
        self.spin_z.setObjectName(u"spin_z")
        self.spin_z.setMinimum(-1000000.000000000000000)
        self.spin_z.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_z, 3, 1, 1, 1)

        self.label_10 = QLabel(Rect_Image)
        self.label_10.setObjectName(u"label_10")
        sizePolicy.setHeightForWidth(self.label_10.sizePolicy().hasHeightForWidth())
        self.label_10.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_10, 5, 2, 1, 1)

        self.label_12 = QLabel(Rect_Image)
        self.label_12.setObjectName(u"label_12")
        sizePolicy.setHeightForWidth(self.label_12.sizePolicy().hasHeightForWidth())
        self.label_12.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_12, 6, 2, 1, 1)

        self.label_7 = QLabel(Rect_Image)
        self.label_7.setObjectName(u"label_7")
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_7, 3, 2, 1, 1)

        self.label_13 = QLabel(Rect_Image)
        self.label_13.setObjectName(u"label_13")
        sizePolicy.setHeightForWidth(self.label_13.sizePolicy().hasHeightForWidth())
        self.label_13.setSizePolicy(sizePolicy)
        self.label_13.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_13, 5, 3, 1, 1)

        self.label_8 = QLabel(Rect_Image)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_2.addWidget(self.label_8, 4, 0, 1, 6)

        self.spin_resYPt = QSpinBox(Rect_Image)
        self.spin_resYPt.setObjectName(u"spin_resYPt")
        self.spin_resYPt.setMinimum(1)
        self.spin_resYPt.setMaximum(1000000)

        self.gridLayout_2.addWidget(self.spin_resYPt, 5, 4, 1, 1)

        self.label_14 = QLabel(Rect_Image)
        self.label_14.setObjectName(u"label_14")
        sizePolicy.setHeightForWidth(self.label_14.sizePolicy().hasHeightForWidth())
        self.label_14.setSizePolicy(sizePolicy)
        self.label_14.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_14, 6, 3, 1, 1)

        self.spin_resYum = QDoubleSpinBox(Rect_Image)
        self.spin_resYum.setObjectName(u"spin_resYum")
        self.spin_resYum.setMinimum(-1000000.000000000000000)
        self.spin_resYum.setMaximum(1000000.000000000000000)

        self.gridLayout_2.addWidget(self.spin_resYum, 6, 4, 1, 1)

        self.label_16 = QLabel(Rect_Image)
        self.label_16.setObjectName(u"label_16")
        sizePolicy.setHeightForWidth(self.label_16.sizePolicy().hasHeightForWidth())
        self.label_16.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_16, 6, 5, 1, 1)

        self.label_15 = QLabel(Rect_Image)
        self.label_15.setObjectName(u"label_15")
        sizePolicy.setHeightForWidth(self.label_15.sizePolicy().hasHeightForWidth())
        self.label_15.setSizePolicy(sizePolicy)

        self.gridLayout_2.addWidget(self.label_15, 5, 5, 1, 1)

        self.btn_storeZ = QPushButton(Rect_Image)
        self.btn_storeZ.setObjectName(u"btn_storeZ")

        self.gridLayout_2.addWidget(self.btn_storeZ, 3, 3, 1, 3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_4 = QLabel(Rect_Image)
        self.label_4.setObjectName(u"label_4")
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_4)

        self.lbl_scanEdges = QLabel(Rect_Image)
        self.lbl_scanEdges.setObjectName(u"lbl_scanEdges")

        self.horizontalLayout.addWidget(self.lbl_scanEdges)


        self.gridLayout_2.addLayout(self.horizontalLayout, 2, 0, 1, 6)


        self.main_layout.addLayout(self.gridLayout_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer)


        self.verticalLayout_2.addLayout(self.main_layout)


        self.retranslateUi(Rect_Image)

        QMetaObject.connectSlotsByName(Rect_Image)
    # setupUi

    def retranslateUi(self, Rect_Image):
        Rect_Image.setWindowTitle(QCoreApplication.translate("Rect_Image", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("Rect_Image", u"Image-based coordinate selection", None))
        self.btn_defineROI.setText(QCoreApplication.translate("Rect_Image", u"Define ROI", None))
        self.chk_lres.setText(QCoreApplication.translate("Rect_Image", u"Use low-resolution image (faster processing)", None))
        self.label_2.setText(QCoreApplication.translate("Rect_Image", u"Selected coordinates (\u00b5m):", None))
        self.lbl_selectedCoors.setText(QCoreApplication.translate("Rect_Image", u"None", None))
        self.label.setText(QCoreApplication.translate("Rect_Image", u"Instructions:\n"
"1. Select an image to display\n"
"2.1. Left-click on the image to include points in the ROI\n"
"2.2. Right-click on the image to reset the selected points.\n"
"3. Click the 'Define ROI' button to finalise the setup.", None))
        self.label_11.setText(QCoreApplication.translate("Rect_Image", u"X:", None))
        self.label_9.setText(QCoreApplication.translate("Rect_Image", u"X:", None))
        self.label_5.setText(QCoreApplication.translate("Rect_Image", u"Z:", None))
        self.label_10.setText(QCoreApplication.translate("Rect_Image", u"points", None))
        self.label_12.setText(QCoreApplication.translate("Rect_Image", u"\u00b5m", None))
        self.label_7.setText(QCoreApplication.translate("Rect_Image", u"\u00b5m", None))
        self.label_13.setText(QCoreApplication.translate("Rect_Image", u"Y:", None))
        self.label_8.setText(QCoreApplication.translate("Rect_Image", u"Imaging resolution:", None))
        self.label_14.setText(QCoreApplication.translate("Rect_Image", u"Y:", None))
        self.label_16.setText(QCoreApplication.translate("Rect_Image", u"\u00b5m", None))
        self.label_15.setText(QCoreApplication.translate("Rect_Image", u"points", None))
        self.btn_storeZ.setText(QCoreApplication.translate("Rect_Image", u"Set current Z-coordinate", None))
        self.label_4.setText(QCoreApplication.translate("Rect_Image", u"Scan edges (\u00b5m):", None))
        self.lbl_scanEdges.setText(QCoreApplication.translate("Rect_Image", u"None", None))
    # retranslateUi

