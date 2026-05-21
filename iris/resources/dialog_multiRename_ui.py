# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'dialog_multiRename.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_Dialog_MultiRename(object):
    def setupUi(self, Dialog_MultiRename):
        if not Dialog_MultiRename.objectName():
            Dialog_MultiRename.setObjectName(u"Dialog_MultiRename")
        Dialog_MultiRename.resize(627, 389)
        self.verticalLayout_2 = QVBoxLayout(Dialog_MultiRename)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_2 = QLabel(Dialog_MultiRename)
        self.label_2.setObjectName(u"label_2")

        self.verticalLayout.addWidget(self.label_2)

        self.ent_prefix = QLineEdit(Dialog_MultiRename)
        self.ent_prefix.setObjectName(u"ent_prefix")

        self.verticalLayout.addWidget(self.ent_prefix)

        self.line_2 = QFrame(Dialog_MultiRename)
        self.line_2.setObjectName(u"line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line_2)

        self.label_3 = QLabel(Dialog_MultiRename)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout.addWidget(self.label_3)

        self.ent_suffix = QLineEdit(Dialog_MultiRename)
        self.ent_suffix.setObjectName(u"ent_suffix")

        self.verticalLayout.addWidget(self.ent_suffix)

        self.line = QFrame(Dialog_MultiRename)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.label = QLabel(Dialog_MultiRename)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.label_5 = QLabel(Dialog_MultiRename)
        self.label_5.setObjectName(u"label_5")

        self.verticalLayout.addWidget(self.label_5)

        self.ent_replace_ori = QLineEdit(Dialog_MultiRename)
        self.ent_replace_ori.setObjectName(u"ent_replace_ori")

        self.verticalLayout.addWidget(self.ent_replace_ori)

        self.label_4 = QLabel(Dialog_MultiRename)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout.addWidget(self.label_4)

        self.ent_replace_with = QLineEdit(Dialog_MultiRename)
        self.ent_replace_with.setObjectName(u"ent_replace_with")

        self.verticalLayout.addWidget(self.ent_replace_with)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_7 = QLabel(Dialog_MultiRename)
        self.label_7.setObjectName(u"label_7")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)

        self.horizontalLayout.addWidget(self.label_7)

        self.lbl_example = QLabel(Dialog_MultiRename)
        self.lbl_example.setObjectName(u"lbl_example")

        self.horizontalLayout.addWidget(self.lbl_example)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.buttonBox = QDialogButtonBox(Dialog_MultiRename)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.verticalLayout_2.addWidget(self.buttonBox)


        self.retranslateUi(Dialog_MultiRename)
        self.buttonBox.accepted.connect(Dialog_MultiRename.accept)
        self.buttonBox.rejected.connect(Dialog_MultiRename.reject)

        QMetaObject.connectSlotsByName(Dialog_MultiRename)
    # setupUi

    def retranslateUi(self, Dialog_MultiRename):
        Dialog_MultiRename.setWindowTitle(QCoreApplication.translate("Dialog_MultiRename", u"Dialog", None))
        self.label_2.setText(QCoreApplication.translate("Dialog_MultiRename", u"Add prefix:", None))
        self.label_3.setText(QCoreApplication.translate("Dialog_MultiRename", u"Add sufix:", None))
        self.label.setText(QCoreApplication.translate("Dialog_MultiRename", u"Replace text:", None))
        self.label_5.setText(QCoreApplication.translate("Dialog_MultiRename", u"Replace:", None))
        self.label_4.setText(QCoreApplication.translate("Dialog_MultiRename", u"With:", None))
        self.label_7.setText(QCoreApplication.translate("Dialog_MultiRename", u"Example:", None))
        self.lbl_example.setText(QCoreApplication.translate("Dialog_MultiRename", u"N/A", None))
    # retranslateUi

