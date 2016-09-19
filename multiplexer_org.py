import ctypes
import visa_messages

VI_NULL = 0
nivisa = ctypes.windll.visa32

def chk(rslt):
    if rslt != 0:
        abbr, message = visa_messages.messages.get(rslt, ('', rslt))
        raise IOError("Visa call failed with error {}: {}".format(rslt, message))
    else:
        return 1


class Multiplexer(object):
    def __init__(self, visa_address):

        self.rm_handle = ctypes.c_int(0)
        chk(nivisa.viOpenDefaultRM(ctypes.byref(self.rm_handle)))

        self.mpx = ctypes.c_int(0)
        chk(nivisa.viOpen(self.rm_handle, visa_address.encode(), VI_NULL, VI_NULL, ctypes.byref(self.mpx)))
        self.clear()
        self.attenuator = -31
        self.prec_att = 'Bypass'

    def __del__(self):
        if self.mpx:
            chk(nivisa.viClose(self.mpx))
        if self.rm_handle:
            chk(nivisa.viClose(self.rm_handle))

    def visaWrite(self, command):
        bytes_written = ctypes.c_int(0)
        chk(nivisa.viWrite(self.mpx, (command+chr(10)).encode(), len(command)+1, ctypes.byref(bytes_written)))

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, inputname):
        """
        inputname = ['None', 'Voltage', 'LineDrive', '4mA', 'Velocity', '3506_1', '3506_2']
        """
        self._input = inputname
        inputs = ['None', 'Voltage', 'LineDrive', '4mA', 'Velocity', '3506_1', '3506_2']
        index = [i for i, inp in enumerate(inputs) if inp == inputname]
        self.visaWrite('A{0}'.format(index[0]))

    @property
    def velocity_load(self):
        return self._velocity_load

    @velocity_load.setter
    def velocity_load(self, load):
        """
        load = ['None', 'Ext', '2M', '1M', '20k', '10k']
        """
        self._velocity_load = load
        loads = ['None', 'Ext', '2M', '1M', '20k', '10k']
        index = [i for i, l in enumerate(loads) if l == load]
        self.visaWrite('C{0}'.format(index[0]))

    @property
    def prec_att(self):
        return self._prec_att

    @prec_att.setter
    def prec_att(self, setting):
        """
        setting = ['None', 'Bypass', 'Select']
        """
        self._prec_att = setting
        settings = ['None', 'Bypass', 'Select']
        index = [i for i, s in enumerate(settings) if s == setting]
        self.visaWrite('B{0}'.format(index[0]))

    @property
    def shaker(self):
        return self._shaker

    @shaker.setter
    def shaker(self, shaker):
        """
        shaker = ['None', '4808', '4809']
        """
        self._shaker = shaker
        shakers = ['None', '4808', '4809']
        index = [i for i, s in enumerate(shakers) if s == shaker]
        self.visaWrite('G{0}'.format(index[0]))

    @property
    def attenuator(self):
        return self._attenuator

    @attenuator.setter
    def attenuator(self, attenuation):
        """
        attenuation = -31 .. 31
        """
        self._attenuator = attenuation
        att_data = ['00','10','20','30','40','50','60','70',
                   '80','90',':0',';0','<0','=0','>0','?0',
                   '01','11','21','31','41','51','61','71',
                   '81','91',':1',';1','<1','=1','>1',
                   '02','12','22','32','42','52','62','72',
                   '82','92',':2',';2','<2','=2','>2','?2',
                   '03','13','23','33','43','53','63','73',
                   '83','93',':3',';3','<3','=3','>3','?3']
        if attenuation > 31:
            attenuation = 31
        if attenuation < -31:
            attenuation = -31

        self.visaWrite('E{0}F{1}'.format(att_data[int(attenuation)+31][0], att_data[int(attenuation)+31][1]))

    def clear(self):
        chk(nivisa.viClear(self.mpx))


if __name__ == '__main__':
    try:
        mpx = Multiplexer("GPIB::7::INSTR")
        mpx.attenuator = -20
        mpx.input = 'Voltage'
    except IOError as err:
        print('Error: %s' % err)
