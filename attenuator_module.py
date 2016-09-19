import visa
import config


def init(attenuation=70):
    rm = visa.ResourceManager()
    global attenuator
    attenuator = rm.get_instrument('GPIB::{0}::INSTR'.format(config.ATTENUATOR_ADDRESS))

    set_attenuator_load('1Mohm')
    set_attenuator_output('ON')
    set_attenuation(attenuation)


def set_attenuation(attenuation):
    """
    attenuation = 0 .. 70
    """
    if attenuation < 0: attenuation = 0
    if attenuation > 70: attenuation = 70
    attenuator.write('A {0}'.format(int(attenuation)))


def set_attenuator_output(state):
    """
    state = ON / OFF
    """
    attenuator.write('O {0}'.format(state))


def set_attenuator_load(load):
    """
    load = 600Ohm / 1Mohm / 10Mohm
    """
    attenuator.write('L {0}'.format(load))


if __name__ == '__main__':
    init()
    set_attenuation(20)
