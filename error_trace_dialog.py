# Wordt niet meer gebruikt

from __future__ import division
import sys
from PyQt4 import QtGui
from guiqwt.plot import CurveWidget
from guiqwt.builder import make


class ErrorTraceDialog(QtGui.QDialog):
    
    def __init__(self, text, freqs, trace, max_freq, ul=None, ll=None, ignore_button=False, parent=None):
        super(ErrorTraceDialog, self).__init__(parent)

        # Plot
        self.curveWidget = CurveWidget(self, xlabel='freq [Hz]')
        self.curveWidget.plot.set_axis_scale('bottom', 'log')

        self.curveWidget.plot.set_axis_limits('bottom', 1, max_freq)
        self.curveWidget.register_all_curve_tools()

        # Resultaat trace
        resultTrace = make.curve([], [], color='b')
        self.curveWidget.plot.add_item(resultTrace)
        resultTrace.set_data(freqs, trace)

        if ul is not None:
            # Upper limit
            ulTrace = make.curve([], [], color='r')
            self.curveWidget.plot.add_item(ulTrace)
            ulTrace.set_data(freqs, ul)

        if ll is not None:
            # Lower limit
            llTrace = make.curve([], [], color='r')
            self.curveWidget.plot.add_item(llTrace)
            llTrace.set_data(freqs, ll)

        # Error icon
        style = QtGui.QApplication.style()
        icon = style.standardIcon(QtGui.QStyle.SP_MessageBoxCritical)
        errorLabel = QtGui.QLabel()
        errorLabel.setPixmap(icon.pixmap(32))
        errorLabel.setMinimumWidth(40)
        errorLabel.setStyleSheet('border-bottom-style:none;')

        # Label
        label = QtGui.QLabel('%s! <p>Klik op Ok, controleer montage/aansluitingen en begin opnieuw.' % text)
        label.setStyleSheet('border-bottom-style:none;')        
        
        # Buttons
        buttonLayout = QtGui.QHBoxLayout()
        cancelButton = QtGui.QPushButton('Ok')
        ignoreButton = QtGui.QPushButton('Negeer')
        traceButton = QtGui.QPushButton('Trace...')
        traceButton.setCheckable(True)
        buttonLayout.addSpacing(10)
        buttonLayout.addWidget(traceButton)
        buttonLayout.addStretch()
        buttonLayout.addWidget(ignoreButton)
        buttonLayout.addWidget(cancelButton)
        buttonLayout.addSpacing(10)

        if not ignore_button:
            ignoreButton.setHidden(True)

        cancelButton.clicked.connect(self.reject)
        ignoreButton.clicked.connect(self.accept)

        # Frame voor de trace
        traceFrame = QtGui.QFrame()
        traceFrame.setFrameStyle(QtGui.QFrame.NoFrame)
        frameLayout = QtGui.QHBoxLayout()
        frameLayout.addWidget(self.curveWidget)
        traceFrame.setLayout(frameLayout)
        traceFrame.hide()

        # Frame voor de boodschap
        messageFrame = QtGui.QFrame()
        messageFrame.setStyleSheet('background-color: white;border-bottom-style:solid;border-bottom-width:1px;border-bottom-color: rgb(190, 190, 190);')
        messageFrameLayout = QtGui.QHBoxLayout()
        messageFrameLayout.addWidget(errorLabel)
        messageFrameLayout.addWidget(label)
        messageFrame.setLayout(messageFrameLayout)

        # Layout
        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 10)
        layout1 = QtGui.QVBoxLayout()
        messageFrameLayout.addStretch()
        layout1.addWidget(messageFrame)
        layout1.addSpacing(10)
        layout1.addLayout(buttonLayout)
        layout1.addWidget(traceFrame)

        layout.addLayout(layout1)
        self.setLayout(layout)
        self.setWindowTitle('Shake It')

        layout.setSizeConstraint(QtGui.QLayout.SetFixedSize)

        cancelButton.setFocus()

        traceButton.toggled.connect(traceFrame.setVisible)


if __name__ == '__main__':
    import numpy as np
    app = QtGui.QApplication(sys.argv)

    freqs = np.arange(0, 100)
    trace = np.sin(freqs*2*np.pi/50)
    ul = np.full_like(trace, 1)
    ll = np.full_like(trace, -1)

    rslt = ErrorTraceDialog('Coherence Fail', freqs, trace, ul, ll, ignore_button=True).exec_()

    sys.exit(app.exec_())