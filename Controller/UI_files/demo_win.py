# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'demo_win.ui'
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

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(256, 249)
        Dialog.setMinimumSize(QtCore.QSize(256, 249))
        Dialog.setMaximumSize(QtCore.QSize(256, 249))
        Dialog.setMouseTracking(False)
        Dialog.setAcceptDrops(False)
        self.formLayoutWidget = QtGui.QWidget(Dialog)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 70, 211, 103))
        self.formLayoutWidget.setObjectName(_fromUtf8("formLayoutWidget"))
        self.formLayout = QtGui.QFormLayout(self.formLayoutWidget)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_1 = QtGui.QLabel(self.formLayoutWidget)
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_1)
        self.doubleSpinBox_for_pulse_amp = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_for_pulse_amp.setObjectName(_fromUtf8("doubleSpinBox_for_pulse_amp"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_for_pulse_amp)
        self.label_2 = QtGui.QLabel(self.formLayoutWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.doubleSpinBox_Dead_time = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_Dead_time.setObjectName(_fromUtf8("doubleSpinBox_Dead_time"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_Dead_time)
        self.label_3 = QtGui.QLabel(self.formLayoutWidget)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.doubleSpinBox_Num_repet = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_Num_repet.setObjectName(_fromUtf8("doubleSpinBox_Num_repet"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_Num_repet)
        self.pushButton = QtGui.QPushButton(self.formLayoutWidget)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.pushButton)
        self.label_4 = QtGui.QLabel(Dialog)
        self.label_4.setGeometry(QtCore.QRect(20, 25, 161, 31))
        self.label_4.setObjectName(_fromUtf8("label_4"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Demo_window", None))
        self.label_1.setText(_translate("Dialog", "Pulse_amps", None))
        self.label_2.setText(_translate("Dialog", "Dead_time", None))
        self.label_3.setText(_translate("Dialog", "Num_repet", None))
        self.pushButton.setText(_translate("Dialog", "Ok", None))
        self.label_4.setText(_translate("Dialog", "Enter value ", None))

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'demo_win.ui'
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

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(256, 249)
        Dialog.setMinimumSize(QtCore.QSize(256, 249))
        Dialog.setMaximumSize(QtCore.QSize(256, 249))
        Dialog.setMouseTracking(False)
        Dialog.setAcceptDrops(False)
        self.formLayoutWidget = QtGui.QWidget(Dialog)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 70, 211, 103))
        self.formLayoutWidget.setObjectName(_fromUtf8("formLayoutWidget"))
        self.formLayout = QtGui.QFormLayout(self.formLayoutWidget)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_1 = QtGui.QLabel(self.formLayoutWidget)
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_1)
        self.doubleSpinBox_for_pulse_amp = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_for_pulse_amp.setDecimals(0)
        self.doubleSpinBox_for_pulse_amp.setObjectName(_fromUtf8("doubleSpinBox_for_pulse_amp"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_for_pulse_amp)
        self.label_2 = QtGui.QLabel(self.formLayoutWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.doubleSpinBox_Dead_time = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_Dead_time.setDecimals(0)
        self.doubleSpinBox_Dead_time.setObjectName(_fromUtf8("doubleSpinBox_Dead_time"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_Dead_time)
        self.label_3 = QtGui.QLabel(self.formLayoutWidget)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.doubleSpinBox_Num_repet = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_Num_repet.setDecimals(0)
        self.doubleSpinBox_Num_repet.setObjectName(_fromUtf8("doubleSpinBox_Num_repet"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_Num_repet)
        self.pushButton = QtGui.QPushButton(self.formLayoutWidget)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.pushButton)
        self.label_4 = QtGui.QLabel(Dialog)
        self.label_4.setGeometry(QtCore.QRect(20, 25, 161, 31))
        self.label_4.setObjectName(_fromUtf8("label_4"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Demo_window", None))
        self.label_1.setText(_translate("Dialog", "Pulse_amps", None))
        self.label_2.setText(_translate("Dialog", "Dead_time", None))
        self.label_3.setText(_translate("Dialog", "Num_repet", None))
        self.pushButton.setText(_translate("Dialog", "Ok", None))
        self.label_4.setText(_translate("Dialog", "Enter value ", None))

# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'demo_win.ui'
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

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(256, 249)
        Dialog.setMinimumSize(QtCore.QSize(256, 249))
        Dialog.setMaximumSize(QtCore.QSize(256, 249))
        Dialog.setMouseTracking(False)
        Dialog.setAcceptDrops(False)
        self.formLayoutWidget = QtGui.QWidget(Dialog)
        self.formLayoutWidget.setGeometry(QtCore.QRect(10, 70, 211, 103))
        self.formLayoutWidget.setObjectName(_fromUtf8("formLayoutWidget"))
        self.formLayout = QtGui.QFormLayout(self.formLayoutWidget)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_1 = QtGui.QLabel(self.formLayoutWidget)
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_1)
        self.doubleSpinBox_for_pulse_amp = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_for_pulse_amp.setDecimals(0)
        self.doubleSpinBox_for_pulse_amp.setObjectName(_fromUtf8("doubleSpinBox_for_pulse_amp"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_for_pulse_amp)
        self.label_2 = QtGui.QLabel(self.formLayoutWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.label_3 = QtGui.QLabel(self.formLayoutWidget)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.doubleSpinBox_Num_repet = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_Num_repet.setDecimals(0)
        self.doubleSpinBox_Num_repet.setObjectName(_fromUtf8("doubleSpinBox_Num_repet"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_Num_repet)
        self.pushButton = QtGui.QPushButton(self.formLayoutWidget)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.pushButton)
        self.doubleSpinBox_Dead_time = QtGui.QDoubleSpinBox(self.formLayoutWidget)
        self.doubleSpinBox_Dead_time.setDecimals(0)
        self.doubleSpinBox_Dead_time.setMaximum(1000000.0)
        self.doubleSpinBox_Dead_time.setObjectName(_fromUtf8("doubleSpinBox_Dead_time"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.doubleSpinBox_Dead_time)
        self.label_4 = QtGui.QLabel(Dialog)
        self.label_4.setGeometry(QtCore.QRect(20, 25, 161, 31))
        self.label_4.setObjectName(_fromUtf8("label_4"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Demo_window", None))
        self.label_1.setText(_translate("Dialog", "Pulse_amps", None))
        self.label_2.setText(_translate("Dialog", "Dead_time", None))
        self.label_3.setText(_translate("Dialog", "Num_repet", None))
        self.pushButton.setText(_translate("Dialog", "Ok", None))
        self.label_4.setText(_translate("Dialog", "Enter value ", None))

