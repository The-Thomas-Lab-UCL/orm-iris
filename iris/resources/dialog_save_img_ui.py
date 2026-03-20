# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_save_img.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_dialog_save_imghub(object):
    def setupUi(self, dialog_save_imghub):
        if not dialog_save_imghub.objectName():
            dialog_save_imghub.setObjectName(u"dialog_save_imghub")
        dialog_save_imghub.resize(400, 300)
        self.verticalLayout_2 = QVBoxLayout(dialog_save_imghub)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(dialog_save_imghub)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label)

        self.spin_resolution = QDoubleSpinBox(dialog_save_imghub)
        self.spin_resolution.setObjectName(u"spin_resolution")
        self.spin_resolution.setMinimum(0.010000000000000)
        self.spin_resolution.setMaximum(100.000000000000000)
        self.spin_resolution.setValue(100.000000000000000)

        self.horizontalLayout.addWidget(self.spin_resolution)

        self.label_2 = QLabel(dialog_save_imghub)
        self.label_2.setObjectName(u"label_2")
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_2)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.chk_stitched = QCheckBox(dialog_save_imghub)
        self.chk_stitched.setObjectName(u"chk_stitched")
        self.chk_stitched.setChecked(True)

        self.verticalLayout.addWidget(self.chk_stitched)

        self.chk_scalebar = QCheckBox(dialog_save_imghub)
        self.chk_scalebar.setObjectName(u"chk_scalebar")
        self.chk_scalebar.setChecked(True)

        self.verticalLayout.addWidget(self.chk_scalebar)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.buttonBox = QDialogButtonBox(dialog_save_imghub)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.buttonBox)


        self.retranslateUi(dialog_save_imghub)
        self.buttonBox.accepted.connect(dialog_save_imghub.accept)
        self.buttonBox.rejected.connect(dialog_save_imghub.reject)

        QMetaObject.connectSlotsByName(dialog_save_imghub)
    # setupUi

    def retranslateUi(self, dialog_save_imghub):
        dialog_save_imghub.setWindowTitle(QCoreApplication.translate("dialog_save_imghub", u"Dialog", None))
        self.label.setText(QCoreApplication.translate("dialog_save_imghub", u"Resolution:", None))
        self.label_2.setText(QCoreApplication.translate("dialog_save_imghub", u"%", None))
        self.chk_stitched.setText(QCoreApplication.translate("dialog_save_imghub", u"Stitch all the images", None))
        self.chk_scalebar.setText(QCoreApplication.translate("dialog_save_imghub", u"Include a scalebar (only applicable for 'stitched')", None))
    # retranslateUi

