import visa
import config


class Attenuator():

    def __init__(self, gpib_address, attenuation=70):
        try:
            rm = visa.ResourceManager()
            self.attenuator = rm.get_instrument('GPIB::{0}::INSTR'.format(gpib_address))

            self.set_attenuator_load('1Mohm')
            self.set_attenuator_output('ON')
            self.set_attenuation(attenuation)
        except visa.VisaIOError as err:
            raise IOError('Error: %s' % err)


    def set_attenuation(self, attenuation):
        """
        attenuation = 0 .. 70
        """
        if attenuation < 0: attenuation = 0
        if attenuation > 70: attenuation = 70
        try:
            self.attenuator.write('A {0}'.format(int(attenuation)))
        except visa.VisaIOError as err:
            raise IOError('Error: %s' % err)


    def set_attenuator_output(self, state):
        """
        state = ON / OFF
        """
        try:
            self.attenuator.write('O {0}'.format(state))
        except visa.VisaIOError as err:
            raise IOError('Error: %s' % err)


    def set_attenuator_load(self, load):
        """
        load = 600Ohm / 1Mohm / 10Mohm
        """
        try:
            self.attenuator.write('L {0}'.format(load))
        except visa.VisaIOError as err:
            raise IOError('Error: %s' % err)


if __name__ == '__main__':
    try:
        pratt = Attenuator(7)
        pratt.set_attenuation(20)
    except IOError as err:
        print('Error: %s' % err)
