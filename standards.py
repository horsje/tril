from PyQt4 import uic
from PyQt4.QtGui import *
import db
import config

form_class, base_class = uic.loadUiType('std_dialog.ui')

class StandardsDialog(base_class, form_class):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

        self.db = db.DB("./" + config.DB_FILENAME)

        self.display_db_values()

        self.editButton.clicked.connect(self.enable_edit)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def display_db_values(self):
        try:
            cap = self.db.query("SELECT * FROM capacitor")[0]['Capacitance']
            self.capInput.setText(str(cap))
            ref = self.db.query("SELECT * FROM ref WHERE Name='Ref1'")[0]['Sens']
            self.refSensInput.setText(str(ref))
            amp = self.db.query("SELECT * FROM ref WHERE Name='Ref1'")[0]['AmpSens']
            self.ampSensInput.setText(str(amp))
        except Exception as err:
            self.editButton.setEnabled(False)
            QMessageBox.critical(self, 'Standaarden', 'Fout bij ophalen gegevens uit DB.\n\n' + str(err), QMessageBox.Ok)

    def write_db_values(self):
        if self.capInput.isEnabled():
            try:
                self.db.update("UPDATE capacitor SET Capacitance=?", float(self.capInput.text()))
                self.db.update("UPDATE ref SET Sens=? WHERE Name='Ref1'", float(self.refSensInput.text()))
                self.db.update("UPDATE ref SET AmpSens=? WHERE Name='Ref1'", float(self.ampSensInput.text()))
                QMessageBox.information(self, 'Standaarden', 'Nieuwe waardes zijn opgeslagen.', QMessageBox.Ok)
            except Exception as err:
                QMessageBox.critical(self, 'Standaarden', 'Fout bij wegschrijven naar database!\n\n' + str(err), QMessageBox.Ok)

    def accept(self):
        self.write_db_values()
        QApplication.processEvents()
        QDialog.accept(self)

    def enable_edit(self):
        self.refSensInput.setEnabled(True)
        self.ampSensInput.setEnabled(True)
        self.capInput.setEnabled(True)


if __name__ == '__main__':
    app = QApplication([])
    dlg = StandardsDialog()
    dlg.show()

    app.exec_()