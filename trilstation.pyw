from PyQt4.QtCore import *
from PyQt4.QtGui import *


if __name__ == '__main__':
    app = QApplication([])
    app.setWindowIcon(QIcon('./python_logo.png'))

    splash_pix = QPixmap('./python-powered.png')
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.setMask(splash_pix.mask())
    splash.show()
    app.processEvents()

    from mainwindow import MainWindow
    form = MainWindow()
    form.show()
    
    splash.finish(form)

    app.exec_()

