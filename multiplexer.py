from visa import Visa


class Shakers:
    SH4808 = 1
    SH4809 = 2


class Inputs:
    Voltage = 1
    LineDrive = 2
    I4mA = 3
    Velocity = 4
    I3506_1 = 5
    I3506_2 = 6


class PrecAttSettings:
    Bypass = 1
    Select = 2


class VelocityLoads:
    Ext = 1
    L2M = 2
    L1M = 3
    L20k = 4
    L10k = 5


class Multiplexer(Visa):
    def __init__(self, visa_address: str):
        super().__init__(visa_address)

        self.clear()
        self.attenuator = -31
        self.prec_att = PrecAttSettings.Bypass

    @property
    def input(self):
        return self._input

    @input.setter
    def input(self, inp: Inputs):
        self._input = inp or 0
        self.write('A{0}'.format(self._input))

    @property
    def velocity_load(self):
        return self._velocity_load

    @velocity_load.setter
    def velocity_load(self, load: VelocityLoads):
        self._velocity_load = load or 0
        self.write('C{0}'.format(self._velocity_load))

    @property
    def prec_att(self):
        return self._prec_att

    @prec_att.setter
    def prec_att(self, setting: PrecAttSettings):
        self._prec_att = setting or 0
        self.write('B{0}'.format(self._prec_att))

    @property
    def shaker(self):
        return self._shaker

    @shaker.setter
    def shaker(self, shaker: Shakers):
        self._shaker = shaker or 0
        self.write('G{0}'.format(self._shaker))

    @property
    def attenuator(self):
        return self._attenuator

    @attenuator.setter
    def attenuator(self, attenuation: int):
        """
        attenuation = -31 .. 31
        """
        attenuation = min(attenuation, 31)
        attenuation = max(attenuation, -31)
        self._attenuator = int(attenuation)

        att_data = ['00', '10', '20', '30', '40', '50', '60', '70',
                    '80', '90', ':0', ';0', '<0', '=0', '>0', '?0',
                    '01', '11', '21', '31', '41', '51', '61', '71',
                    '81', '91', ':1', ';1', '<1', '=1', '>1',
                    '02', '12', '22', '32', '42', '52', '62', '72',
                    '82', '92', ':2', ';2', '<2', '=2', '>2', '?2',
                    '03', '13', '23', '33', '43', '53', '63', '73',
                    '83', '93', ':3', ';3', '<3', '=3', '>3', '?3']

        self.write('E%sF%s' % (att_data[self._attenuator + 31][0], att_data[self._attenuator + 31][1]))


if __name__ == '__main__':
    try:
        mpx = Multiplexer("GPIB::7::INSTR")
        mpx.attenuator = -20
        mpx.shaker = Shakers.SH4809
        mpx.input = Inputs.Velocity
    except IOError as err:
        print('Error: %s' % err)
