'''
Created on Oct 6, 2016

@author: fortheking
'''

import sys
from PyQt4 import QtGui
from UI_files.first_gui import Ui_Form
from UI_files.demo_win import Ui_Dialog
import single_pulse as sp
import numpy as np

#from Dialog import Dialog

class Dialog(QtGui.QMainWindow):

    
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui =Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.pushButton.clicked.connect(self.acceptOKBtnClicked)
        #self.ab = self.ui.label_1.getText("Pulse_amps")
        self.ac = self.ui.doubleSpinBox_for_pulse_amp.valueChanged.connect(self.handler)
        self.aq = self.ui.doubleSpinBox_Dead_time.valueChanged.connect(self.handler)
        self.aw = self.ui.doubleSpinBox_Num_repet.valueChanged.connect(self.handler)
    
    def handler(self):
        self.a1 = self.ui.doubleSpinBox_for_pulse_amp.value()
        self.a2 = self.ui.doubleSpinBox_Dead_time.value()
        self.a3 = self.ui.doubleSpinBox_Num_repet.value()
        return self.a1, self.a2,self.a3
    
    def save_value(self):
        self.pre = self.handler()
        self.pulse_amp = self.pre[0]
        self.dead_time = self.pre[1]
        self.num_repet = self.pre[2]

    def acceptOKBtnClicked(self):
        self.ac = self.ui.doubleSpinBox_for_pulse_amp.valueChanged.connect(self.handler)
        self.close() 
        
    
class Main(QtGui.QMainWindow):

    
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui =Ui_Form()
        self.ui.setupUi(self)
        
        self.ui.Mai_btn.clicked.connect(self.btnSayhello_clicked)
        self.ui.Load_btn.clicked.connect(self.btnSayload_clicked)
        self.ui.Clear_btn.clicked.connect(self.btnSayclear_clicked)
        
        self.ui.Mai_btn.clicked.connect(self.actionMain_triggered)
        self.pop = Dialog()
   
    def actionMain_triggered(self):
        self.pop.show()
        
    def btnSayhello_clicked(self):
        print ("Demo window")
        
    def btnSayload_clicked(self):
        self.pop.save_value()
        print ("Load")
        self.test = sp.run_expt(pulse_amps=np.array([int(self.pop.pulse_amp)]),pulse_times=np.array([100]),dead_time=int(self.pop.dead_time),rep_time_sec=0.01,num_avgs=1,num_repetitions=int(self.pop.num_repet))
        #pulse_amps=np.array([int(self.pop.pulse_amp)])
        #print pulse_amps
        #dead_time=int(self.pop.dead_time)
        #print dead_time
        #num_repetitions = int(self.pop.num_repet)
        #print num_repetitions
        #pulse_times=np.array([100]),dead_time=%d,rep_time_sec=0.01,num_avgs=128,num_repetitions=%d (self.pop.pulse_amp,self.pop.dead_time,self.pop.num_repet)
        #print testing
        #self.test = sp.run_expt() 
        #print self.test
        print "Value  =",self.pop.pre
        #print "Value 2 =",self.pop.dead_time
        #print "Value 3=",self.pop.num_repet
        
        
    def btnSayclear_clicked(self):
        self.pop = Dialog()
        print self.pop.handler()
        print ("clear!!!")

        
        
    

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())