from PyQt4.QtCore import *
from PyQt4.QtGui import *
import sys

app = QApplication(sys.argv)

rslt = QMessageBox.critical(None, 'Shake It!', 'Coherence Fail! Klik op OK, controleer montage/aansluitingen en begin opnieuw.',
                                         QMessageBox.Ok|QMessageBox.Ignore, defaultButton=QMessageBox.Ok)
print (rslt)

app.exec_()