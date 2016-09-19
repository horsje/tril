import numpy as np
import datetime
import ctypes
from PyQt4 import QtCore, QtGui, uic
import config

nidaq = ctypes.windll.nicaiu
DAQmx_Val_DoNotWrite = 12540


def con_rel_res(val, start, tol):
    return start * (1 + 2 * tol) ** val


def con_res(val, start, step):
    return start + val * step


def con_rel_res_to_teds(val, start, tol):
    return int(round(np.log(val / start) / np.log(1 + 2 * tol)))


def teds_value(bits):
    val = 0
    for i in range(len(bits)):
        val += (2 ** i) * bits[i]
    return val


def bitlist(n):
    return [int(digit) for digit in bin(n)[2:][::-1]]


def chk(err):
    if err < 0:
        buf_size = 512
        buf = ctypes.create_string_buffer(b'\0' * buf_size)
        nidaq.DAQmxGetErrorString(err, ctypes.byref(buf), buf_size)
        raise IOError('nidaq call failed with error {}: {}'.format(err, buf.value.decode()))


class TEDS(object):

    def __init__(self, channel='PXI4461/ai1'):
        self.channel = bytes(channel, 'ascii')
        self.bitstream = None

    @property
    def ref_sens(self):
        return con_rel_res(teds_value(self.bitstream[76:92]), 5e-7, 0.00015)

    @property
    def ref_freq(self):
        return con_rel_res(teds_value(self.bitstream[148:156]), 0.35, 0.0175)

    @property
    def cal_date(self):
        teds_val = teds_value(self.bitstream[161:177])
        start_date = datetime.date(1998, 1, 1)
        delta = datetime.timedelta(days=teds_val)
        return start_date + delta

    @property
    def cal_initials(self):
        init1 = teds_value(self.bitstream[177:182]) + 64
        init2 = teds_value(self.bitstream[182:187]) + 64
        init3 = teds_value(self.bitstream[187:192]) + 64
        return chr(init1) + chr(init2) + chr(init3)

    @property
    def cal_period(self):
        return teds_value(self.bitstream[192:204])

    @property
    def ref_temp(self):
        return con_res(teds_value(self.bitstream[156:161]), 15, 0.5)

    @ref_sens.setter
    def ref_sens(self, val):
        ref_sens = con_rel_res_to_teds(val, 5e-7, 0.00015)
        sens_teds = bytearray(16)
        sens_teds[0:len(bin(ref_sens)) - 2] = bitlist(ref_sens)
        self.bitstream[76:92] = sens_teds

    @cal_date.setter
    def cal_date(self, val):
        day, month, year = val
        start_date = datetime.date(1998, 1, 1)
        cal_date = datetime.date(year, month, day)
        delta = (cal_date - start_date).days
        delta_teds = bytearray(16)
        delta_teds[0:len(bin(delta)) - 2] = bitlist(delta)
        self.bitstream[161:177] = delta_teds

    @cal_initials.setter
    def cal_initials(self, val):
        self.bitstream[217:232] = bytearray(15)
        for i in range(len(val)):
            init = bytearray(5)
            init[0:len(bin(ord(val[i]) - 64)) - 2] = bitlist(ord(val[i]) - 64)
            self.bitstream[177 + (i * 5):182 + (i * 5)] = init

    @ref_temp.setter
    def ref_temp(self, val):
        temp = int((val - 15) / 0.5)
        temp_teds = bytearray(5)
        temp_teds[0:len(bin(temp)) - 2] = bitlist(temp)
        self.bitstream[156:161] = temp_teds

    def read_sensor(self):
        size = 31
        data_block = np.zeros(size, dtype=np.uint8)
        chk(nidaq.DAQmxConfigureTEDS(self.channel, b""))
        chk(nidaq.DAQmxGetPhysicalChanTEDSBitStream(self.channel, data_block.ctypes.data, size))
        self.bitstream = bytearray(size * 8)
        for i in range(size):
            for n in range(8):
                self.bitstream[(i * 8) + n] = int((data_block[i] & 1 << n) / 2 ** n)

    def write_sensor(self, path):
        chk(nidaq.DAQmxWriteToTEDSFromFile(self.channel, bytes(path, 'ascii'), DAQmx_Val_DoNotWrite))

    @property
    def type_serial_num(self):
        model = ctypes.c_uint32(0)
        version_num = ctypes.c_uint32(0)
        serial_num = ctypes.c_uint32(0)
        version_letter = ctypes.create_string_buffer(b'\0' * 4)
        chk(nidaq.DAQmxGetPhysicalChanTEDSModelNum(self.channel, ctypes.byref(model)))
        chk(nidaq.DAQmxGetPhysicalChanTEDSVersionLetter(self.channel, ctypes.byref(version_letter), 3))
        vl = version_letter.value.decode()
        if vl == ' ': vl = ''
        chk(nidaq.DAQmxGetPhysicalChanTEDSVersionNum(self.channel, ctypes.byref(version_num)))
        chk(nidaq.DAQmxGetPhysicalChanTEDSSerialNum(self.channel, ctypes.byref(serial_num)))
        return '%s%s%s_%s' % (model.value, vl, version_num.value, serial_num.value)

    @property
    def serial_num(self):
        serial_num = ctypes.c_uint32(0)
        chk(nidaq.DAQmxGetPhysicalChanTEDSSerialNum(self.channel, ctypes.byref(serial_num)))
        return serial_num.value

    def write_virtual_teds_file(self, file):
        with open(file, "wb")as f:
            ver = b"[v03]"
            for v in ver:
                for n in range(8):
                    f.write(bytes(chr(int((v & 1 << n) / 2 ** n)), 'ascii'))
            f.write(self.bitstream)

    def read_virtual_teds_file(self, file):
        with open(file, "rb") as f:
            self.bitstream = bytearray(f.read())[40:]

    def print_sensor_data(self):
        print("Sensor data:")
        print("\tType_Serienr.: \t%s" % self.type_serial_num)
        print("\tRef. Sens.: \t%.10f" % (self.ref_sens * 1000))
        print("\tRef. Freq.: \t%.5f" % self.ref_freq)
        print("\tRef. Temp.: \t%.2f" % self.ref_temp)
        print("\tCal. Date.: \t%s" % self.cal_date)
        print("\tCal. Initials: \t%s" % self.cal_initials)
        print("\tCal. Period: \t%i\n" % self.cal_period)


