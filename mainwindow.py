import logging
import platform
import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *

try:
    import config
except Exception as err:
    QMessageBox.critical(None, 'Error', 'Fout tijdens inlezen configuratie!\n\n%s\n\nProgramma wordt afgesloten.' % err)
    exit(-1)

import response
import dutdialog
from measurement import Measurement
import resultdialog
import standards
import teds


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)

        # DUT data
        self.dut = {'Type': None}

        # Meting
        self.meas = None

        # Settings
        self.settings = QSettings(config.SETTINGS_FILE, QSettings.IniFormat)

        # Logging
        logging.basicConfig(filename='tril.log', level=logging.DEBUG,
                            format='%(levelname)s: %(asctime)s %(message)s',
                            datefmt='%d-%m-%Y %H:%M:%S',
                            filemode='w')
        logger = logging.getLogger('tril')
        logger.info('Programma gestart')

        # Mainwindow settings
        self.setWindowTitle('Shake It!')
        self.restoreGeometry(self.settings.value('MainGeometry'))

        # File menu
        self.fileMenu = self.menuBar().addMenu('&Bestand')
        eraseRefSpecAction = self.fileMenu.addAction('Wis Ref Spectra', self.del_ref_trace)
        # eraseRefSpecAction.setShortcut('Ctrl+W')
        self.fileMenu.addSeparator()
        self.fileMenu.addAction('Standaarden', self.show_standards_dialog)
        self.fileMenu.addSeparator()
        self.tedsMenuAction = self.fileMenu.addAction('TEDS', self.show_teds_dialog)
        self.fileMenu.addSeparator()
        stopAction = self.fileMenu.addAction('Stop', self.close)
        stopAction.setShortcut('Ctrl+Q')

        # DUT menu
        self.dutMenu = self.menuBar().addMenu('&Kalibreren')
        selectDutAction = self.dutMenu.addAction('Selecteer &DUT', self.select_dut)
        selectDutAction.setShortcut('Ctrl+D')

        # Help menu
        self.helpMenu = self.menuBar().addMenu('&Help')
        self.helpMenu.addAction('Over', self.about_box)

        # Statusbar
        statusbar = self.statusBar()
        self.status = QLabel('Klaar...')
        statusbar.addPermanentWidget(self.status, 1)

        # ResultTable
        self.resultTable = QTableWidget()
        self.resultTable.setColumnCount(3)
        self.resultTable.verticalHeader().hide()
        self.resultTable.horizontalHeader().setStretchLastSection(True)
        # self.resultTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.resultTable.setShowGrid(0)
        self.resultTable.setHorizontalHeaderLabels(['Stap', 'Resultaat', ''])
        self.resultTable.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.resultTable.horizontalHeader().setClickable(0)
        self.resultTable.verticalHeader().setDefaultSectionSize(20)
        self.resultTable.setFocusPolicy(Qt.NoFocus)
        self.resultTable.setColumnWidth(0, 200)
        self.resultTable.setColumnWidth(1, 75)
        self.resultTable.setColumnWidth(2, 200)

        # Central Widget
        layout = QHBoxLayout()
        layout.addWidget(self.resultTable)
        layout.setContentsMargins(10, 10, 10, 10)
        mainWidget = QWidget()
        mainWidget.setLayout(layout)
        self.setCentralWidget(mainWidget)

        self.busy_timer = None

        # Response Window
        self.responseDialog = response.ResponseDlg(self, Qt.WindowTitleHint)
        self.responseDialog.setWindowTitle("Frequency Response")
        self.responseDialog.restoreGeometry(self.settings.value('RespGeometry'))

        # Sensitivity Window
        self.sensDialog = response.ResponseDlg(self, Qt.WindowTitleHint)
        self.sensDialog.setWindowTitle("Reference Sensitivity")
        self.sensDialog.restoreGeometry(self.settings.value('SensGeometry'))

    def show_standards_dialog(self):
        inp, rslt = QInputDialog.getText(self, "Wachtwoord", "Geef wachtwoord:", mode=QLineEdit.Password, flags=Qt.WindowTitleHint)
        if inp == config.WACHTWOORD and rslt is True:
            dlg = standards.StandardsDialog(self, Qt.WindowTitleHint)
            dlg.exec_()

    def show_teds_dialog(self):
        rslt = QMessageBox.information(self, 'TEDS', 'Verbind de opnemer met de TEDS aansluiting.', QMessageBox.Ok|QMessageBox.Cancel)
        if rslt == QMessageBox.Ok:
            sens = self.dut.get('refsens', 1.)
            tedsDialog = teds.TEDSDialog(self, Qt.WindowTitleHint, refsens=sens, parent=self)
            tedsDialog.exec_()

    def change_last_test_result(self, result):
        if result[:5] != 'Bezig':
            self.progress.setVisible(False)
            self.resultTable.removeCellWidget(self.resultTable.rowCount()-1, 2)
            if self.busy_timer:
                self.killTimer(self.busy_timer)
                self.busy_timer = None

        resultItem = QTableWidgetItem(result)
        if result == 'Pass': color = QColor(Qt.darkGreen)
        elif result == 'Fail': color = QColor(Qt.darkRed)
        else: color = QColor(Qt.darkBlue)
        resultItem.setTextColor(color)
        resultItem.setFlags(Qt.ItemIsEnabled)
        self.resultTable.setItem(self.resultTable.rowCount()-1, 1, resultItem)

    def add_test_result(self, test, result, duration=0):
        testItem = QTableWidgetItem(test)
        resultItem = QTableWidgetItem(result)
        progressItem = QTableWidgetItem('')
        if result == 'Pass': color = QColor(Qt.darkGreen)
        elif result == 'Fail': color = QColor(Qt.darkRed)
        else: color = QColor(Qt.darkBlue)
        resultItem.setTextColor(color)
        if len(result) == 0:
            testItem.setTextColor(QColor(Qt.darkBlue))
            font = QFont()
            font.setBold(True)
            testItem.setFont(font)
        testItem.setFlags(Qt.ItemIsEnabled)
        resultItem.setFlags(Qt.ItemIsEnabled)
        progressItem.setFlags(Qt.ItemIsEnabled)
        self.resultTable.insertRow(self.resultTable.rowCount())
        self.resultTable.setItem(self.resultTable.rowCount()-1, 0, testItem)
        self.resultTable.setItem(self.resultTable.rowCount()-1, 1, resultItem)
        self.resultTable.setItem(self.resultTable.rowCount()-1, 2, progressItem)

        # Toon progress bar
        if result[:5] == 'Bezig':
            self.progress = QProgressBar()
            self.progress.setTextVisible(False)
            self.progress.setMaximum(duration)
            self.progress.setStyleSheet('margin: 5px;')
            self.progress_value = 0
            self.resultTable.setCellWidget(self.resultTable.rowCount()-1, 2, self.progress)
            self.busy_timer = self.startTimer(1000)

        QApplication.processEvents()

    def timerEvent(self, event):
        self.progress_value += 1
        self.progress.setValue(self.progress_value)

    def del_ref_trace(self):
        rslt = QMessageBox.warning(self, 'Wis Ref Spectra', 'Weet u zeker dat u de Ref Spectra wilt wissen?', QMessageBox.Ok|QMessageBox.Cancel)
        if rslt == QMessageBox.Ok:
            ref_files_4808 = ['.\\Ref\\LF_4808_ref_spectrum.npz', '.\\Ref\\HF_4808_ref_spectrum.npz']
            for ref_file in ref_files_4808:
                if os.path.exists(ref_file):
                    os.remove(ref_file)

            ref_files_4809 = ['.\\Ref\\LF_4809_ref_spectrum.npz', '.\\Ref\\HF_4809_ref_spectrum.npz']
            for ref_file in ref_files_4809:
                if os.path.exists(ref_file):
                    os.remove(ref_file)

    def select_dut(self):
        dutDialog = dutdialog.DutDialog(self, Qt.WindowTitleHint, default=self.dut['Type'])
        if dutDialog.exec_() and dutDialog.dut_db:
            self.dut = dutDialog.dut_db
            self.status.setText('DUT: %s' % self.dut['Type'])
            logging.info('DUT %s geselecteerd.' % self.dut['Type'])
            self.cal_dut()

    def cal_dut(self):
        self.dutMenu.setDisabled(True)
        self.fileMenu.setDisabled(True)

        self.meas = Measurement(self.dut, parent=self)

        # Signals
        self.meas.clear_test_results.connect(self.clear_test_result)
        self.meas.add_test_result.connect(self.add_test_result)
        self.meas.change_last_test_result.connect(self.change_last_test_result)

        if self.meas.init_instruments():                # Hardware init
            self.meas.resp_dlg = self.responseDialog
            self.meas.sens_dlg = self.sensDialog
            self.responseDialog.show()

            if self.dut['Group'] == 'amp':              # Charge amp
                rslt = self.meas.measure_charge_amp()
            else:                                       # Opnemer
                # Ref meting
                rslt = self.meas.measure_ref()
                # DUT meting
                if rslt:
                    rslt = self.meas.measure_dut()
            if rslt:
                self.meas.calc_full_response()
                self.meas.calc_pass_fail()
                resultDialog = resultdialog.ResultDialog(self.dut, self)
                resultDialog.exec_()
                # TEDS
                if self.dut['TEDS']:
                    self.show_teds_dialog()

                if self.dut['Group'] == 'amp':
                    QMessageBox.warning(self, 'Let op', 'Vergeet niet de bekabeling van het trilstation te herstellen!')

        self.dutMenu.setDisabled(False)
        self.fileMenu.setDisabled(False)

    def clear_test_result(self):
        self.resultTable.setRowCount(0)

    def about_box(self):
        QMessageBox.about(self, 'Over Shake It!',
                          '''
                          <b>Shake It!</b> v %s
                          <p>Copyright &copy; 2016 Albert & Jan Willem
                          <p>Python %s - PyQt %s - Qt %s
                          ''' % (config.VERSION, platform.python_version(), PYQT_VERSION_STR, QT_VERSION_STR))

    def closeEvent(self, event):
        # Save settings
        self.settings.setValue("MainGeometry", self.saveGeometry())
        self.settings.setValue("RespGeometry", self.responseDialog.saveGeometry())
        self.settings.setValue("SensGeometry", self.sensDialog.saveGeometry())
        logging.info('Programma afgesloten')

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            if self.meas:
                self.meas.stop()
