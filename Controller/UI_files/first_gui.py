# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'first_gui.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(454, 420)
        self.gridLayoutWidget = QtGui.QWidget(Form)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(160, 110, 160, 80))
        self.gridLayoutWidget.setObjectName(_fromUtf8("gridLayoutWidget"))
        self.gridLayout = QtGui.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.Mai_btn = QtGui.QPushButton(self.gridLayoutWidget)
        self.Mai_btn.setObjectName(_fromUtf8("Mai_btn"))
        self.gridLayout.addWidget(self.Mai_btn, 0, 0, 1, 1)
        self.horizontalLayoutWidget = QtGui.QWidget(Form)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(130, 220, 231, 80))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.Load_btn = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.Load_btn.setObjectName(_fromUtf8("Load_btn"))
        self.horizontalLayout.addWidget(self.Load_btn)
        self.Clear_btn = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.Clear_btn.setObjectName(_fromUtf8("Clear_btn"))
        self.horizontalLayout.addWidget(self.Clear_btn)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "High Q ", None))
        self.Mai_btn.setText(_translate("Form", " [data_avg,data_part,data]", None))
        self.Load_btn.setText(_translate("Form", "Load", None))
        self.Clear_btn.setText(_translate("Form", "clear", None))

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'first_gui.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(454, 420)
        self.gridLayoutWidget = QtGui.QWidget(Form)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(160, 110, 160, 80))
        self.gridLayoutWidget.setObjectName(_fromUtf8("gridLayoutWidget"))
        self.gridLayout = QtGui.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.Mai_btn = QtGui.QPushButton(self.gridLayoutWidget)
        self.Mai_btn.setObjectName(_fromUtf8("Mai_btn"))
        self.gridLayout.addWidget(self.Mai_btn, 0, 0, 1, 1)
        self.horizontalLayoutWidget = QtGui.QWidget(Form)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(130, 220, 231, 80))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.Load_btn = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.Load_btn.setObjectName(_fromUtf8("Load_btn"))
        self.horizontalLayout.addWidget(self.Load_btn)
        self.Clear_btn = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.Clear_btn.setObjectName(_fromUtf8("Clear_btn"))
        self.horizontalLayout.addWidget(self.Clear_btn)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "High Q ", None))
        self.Mai_btn.setText(_translate("Form", " [data_avg,data_part,data]", None))
        self.Load_btn.setText(_translate("Form", "Load", None))
        self.Clear_btn.setText(_translate("Form", "clear", None))

