'''
Toont lijst met DUTs. Gegevens van geselecteerde DUT worden als dict afgeleverd
in self.dut_db.
'''
import os
import pyodbc
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import config


class DutDialog(QDialog):
    
    def __init__(self, *args, default=None):
        super().__init__(*args)

        layout = QVBoxLayout()

        self.dutList = QListWidget()
        types = self.getTypeList()
        self.dutList.addItems(types)
        if default:
            defaultRow = [index for index,type in enumerate(types) if type==default]
            self.dutList.setCurrentRow(defaultRow[0])
        layout.addWidget(self.dutList)

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setGeometry(QRect(30, 240, 341, 32))
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)
        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

        self.setWindowTitle('Selecteer DUT Type')

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.dutList.itemDoubleClicked.connect(self.accept)

        self.dut_db = {}

    def accept(self):
        try:
            dutType = self.dutList.currentItem().text()
            self.dut_db = self.executeQuery('SELECT * FROM dut WHERE'
                                            ' Type = \'%s\'' % dutType)[0]

            # Lege waardes in DUT dict nul maken
            for key in self.dut_db.keys():
                if self.dut_db[key] is None:
                    self.dut_db[key] = 0

            # Max/Min Freq bepalen
            self.dut_db['max_freq'] = max([float(self.dut_db['Band1EndFreq']),float(self.dut_db['Band2EndFreq']),float(self.dut_db['Band3EndFreq'])])
            self.dut_db['min_freq'] = float(self.dut_db['Band1StartFreq'])

            # Sensitivity Unit
            if self.dut_db['Group'].lower() == 'amp':
                self.dut_db['sensunit'] = 'mV/pC'
            elif self.dut_db['Group'].lower() == 'acc':
                if self.dut_db['TestParameter'].lower() == 'charge':
                    self.dut_db['sensunit'] = 'pC/(m/s\u00B2)'
                else:
                    self.dut_db['sensunit'] = 'mV/(m/s\u00B2)'
            else:
                self.dut_db['sensunit'] = 'mV/(m/s)'
        except:
            self.dut_db = {}
        
        QDialog.accept(self)


    def getTypeList(self):        
        typeListQuery = self.executeQuery('SELECT Type FROM dut ORDER BY Type')
        typeList = [field['Type'] for field in typeListQuery]               
        return typeList

    def executeQuery(self, query):
        result = []
        try:
            DBfile = './' + str(config.DB_FILENAME)
            conn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ='+ DBfile)
            try:
                cursor = conn.cursor().execute(query)
                columns = [column[0] for column in cursor.description]
                for row in cursor.fetchall():
                    result.append(dict(zip(columns,row)))
            finally:
                cursor.close()
                conn.close()
        except:
            QMessageBox.warning(self, 'Database fout', 'Fout tijdens ophalen database gegevens!')
                
        return result


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlg = DutDialog()
    dlg.exec_() 
    
    app.exec_()