form_class, base_class = uic.loadUiType('teds.ui')

class TEDSDialog(form_class, base_class):

    def __init__(self, *args, refsens=1.0, parent=None):
        super().__init__(*args)
        self.setupUi(self)

        self.parent = parent

        self.refSensNew.setText(str(refsens))
        self.calMonthNew.setText(str(datetime.datetime.now().month))
        self.calYearNew.setText(str(datetime.datetime.now().year))

        self.teds = TEDS(channel="PXI4461/ai1")
        self.ShowTEDSData()

    def ShowTEDSData(self):
        try:
            self.teds.read_sensor()
            self.refSensStored.setText(str(self.teds.ref_sens * 1000))
            self.calMonthStored.setText(str(self.teds.cal_date.month))
            self.calYearStored.setText(str(self.teds.cal_date.year))
        except IOError as err:
            QtGui.QMessageBox.critical(self.parent, "TEDS", "Fout bij uitlezen opnemer!\n\n%s" % err)

    @QtCore.pyqtSlot()
    def on_editButton_clicked(self):
        self.refSensNew.setEnabled(True)
        self.calMonthNew.setEnabled(True)
        self.calYearNew.setEnabled(True)

    @QtCore.pyqtSlot()
    def on_readSensor_clicked(self):
        self.ShowTEDSData()

    @QtCore.pyqtSlot()
    def on_writeSensor_clicked(self):
        try:
            # Save original TEDS
            dir = config.TEDS_PATH
            type_serial = self.teds.type_serial_num
            file_org = dir + r"\%s_%s_org.ted" % (type_serial, datetime.date.today().isoformat())
            self.teds.write_virtual_teds_file(file_org)

            # Create new TEDS
            self.teds.ref_sens = float(self.refSensNew.text()) / 1000
            self.teds.ref_temp = 23
            self.teds.cal_date = (int(datetime.datetime.now().day), int(self.calMonthNew.text()), int(self.calYearNew.text()))
            self.teds.cal_initials = 'MKC'
            file_new = dir + r"\%s_%s_new.ted" % (type_serial, datetime.date.today().isoformat())
            self.teds.write_virtual_teds_file(file_new)
            self.teds.write_sensor(file_new)
            self.ShowTEDSData()
            QtGui.QMessageBox.information(self.parent, "TEDS", 'TEDS wegschrijven naar opnemer voltooid!\n')
        except (FileNotFoundError, IOError) as err:
            QtGui.QMessageBox.critical(self.parent, "TEDS", "Fout bij wegschrijven TEDS!\n\n%s" % err)


if __name__ == "__main__":
    app = QtGui.QApplication([])
    form = TEDSDialog(refsens=1.023)
    form.show()
    app.exec_()
