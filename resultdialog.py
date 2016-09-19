from __future__ import division
import sys
from PyQt4 import QtCore, QtGui
from guiqwt.plot import CurveWidget
from guiqwt.builder import make
import numpy as np
import excelreport
from utilities import round_sig


class ResultDialog(QtGui.QDialog):
    
    def __init__(self, dut, parent=None):
        super(ResultDialog, self).__init__(parent)

        self.resize(1000, 400)

        self.dut = dut

        # Plot
        ymax = max([float(self.dut['Band1TolPlus']), float(self.dut['Band2TolPlus']), float(self.dut['Band3TolPlus'])])
        curveWidget = CurveWidget(self, xlabel='freq [Hz]', ylabel='relative sensitivity [%]')
        curveWidget.plot.set_axis_limits('left', -2 * ymax, 2 * ymax)
        curveWidget.plot.set_axis_scale('bottom', 'log')
        curveWidget.plot.set_axis_limits('bottom', min(self.dut['freqs']), max(self.dut['freqs']))
        curveWidget.register_all_curve_tools()

        # Resultaat trace
        resultTrace = make.curve([], [], color='b')
        curveWidget.plot.add_item(resultTrace)
        resultTrace.set_data(self.dut['freqs'], 100 * (abs(self.dut['result'] / self.dut['refsens']) - 1))

        # Upper Limit trace
        upperLim = make.curve([], [], color='r')
        curveWidget.plot.add_item(upperLim)
        upperLim.set_data(self.dut['freqs'], self.dut['upper_lim'])

        # Lower Limit trace
        upperLim = make.curve([], [], color='r')
        curveWidget.plot.add_item(upperLim)
        upperLim.set_data(self.dut['freqs'], self.dut['lower_lim'])

        # Pass/Fail Label
        if self.dut['freqresppassfail'] == 'Pass':
            label = make.label('<span style="color:green">Pass</span>', "TR", (-10, 10), "TR")
        else:
            label = make.label('<span style="color:red">Fail</span>', "TR", (-10, 10), "TR")
        curveWidget.plot.add_item(label)

        # Buttons
        buttonLayout = QtGui.QHBoxLayout()
        reportButton = QtGui.QPushButton('Rapport')
        cancelButton = QtGui.QPushButton('Terug')
        cancelButton.setAutoDefault(False)
        buttonLayout.addStretch()
        buttonLayout.addWidget(cancelButton)
        buttonLayout.addWidget(reportButton)

        cancelButton.clicked.connect(self.reject)
        reportButton.clicked.connect(self.report)

        # Sens Label
        sensLayout = QtGui.QHBoxLayout()
        sensLabel = QtGui.QLabel()
        refsens_formatted, dummy = round_sig(self.dut['refsens'], 5)
        tolmin_formatted, dummy = round_sig(float(self.dut['Sens']) - float(self.dut['SensTolMin']), 4)
        tolplus_formatted, dummy = round_sig(float(self.dut['Sens']) + float(self.dut['SensTolPlus']), 4)
        sensLabel.setText('Ref. Sensitivity @ %.f Hz: %s %s' % (self.dut['SensFreq'], refsens_formatted, self.dut['sensunit']))
        sensLabel.setToolTip('Eis: %s - %s' % (tolmin_formatted, tolplus_formatted))

        refSensPassFailLabel = QtGui.QLabel()
        if self.dut['refsenspassfail'] == 'Pass':
            refSensPassFailLabel.setText('<span style="color:green">Pass</span>')
        else: refSensPassFailLabel.setText('<span style="color:red">Fail</span>')
        refSensPassFailLabel.setToolTip('Eis: %s - %s' % (tolmin_formatted, tolplus_formatted))
        sensLayout.addWidget(sensLabel)
        sensLayout.addSpacing(10)
        sensLayout.addWidget(refSensPassFailLabel)
        sensLayout.addStretch()

        # Layout
        layout = QtGui.QHBoxLayout()
        layout1 = QtGui.QVBoxLayout()
        layout1.addWidget(curveWidget)
        layout1.addLayout(sensLayout)
        line = QtGui.QFrame(self)
        line.setFrameShape(QtGui.QFrame.HLine)
        line.setFrameShadow(QtGui.QFrame.Sunken)
        layout1.addWidget(line)
        layout1.addLayout(buttonLayout)

        layout.addLayout(layout1)
        self.setLayout(layout)
        self.setWindowTitle('Resultaat')

    def report(self):
        kalnr, result = QtGui.QInputDialog.getText(None, "Kalibratienummer", "Wat is het kalibratienummer?")
        self.dut['kalnummer'] = kalnr
        excelreport.ExcelReport(self.dut)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    dut = {}
    fstep = 5
    imaxlim1, imaxlim2, imaxlim3 = (7000//fstep), (9100//fstep), (10000//fstep)
    upperlim = fstep * np.zeros(imaxlim3,dtype=np.float64)
    upperlim[0:imaxlim1] = 5
    upperlim[imaxlim1:imaxlim2] = 7.5
    upperlim[imaxlim2:imaxlim3] = 10
    dut['freqs'] = fstep * (1+np.arange(imaxlim3, dtype=np.float64))
    dut['result'] = 0.01 * np.random.sample(imaxlim3) + 1.02
    dut['upper_lim'] = upperlim
    lowerlim = np.zeros(imaxlim3,dtype=np.float64)
    lowerlim[0:imaxlim3] = -5
    dut['lower_lim'] = lowerlim
    dut['refsens'] = 1.0294
    dut['fmax'] = 10000
    dut['Y-Max'] = 10
    dut['sensunit'] = 'pC/(m/s\u00B2)'
    dut['X-As'] = 'Log'
    dut['SensFreq'] = 160
    dut['Sens'] = '1'
    dut['SensTolPlus'] = '0.029'
    dut['SensTolMin'] = '0.029'
    dut['Band1TolPlus'] = 5
    dut['Band2TolPlus'] = 7.5
    dut['Band3TolPlus'] = 10

    dlg = ResultDialog(dut)
    dlg.show()
    
    sys.exit(app.exec_())

