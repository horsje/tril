from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import time
import logging
import numpy as np
import _thread
import config
import db
from analyzer import Analyzer
from multiplexer import *

Succesful = True
Unsuccesful = False

logger = logging.getLogger('tril')


class Measurement(QObject):

    clear_test_results = pyqtSignal()
    add_test_result = pyqtSignal(str, str, int)
    change_last_test_result = pyqtSignal(str)

    def __init__(self, dut, parent=None):
        QObject.__init__(self)

        self.parent = parent

        self.dut = dut
        self.ref = self.select_ref_specs_from_db(config.REF_ACC)

        self.att_setting = -31

        self.dut['input_range'] = self.calc_input_range()

        self.analyzer = None
        self.mpx = None

        self.exc_ready = False
        self.exc_error = None
        self.stopped = False

        self.init_ready = False
        self.init_error = None

        self.resp_dlg = None
        self.sens_dlg = None

    def init_instruments(self):
        try:
            self.analyzer = Analyzer(dev_name=config.DAQ_DEVNAME, start_freq=self.dut['min_freq'], stop_freq=self.dut['max_freq'], dut_input_range=self.dut['input_range'])
            self.analyzer.data_ready.connect(self.update_spectrum_dialogs)
            self.analyzer.avg_ready.connect(self.update_spectrum_dialogs)
            self.mpx = Multiplexer(visa_address=config.MULTIPLEXER_ADDDRESS)
            self.mpx.prec_att = PrecAttSettings.Bypass
            return Succesful
        except IOError as err:
            self.error_message(str(err))
            return Unsuccesful

    def calc_input_range(self):
        if self.dut['Group'] == 'acc':
            if self.dut['TestParameter'].lower() == 'charge':
                if self.dut['Sens'] < 0.5:
                    input_range = 1
                else:
                    input_range = 10
            elif self.dut['TestParameter'].lower() == 'voltage':
                if self.dut['Sens'] < 5:
                    input_range = 1
                else:
                    input_range = 10
            else:
                input_range = 10
        elif self.dut['Group'] == 'vel':
            input_range = 10
        else:
            input_range = 10
        return input_range

    def status_message(self, text, status='', duration=0):
        self.add_test_result.emit(text, status, duration)

    def change_status_message(self, status):
        self.change_last_test_result.emit(status)

    def measure_ref(self):
        if self.valid_ref_spec('LF') and self.valid_ref_spec('HF'):
            return Succesful
        else:
            if self.dut['Shakertype'] == '4808':
                rslt = self.instruction('''
                                        <p>Monteer de <b>WS3104</b> adapterplaat op de <b>4808</b> shaker.
                                        <p>Monteer de <b>REF1</b> opnemer op de adapterplaat.
                                        <p>Verbind de <b>REF1</b> opnemer met de <b>REF1</b> Conditioning Amplifier.
                                        ''')
            else:
                rslt = self.instruction('''
                                        <p>Monteer de <b>REF2</b> opnemer op de <b>4809</b> shaker.
                                        <p>Verbind de <b>REF2</b> opnemer met de <b>4809 Working Std. Input</b> van de Multiplexer.
                                        <p>Monteer de <b>REF1</b> opnemer op de <b>REF2</b> opnemer.
                                        <p>Verbind de <b>REF1</b> opnemer met de <b>REF1</b> Conditioning Amplifier.
                                        ''')
            if rslt == QMessageBox.Ok:
                # LF Meting
                self.clear_test_results.emit()
                self.status_message('Referentie Meting LF')

                # Cond Amp settings
                rslt = self.instruction('''
                                        <p>Stel de <b>Conditioning Amplifier</b> als volgt in:
                                        <p>SENSITIVITY pC/Unit: <b>1.00</b>
                                        <p>VOLT/UNIT OUT: <b>0.01</b>
                                        ''')

                rslt = self.instruction('Draai de <b>Gain</b> van de <b>2712 Power Amplifier</b> naar <b>maximaal</b>.')

                if rslt == QMessageBox.Ok:

                    try:
                        # Multiplexer settings
                        if self.dut['Shakertype'] == '4808':
                            self.mpx.shaker = Shakers.SH4808
                        else:
                            self.mpx.shaker = Shakers.SH4809
                        self.mpx.input = Inputs.I3506_1
                        self.mpx.attenuator = -31

                        self.analyzer.dut_input_range = 1

                        # Levels check
                        self.status_message('Excitation Level Check', 'Bezig...')
                        self.analyzer.navg = config.AVG_LEV
                        self.analyzer.fs = config.SAMPLE_FREQ_LF
                        self.analyzer.nfft = config.N_FFT_LF
                        self.analyzer.stop_freq = config.FREQ_LIMIT_LF

                        # Response Dialog
                        self.resp_display = DisplayChoice.AutoSpectrumATotalLF

                        # Start set_excitation_level als thread
                        self.exc_ready = False
                        self.exc_error = None
                        _thread.start_new_thread(self.set_excitation_level, ())
                        while not (self.exc_ready or self.exc_error):
                            QApplication.processEvents()
                            time.sleep(.01)
                        if not self.exc_error:
                            self.change_status_message('Pass')
                        else:
                            raise IOError(self.exc_error)
                    except IOError as err:
                        self.change_status_message('Fail')
                        self.error_message(str(err))
                        return Unsuccesful

                    # LF Freq Response
                    try:
                        # Response Dialog
                        self.resp_display = DisplayChoice.FreqRespRefLF

                        self.analyzer.navg = config.AVG_ACQ_LF
                        acq_time = int(self.analyzer.navg * self.analyzer.nfft / self.analyzer.fs)
                        self.status_message('Frequency Response Meting', 'Bezig...', acq_time)
                        time.sleep(1)
                        self.analyzer.start_random_noise()
                        time.sleep(1)

                        # Start analyzer.acquire_data als thread
                        self.analyzer.acq_ready = False
                        self.analyzer.error = None
                        _thread.start_new_thread(self.analyzer.acquire_data, ())
                        while not (self.analyzer.acq_ready or self.analyzer.error):
                            QApplication.processEvents()
                            time.sleep(0.01)
                        self.analyzer.stop_random_noise()
                        self.mpx.attenuator = -31
                        if not self.analyzer.error:
                            self.change_status_message('Klaar')
                        else:
                            raise IOError(self.analyzer.error)
                    except IOError as err:
                        self.analyzer.stop_random_noise()
                        self.mpx.attenuator = -31
                        self.change_status_message('Fail')
                        self.error_message(str(err))
                        return Unsuccesful

                    # Coherence
                    self.status_message('Coherence Check', 'Bezig...')
                    if self.check_coherence(min_freq=self.analyzer.start_freq, max_freq=config.FREQ_LIMIT_LF, ref=True):
                        self.change_status_message('Pass')
                    else:
                        self.change_status_message('Fail')
                        self.resp_display = DisplayChoice.CoherenceLF
                        self.update_spectrum_dialogs()
                        self.error_message(self.coherence_error)
                        return Unsuccesful

                    # Check Ref Spectrum
                    self.status_message('Reference Check', 'Bezig...')
                    if self.check_reference_response('LF'):
                        self.change_status_message('Pass')
                        self.store_ref_response('LF')
                    else:
                        self.change_status_message('Fail')
                        self.error_message(self.reference_error)
                        return Unsuccesful

                    # HF Meting
                    self.status_message('Referentie Meting HF')

                    try:
                        # Levels check
                        self.status_message('Excitation Level Check', 'Bezig...')
                        self.analyzer.navg = 5 * config.AVG_LEV
                        self.analyzer.fs = config.SAMPLE_FREQ_HF
                        self.analyzer.nfft = config.N_FFT_HF
                        if self.dut['Shakertype'] == '4808':
                            self.analyzer.start_freq = 5
                            self.analyzer.stop_freq = 5e3
                        else:
                            self.analyzer.start_freq = 10
                            self.analyzer.stop_freq = 10e3

                        # Response Dialog
                        self.resp_display = DisplayChoice.AutoSpectrumATotalHF

                        # Start set_excitation_level als thread
                        self.exc_ready = False
                        self.exc_error = None
                        _thread.start_new_thread(self.set_excitation_level, ())
                        while not (self.exc_ready or self.exc_error):
                            QApplication.processEvents()
                            time.sleep(.01)
                        if not self.exc_error:
                            self.change_status_message('Pass')
                        else:
                            raise IOError(self.exc_error)
                    except IOError as err:
                        self.change_status_message('Fail')
                        self.error_message(str(err))
                        return Unsuccesful

                    # HF Freq Response
                    try:
                        # Response Dialog
                        self.resp_display = DisplayChoice.FreqRespRefHF

                        self.analyzer.navg = config.AVG_ACQ_HF
                        acq_time = int(self.analyzer.navg * self.analyzer.nfft / self.analyzer.fs)
                        self.status_message('Frequency Response Meting', 'Bezig...', acq_time)
                        time.sleep(1)
                        self.analyzer.start_random_noise()
                        time.sleep(1)

                        # Start analyzer.acquire_data als thread
                        self.analyzer.acq_ready = False
                        self.analyzer.error = None
                        _thread.start_new_thread(self.analyzer.acquire_data, ())
                        while not (self.analyzer.acq_ready or self.analyzer.error):
                            QApplication.processEvents()
                            time.sleep(0.01)
                        self.analyzer.stop_random_noise()
                        self.mpx.attenuator = -31
                        if not self.analyzer.error:
                            self.change_status_message('Klaar')
                        else:
                            raise IOError(self.analyzer.error)
                    except IOError as err:
                        self.analyzer.stop_random_noise()
                        self.mpx.attenuator = -31
                        self.change_status_message('Fail')
                        self.error_message(str(err))
                        return Unsuccesful

                    # Coherence
                    self.status_message('Coherence Check', 'Bezig...')
                    if self.check_coherence(min_freq=config.FREQ_LIMIT_LF, max_freq=self.analyzer.stop_freq, ref=True):
                        self.change_status_message('Pass')
                    else:
                        self.change_status_message('Fail')
                        self.resp_display = DisplayChoice.CoherenceHF
                        self.update_spectrum_dialogs()
                        self.error_message(self.coherence_error)
                        return Unsuccesful

                    # Check Ref Spectrum
                    self.status_message('Reference Check', 'Bezig...')
                    if self.check_reference_response('HF'):
                        self.change_status_message('Pass')
                        self.store_ref_response('HF')
                        return Succesful
                    else:
                        self.change_status_message('Fail')
                        self.error_message(self.reference_error)
                        return Unsuccesful
            else:
                return Unsuccesful

    def valid_ref_spec(self, freq_range):
        try:
            if freq_range == 'LF':
                ref_file = self.load_ref_response('LF')
            else:
                ref_file = self.load_ref_response('HF')
            if time.time() - ref_file['time'] < config.REF_VALID_TIME * 3600:
                return True
            else:
                return False
        except IOError as err:
            return False

    def store_ref_response(self, freq_range):
        filename = '%s_%s_ref_spectrum.npz' % (freq_range, self.dut['Shakertype'])
        file = os.path.join(config.REF_SPEC_PATH, filename)
        np.savez(file, resp=self.analyzer.freq_response, shaker=self.dut['Shakertype'], stop=self.analyzer.stop_freq,
                 freqs=self.analyzer.freqs, time=time.time())

    def load_ref_response(self, freq_range):
        filename = '%s_%s_ref_spectrum.npz' % (freq_range, self.dut['Shakertype'])
        file = os.path.join(config.REF_SPEC_PATH, filename)
        ref_file = np.load(file)
        return ref_file

    def check_coherence(self, min_freq, max_freq, ref=False):
        if ref:
            tol = config.ACC_COHERENCE_TOL
        else:
            if self.dut['Group'].lower() == 'vel':
                tol = config.VEL_COHERENCE_TOL
            else:
                tol = config.ACC_COHERENCE_TOL

        skip_lines = round(config.COHERENCE_LINE_SKIP * (max_freq - min_freq) / self.analyzer.fstep)
        line_low = int((min_freq / self.analyzer.fstep) + skip_lines)
        line_high = int((max_freq / self.analyzer.fstep) - skip_lines)
        coh_ok = True
        for line in self.analyzer.coherence[line_low:line_high]:
            if abs(line - 1) > tol:
                coh_ok = False
                break
        return coh_ok

    def check_reference_response(self, freq_range):
        if self.dut['Shakertype'] == '4808':
            f1 = config.F1SH4808
            f2 = config.F2SH4808
            fw = config.FWSH4808
            ash = config.ASH4808
            # wstd_sens = config.WSTD_SENS_4808
            if freq_range == 'LF':
                min_line = int(5 / self.analyzer.fstep)
            else:
                min_line = int(config.FREQ_LIMIT_LF / self.analyzer.fstep)

        else:
            f1 = config.F1SH4809
            f2 = config.F2SH4809
            fw = config.FWSH4809
            ash = config.ASH4809
            # wstd_sens = config.WSTD_SENS_4809
            if freq_range == 'LF':
                min_line = int(10 / self.analyzer.fstep)
            else:
                min_line = int(config.FREQ_LIMIT_LF / self.analyzer.fstep)

        freq_resp = self.analyzer.freq_response
        f = self.analyzer.freqs
        f_ref = self.dut['SensFreq']
        # volgens boek
        norm_val = abs(freq_resp[int(f_ref) // self.analyzer.fstep])
        # jw Checkt ook instelling cond. amp
        # norm_val = self.ref['Sens'] * self.ref['AmpSens'] * config.g / (wstd_sens * config.LINE_DRIVE_SENS * 1000)

        # Zie blz. 109 Manual 9610
        corr = np.exp(-ash * np.log(f / f_ref)) * (1 - (f_ref / fw)**2) * (1 - (f / f1)**2) * (1 - (f / f2)**2) / \
               (norm_val * (1 - (f / fw)**2) * (1 - (f_ref / f1)**2) * (1 - (f_ref / f2)**2))
        corr_resp = abs(freq_resp) * corr

        #jw
        np.savez('.\\ref_resp_check.npz', resp=freq_resp, corr=corr, freqs=f)

        # Check Tol
        ref_tol_ok = True
        max_line = int(self.analyzer.stop_freq / self.analyzer.fstep)
        for line in range(min_line, max_line):
            if corr_resp[line] > (1 + (config.REF_SPEC_TOL / 100)) or corr_resp[line] < (1 - (config.REF_SPEC_TOL / 100)):
                ref_tol_ok = False
                break
        return ref_tol_ok

    def new_level(self, end_level, current_level):
        tmp = 10 * np.log10(end_level / current_level)
        if tmp < 0:
            new = np.round(tmp - 0.5)
        else:
            new = np.round(tmp + 0.5)
        return new

    def set_excitation_level(self):
        self.exc_ready = False
        level_ok = False
        att_setting = -20

        try:
            self.mpx.attenuator = att_setting
            time.sleep(1)

            self.analyzer.start_random_noise()
            time.sleep(1)

            if self.dut['Shakertype'] == '4808':
                wstd_sens = config.WSTD_SENS_4808
                max_att_setting = config.MAX_ATT_SETTING_4808
            else:
                wstd_sens = config.WSTD_SENS_4809
                max_att_setting = config.MAX_ATT_SETTING_4809

            tries = 0
            while (not level_ok) and att_setting < max_att_setting and tries < 10:
                self.analyzer.acquire_data()
                exc_level = self.analyzer.calc_total_value(input=0) / (wstd_sens * config.LINE_DRIVE_SENS)
                logger.info('exc_level: %f' % exc_level)
                print('exc_lev: ', exc_level)

                if (exc_level < config.MIN_G_LEVEL) or (exc_level > config.MAX_G_LEVEL):
                    self.analyzer.stop_random_noise()
                    raise IOError(self.excitation_error)

                if (exc_level < (config.G_LEVEL - config.G_LEVEL_TOL)) \
                        or (exc_level > (config.G_LEVEL + config.G_LEVEL_TOL)):
                    att_setting += self.new_level(config.G_LEVEL, exc_level)
                    self.mpx.attenuator = att_setting
                    time.sleep(0.25)
                else:
                    level_ok = True
                tries += 1

            self.analyzer.stop_random_noise()

            if not level_ok:
                raise IOError(self.excitation_error)
            else:
                self.exc_ready = True
        except IOError as err:
            self.analyzer.stop_random_noise()
            self.exc_error = err

    def measure_dut(self):
        if self.dut['Shakertype'] == '4808':
            instruction = 'Monteer de <b>DUT</b> op de <b>4808</b> shaker.'
        else:
            instruction = 'Monteer de <b>DUT</b> op de <b>REF2</b> opnemer op de <b>4809</b> shaker.'
        rslt = self.instruction(instruction, self.dut['MontageTip'])
        if rslt == QMessageBox.Ok:
            rslt = self.select_dut_input()
            if rslt == QMessageBox.Ok:
                # LF Meting
                self.clear_test_results.emit()
                self.analyzer.stored_response = self.load_ref_response('LF')['resp']
                self.status_message('DUT Meting LF')

                try:
                    # Multiplexer settings
                    if self.dut['Shakertype'] == '4808':
                        self.mpx.shaker = Shakers.SH4808
                    else:
                        self.mpx.shaker = Shakers.SH4809

                    # Levels check
                    self.status_message('Excitation Level Check', 'Bezig...')
                    self.analyzer.navg = config.AVG_LEV
                    self.analyzer.fs = config.SAMPLE_FREQ_LF
                    self.analyzer.nfft = config.N_FFT_LF
                    self.analyzer.stop_freq = config.FREQ_LIMIT_LF
                    self.analyzer.dut_input_range = self.dut['input_range']

                    # Response Dialog
                    self.resp_display = DisplayChoice.AutoSpectrumATotalLF

                    # Start set_excitation_level als thread
                    self.exc_ready = False
                    self.exc_error = None
                    _thread.start_new_thread(self.set_excitation_level, ())
                    while not (self.exc_ready or self.exc_error):
                        QApplication.processEvents()
                        time.sleep(0.01)
                    if not self.exc_error:
                        self.change_status_message('Pass')
                    else:
                        raise IOError(self.exc_error)
                except IOError as err:
                    self.change_status_message('Fail')
                    self.error_message(str(err))
                    return Unsuccesful

                # LF Freq Response
                try:
                    # Response Dialog
                    self.resp_display = DisplayChoice.FreqRespDutLF

                    self.analyzer.navg = config.AVG_ACQ_LF
                    acq_time = int(self.analyzer.navg * self.analyzer.nfft / self.analyzer.fs)
                    self.status_message('Frequency Response Meting', 'Bezig...', acq_time)
                    time.sleep(1)
                    self.analyzer.start_random_noise()
                    time.sleep(1)

                    # Start analyzer.acquire_data als thread
                    self.analyzer.acq_ready = False
                    self.analyzer.error = None
                    _thread.start_new_thread(self.analyzer.acquire_data, ())
                    while not (self.analyzer.acq_ready or self.analyzer.error):
                        QApplication.processEvents()
                        time.sleep(0.01)
                    self.analyzer.stop_random_noise()
                    self.mpx.attenuator = -31
                    if not self.analyzer.error:
                        self.change_status_message('Klaar')
                    else:
                        raise IOError(self.analyzer.error)
                except IOError as err:
                    self.analyzer.stop_random_noise()
                    self.mpx.attenuator = -31
                    self.change_status_message('Fail')
                    self.error_message(str(err))
                    return Unsuccesful

                # Coherence
                self.status_message('Coherence Check', 'Bezig...')

                if not self.check_coherence(min_freq=self.dut['min_freq'], max_freq=config.FREQ_LIMIT_LF):
                    self.change_status_message('Fail')
                    self.resp_display = DisplayChoice.CoherenceLF
                    self.update_spectrum_dialogs()
                    rslt = self.error_message(self.coherence_error, ignore_button=True)
                    if rslt == QMessageBox.Ok:
                        return Unsuccesful
                else:
                    self.change_status_message('Pass')

                # Calc LF DUT Response
                self.status_message('DUT LF Response Berekening', 'Bezig...')
                self.dut['result_lf'], self.dut['freqs_lf'] = self.calc_dut_freq_response()
                self.change_status_message('Klaar')

                time.sleep(2)

                # HF Meting
                self.status_message('DUT Meting HF')
                self.analyzer.stored_response = self.load_ref_response('HF')['resp']

                # Levels check
                try:
                    self.status_message('Excitation Level Check', 'Bezig...')
                    self.analyzer.navg = 5 * config.AVG_LEV
                    self.analyzer.fs = config.SAMPLE_FREQ_HF
                    self.analyzer.nfft = config.N_FFT_HF
                    self.analyzer.stop_freq = max(self.dut['max_freq'], 3e3)
                    self.analyzer.dut_input_range = self.dut['input_range']

                    # Response Dialog
                    self.resp_display = DisplayChoice.AutoSpectrumATotalHF

                    # Start set_excitation_level als thread
                    self.exc_ready = False
                    self.exc_error = None
                    _thread.start_new_thread(self.set_excitation_level, ())
                    while not (self.exc_ready or self.exc_error):
                        QApplication.processEvents()
                        time.sleep(0.01)
                    if not self.exc_error:
                        self.change_status_message('Pass')
                    else:
                        raise IOError(self.exc_error)
                except IOError as err:
                    self.change_status_message('Fail')
                    self.error_message(str(err))
                    return Unsuccesful

                # HF Freq Response
                try:
                    # Response Dialog
                    self.resp_display = DisplayChoice.FreqRespDutHF

                    self.analyzer.navg = config.AVG_ACQ_HF
                    acq_time = int(self.analyzer.navg * self.analyzer.nfft / self.analyzer.fs)
                    time.sleep(1)
                    self.status_message('Frequency Response Meting', 'Bezig...', acq_time)
                    self.analyzer.start_random_noise()
                    time.sleep(1)

                    # Start analyzer.acquire_data als thread
                    self.analyzer.acq_ready = False
                    self.analyzer.error = None
                    _thread.start_new_thread(self.analyzer.acquire_data, ())
                    while not (self.analyzer.acq_ready or self.analyzer.error):
                        QApplication.processEvents()
                        time.sleep(0.01)
                    self.analyzer.stop_random_noise()
                    self.mpx.attenuator = -31
                    if not self.analyzer.error:
                        self.change_status_message('Klaar')
                    else:
                        raise IOError(self.analyzer.error)
                except IOError as err:
                    self.analyzer.stop_random_noise()
                    self.mpx.attenuator = -31
                    self.change_status_message('Fail')
                    self.error_message(str(err))
                    return Unsuccesful

                # Coherence
                self.status_message('Coherence Check', 'Bezig...')
                if not self.check_coherence(min_freq=config.FREQ_LIMIT_LF, max_freq=self.dut['max_freq']):
                    self.change_status_message('Fail')
                    self.resp_display = DisplayChoice.CoherenceHF
                    self.update_spectrum_dialogs()
                    rslt = self.error_message(self.coherence_error, ignore_button=True)
                    if rslt == QMessageBox.Ok:
                        return Unsuccesful
                else:
                    self.change_status_message('Pass')

                # Calc HF DUT Response
                self.status_message('DUT HF Response Berekening', 'Bezig...')
                self.dut['result_hf'], self.dut['freqs_hf'] = self.calc_dut_freq_response()
                self.change_status_message('Klaar')

                self.analyzer.reset()
                self.mpx.clear()

                return Succesful

    def measure_charge_amp(self):
        instruction = 'Verbind de <b>Output AO 0</b> van de PXI4461 via een BNC T-stuk met ' \
                      'de <b>Input AI 0</b> van de PXI4461 en de <b>1nF Condensator</b> (H596).' \
                      '<p>Verbind de andere zijde van de Condensator met de <b>DUT Input</b>.'
        rslt = self.instruction(instruction)
        if rslt == QMessageBox.Ok:
            rslt = self.select_dut_input()
            if rslt == QMessageBox.Ok:
                # LF Meting
                self.clear_test_results.emit()
                self.status_message('DUT Meting LF')

                # Response Dialog
                self.resp_display = DisplayChoice.FreqRespAmpLF

                self.analyzer.fs = config.SAMPLE_FREQ_LF
                self.analyzer.nfft = config.N_FFT_LF
                self.analyzer.stop_freq = config.FREQ_LIMIT_LF
                self.analyzer.dut_input_range = 10
                self.analyzer.output_level = 0.01

                # LF Freq Response
                try:
                    self.analyzer.navg = config.AVG_ACQ_LF
                    acq_time = int(self.analyzer.navg * self.analyzer.nfft / self.analyzer.fs)
                    self.status_message('Frequency Response Meting', 'Bezig...', acq_time)
                    # time.sleep(1)
                    self.analyzer.start_random_noise()
                    time.sleep(1)

                    # Start analyzer.acquire_data als thread
                    self.analyzer.acq_ready = False
                    self.analyzer.error = None
                    _thread.start_new_thread(self.analyzer.acquire_data, ())
                    while not (self.analyzer.acq_ready or self.analyzer.error):
                        QApplication.processEvents()
                        time.sleep(0.01)
                    self.analyzer.stop_random_noise()
                    if not self.analyzer.error:
                        self.change_status_message('Klaar')
                    else:
                        raise IOError(self.analyzer.error)
                except IOError as err:
                    self.analyzer.stop_random_noise()
                    self.change_status_message('Fail')
                    self.error_message(str(err))
                    return Unsuccesful

                # Coherence
                self.status_message('Coherence Check', 'Bezig...')

                if not self.check_coherence(min_freq=self.dut['min_freq'], max_freq=config.FREQ_LIMIT_LF):
                    self.change_status_message('Fail')
                    self.resp_display = DisplayChoice.CoherenceLF
                    self.update_spectrum_dialogs()
                    rslt = self.error_message(self.coherence_error, ignore_button=True)
                    if rslt == QMessageBox.Ok:
                        return Unsuccesful
                else:
                    self.change_status_message('Pass')

                # Calc LF DUT Response
                self.status_message('DUT LF Response Berekening', 'Bezig...')
                self.dut['result_lf'], self.dut['freqs_lf'] = self.calc_amp_freq_response()
                self.change_status_message('Klaar')

                # HF Meting
                self.status_message('DUT Meting HF')

                # Response Dialog
                self.resp_display = DisplayChoice.FreqRespAmpHF

                self.analyzer.fs = 51.2e3
                self.analyzer.nfft = config.N_FFT_HF
                self.analyzer.stop_freq = max(self.dut['max_freq'], 3e3)
                self.analyzer.dut_input_range = 10
                self.analyzer.netfilter_enabled = False

                # HF Freq Response
                try:
                    self.analyzer.navg = config.AVG_ACQ_HF
                    acq_time = int(self.analyzer.navg * self.analyzer.nfft / self.analyzer.fs) + 3
                    self.status_message('Frequency Response Meting', 'Bezig...', acq_time)
                    # time.sleep(1)
                    self.analyzer.start_random_noise()
                    time.sleep(1)

                    # Start analyzer.acquire_data als thread
                    self.analyzer.acq_ready = False
                    self.analyzer.error = None
                    _thread.start_new_thread(self.analyzer.acquire_data, ())
                    while not (self.analyzer.acq_ready or self.analyzer.error):
                        QApplication.processEvents()
                        time.sleep(0.01)
                    self.analyzer.stop_random_noise()
                    if not self.analyzer.error:
                        self.change_status_message('Klaar')
                    else:
                        raise IOError(self.analyzer.error)
                except IOError as err:
                    self.analyzer.stop_random_noise()
                    self.change_status_message('Fail')
                    self.error_message(str(err))
                    return Unsuccesful

                # Coherence
                self.status_message('Coherence Check', 'Bezig...')
                if not self.check_coherence(min_freq=config.FREQ_LIMIT_LF, max_freq=self.dut['max_freq']):
                    self.change_status_message('Fail')
                    self.resp_display = DisplayChoice.CoherenceHF
                    self.update_spectrum_dialogs()
                    rslt = self.error_message(self.coherence_error, ignore_button=True)
                    if rslt == QMessageBox.Ok:
                        return Unsuccesful
                else:
                    self.change_status_message('Pass')

                # Calc HF DUT Response
                self.status_message('DUT HF Response Berekening', 'Bezig...')
                self.dut['result_hf'], self.dut['freqs_hf'] = self.calc_amp_freq_response()
                self.change_status_message('Klaar')

                self.analyzer.reset()
                self.mpx.clear()

                return Succesful

    def select_dut_input(self):
        rslt = False
        if self.dut['Group'].lower() == 'acc' or self.dut['Group'].lower() == 'amp':
            if self.dut['TestParameter'].lower() == 'charge':
                self.mpx.input = Inputs.I3506_1
                instruction = '<p>Verbind de <b>DUT</b> Output met de Conditioning Amplifier <b>REF1</b>.'
            elif self.dut['InternElectr'].lower() == '4ma':
                self.mpx.input = Inputs.I4mA
                instruction = '<p>Verbind de <b>DUT</b> Output met de <b>4mA Supply</b> input van de Multiplexer.'
            elif self.dut['InternElectr'].lower() == 'line drive':
                self.mpx.input = Inputs.LineDrive
                instruction = '<p>Verbind de <b>DUT</b> Output met de <b>Line Drive</b> input van de Multiplexer.'
            else:
                self.mpx.input = Inputs.Voltage
                instruction = '<p>Verbind de <b>DUT</b> Output met de <b>Voltage</b> input van de Multiplexer.'
        else:
            self.mpx.input = Inputs.Velocity
            self.mpx.velocity_load = VelocityLoads.L10k
            instruction = '<p>Verbind de <b>DUT</b> Output met de <b>Velocity</b> input van de Multiplexer.'

        rslt = self.instruction(instruction, self.dut['AansluitTip'])
        return rslt

    def calc_dut_freq_response(self):
        f = self.analyzer.freqs

        dut_response = self.analyzer.equalized_response * float(self.ref['Sens'])
        if self.dut['Group'].lower() == 'vel' or self.dut['TestParameter'].lower() == 'voltage':
            dut_response *= float(self.ref['AmpSens'])

        m_dut = self.dut['Weight']
        m_ref = self.ref['Weight']
        d_dut = self.dut['CouplingDiam']
        d_ref = self.ref['CouplingDiam']

        if self.dut['Shakertype'] == '4808':
            F1 = config.F1SH4808
            F2 = config.F2SH4808
        else:
            F1 = config.F1SH4809
            F2 = config.F2SH4809
            d_dut = min(d_dut, d_ref)

        if not d_dut or self.dut['Group'].lower() == 'vel':
            TC = 0
        else:
            TC = 1 - (m_dut / d_dut) / (m_ref / d_ref)

        corr = (1 - TC * (160 / F2) ** 2) * (1 - (160 / F1) ** 2) / ((1 - (f / F1) ** 2) * (1 - TC * (f / F2) ** 2))
        dut_response *= corr

        if self.dut['Group'].lower() == 'vel':
            dut_response *= 2 * np.pi * f

        return dut_response, f

    def calc_amp_freq_response(self):
        resp = self.analyzer.freq_response / config.C
        freqs = self.analyzer.freqs
        return resp, freqs

    def instruction(self, text, extratext=''):
        msgbox = QMessageBox(parent=self.parent)
        msgbox.setWindowTitle('Shake It')
        msgbox.setIcon(QMessageBox.Information)
        msgbox.setText(text)
        if extratext:
            msgbox.setInformativeText(extratext)
        msgbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        return msgbox.exec_()

    def error_message(self, text, extratext='', ignore_button=False):
        logger.critical(text)
        msgbox = QMessageBox(parent=self.parent)
        msgbox.setWindowTitle('Shake It')
        msgbox.setIcon(QMessageBox.Critical)
        msgbox.setText(text)
        if extratext:
            msgbox.setInformativeText(extratext)
        if ignore_button:
            msgbox.setStandardButtons(QMessageBox.Ok|QMessageBox.Ignore)
        else:
            msgbox.setStandardButtons(QMessageBox.Ok)
        return msgbox.exec_()

    def select_ref_specs_from_db(self, ref_acc):
        try:
            dbase = db.DB('./' + config.DB_FILENAME)
            return dbase.query('SELECT * FROM ref WHERE Name = ?', ref_acc)[0]
        except Exception as err:
            self.error_message('%s\n\n%s' % (self.db_error, err))
            exit(-1)

    def calc_full_response(self):
        fstep_lf = self.dut['freqs_lf'][2] - self.dut['freqs_lf'][1]
        fstep_hf = self.dut['freqs_hf'][2] - self.dut['freqs_hf'][1]

        # LF Limits
        self.dut['refsens'] = abs(self.dut['result_lf'][(int(self.dut['SensFreq'] / fstep_lf))])

        imin_lf = int(self.dut['Band1StartFreq'] // fstep_lf)
        imax_lf = int(config.FREQ_LIMIT_LF // fstep_lf)

        imaxlim1 = min(int(self.dut['Band1EndFreq']) // fstep_lf, imax_lf) + 1
        imaxlim2 = min(int(self.dut['Band2EndFreq']) // fstep_lf, imax_lf) + 1
        imaxlim3 = min(int(self.dut['Band3EndFreq']) // fstep_lf, imax_lf) + 1

        upper_limit_lf = np.zeros(imax_lf+1, dtype=np.float64)
        lower_limit_lf = np.zeros(imax_lf+1, dtype=np.float64)
        upper_limit_lf[0:int(imaxlim1)] = float(self.dut['Band1TolPlus'])
        lower_limit_lf[0:int(imaxlim1)] = - float(self.dut['Band1TolMin'])
        upper_limit_lf[int(imaxlim1):int(imaxlim2)] = float(self.dut['Band2TolPlus'])
        lower_limit_lf[int(imaxlim1):int(imaxlim2)] = - float(self.dut['Band2TolMin'])
        upper_limit_lf[int(imaxlim2):int(imaxlim3)] = float(self.dut['Band3TolPlus'])
        lower_limit_lf[int(imaxlim2):int(imaxlim3)] = - float(self.dut['Band3TolMin'])

        # HF Limits
        imaxlim1 = int(self.dut['Band1EndFreq']) // fstep_hf + 1
        imaxlim2 = int(self.dut['Band2EndFreq']) // fstep_hf + 1
        imaxlim3 = int(self.dut['Band3EndFreq']) // fstep_hf + 1

        imax_hf = int(self.dut['max_freq'] // fstep_hf)

        upper_limit_hf = np.zeros(imax_hf+1, dtype=np.float64)
        lower_limit_hf = np.zeros(imax_hf+1, dtype=np.float64)
        upper_limit_hf[0:int(imaxlim1)] = float(self.dut['Band1TolPlus'])
        lower_limit_hf[0:int(imaxlim1)] = - float(self.dut['Band1TolMin'])
        upper_limit_hf[int(imaxlim1):int(imaxlim2)] = float(self.dut['Band2TolPlus'])
        lower_limit_hf[int(imaxlim1):int(imaxlim2)] = - float(self.dut['Band2TolMin'])
        upper_limit_hf[int(imaxlim2):int(imaxlim3)] = float(self.dut['Band3TolPlus'])
        lower_limit_hf[int(imaxlim2):int(imaxlim3)] = - float(self.dut['Band3TolMin'])

        # LF Response
        lf_resp = self.dut['result_lf'][0:imax_lf+1]
        lf_freqs = self.dut['freqs_lf'][0:imax_lf+1]
        lf_upper_lim = upper_limit_lf[0:imax_lf+1]
        lf_lower_lim = lower_limit_lf[0:imax_lf+1]

        # HF Response
        imin_hf = int(config.FREQ_LIMIT_LF / fstep_hf) + 1
        hf_resp = self.dut['result_hf'][imin_hf:imax_hf+1]
        hf_freqs = self.dut['freqs_hf'][imin_hf:imax_hf+1]
        hf_upper_lim = upper_limit_hf[imin_hf:imax_hf+1]
        hf_lower_lim = lower_limit_hf[imin_hf:imax_hf+1]

        # LF response decimeren bij velocity transducers voor rustiger trace verloop
        if self.dut['Group'].lower() == 'vel':
            lf_resp = np.append(self.decimate(lf_resp[:800], 10), lf_resp[800])
            lf_freqs = [f for f in lf_freqs if (np.mod(f, 5)==0)]
            lf_upper_lim = [lf_upper_lim[n] for n, lim in enumerate(lf_upper_lim) if (np.mod(n, 10) == 0)]
            lf_lower_lim = [lf_lower_lim[n] for n, lim in enumerate(lf_lower_lim) if (np.mod(n, 10) == 0)]
            imin_lf = int(self.dut['Band1StartFreq'] // (10 * fstep_lf))
            self.dut['refsens'] = abs(lf_resp[(int(self.dut['SensFreq'] / (10*fstep_lf)))])

        # Full Response
        full_response = np.append(lf_resp, hf_resp)
        full_freqs = np.append(lf_freqs, hf_freqs)
        full_upper_lim = np.append(lf_upper_lim, hf_upper_lim)
        full_lower_lim = np.append(lf_lower_lim, hf_lower_lim)

        self.dut['result'] = abs(full_response)[imin_lf:]
        self.dut['freqs'] = full_freqs[imin_lf:]
        self.dut['upper_lim'] = full_upper_lim[imin_lf:]
        self.dut['lower_lim'] = full_lower_lim[imin_lf:]

        #jw
        np.savez('.\\full_resp.npz', resp=self.dut['result'], freqs=self.dut['freqs'])

    def calc_pass_fail(self):
        # Freq Response
        self.dut['failindex'] = []
        self.dut['freqresppassfail'] = 'Pass'
        for i, rslt in enumerate(self.dut['result']):
            if (100 * (rslt / self.dut['refsens'] - 1)) > self.dut['upper_lim'][i] or (100 * (rslt / self.dut['refsens'] - 1)) < self.dut['lower_lim'][i]:
                self.dut['failindex'].append(i)
                self.dut['freqresppassfail'] = 'Fail'

        # Ref Sens
        if float(self.dut['refsens']) > (float(self.dut['Sens']) + float(self.dut['SensTolPlus'])) \
                or float(self.dut['refsens']) < (float(self.dut['Sens']) - float(self.dut['SensTolMin'])):
            self.dut['refsenspassfail'] = 'Fail'
        else: self.dut['refsenspassfail'] = 'Pass'

    def stop(self):
        self.analyzer.stop_random_noise()
        self.stopped = True
        self.mpx.attenuator = -31
        # self.analyzer.abort()

    def decimate(self, x, n):
        return x.reshape(-1, n).mean(axis=1)

    def calc_limits_lf(self):
        fstep_lf = config.FSTEP_LF

        imax_lf = int(config.FREQ_LIMIT_LF // fstep_lf)

        imaxlim1 = min(int(self.dut['Band1EndFreq']) // fstep_lf, imax_lf) + 1
        imaxlim2 = min(int(self.dut['Band2EndFreq']) // fstep_lf, imax_lf) + 1
        imaxlim3 = min(int(self.dut['Band3EndFreq']) // fstep_lf, imax_lf) + 1

        upper_limit_lf = np.zeros(imax_lf+1, dtype=np.float64)
        lower_limit_lf = np.zeros(imax_lf+1, dtype=np.float64)
        upper_limit_lf[0:int(imaxlim1)] = float(self.dut['Band1TolPlus'])
        lower_limit_lf[0:int(imaxlim1)] = - float(self.dut['Band1TolMin'])
        upper_limit_lf[int(imaxlim1):int(imaxlim2)] = float(self.dut['Band2TolPlus'])
        lower_limit_lf[int(imaxlim1):int(imaxlim2)] = - float(self.dut['Band2TolMin'])
        upper_limit_lf[int(imaxlim2):int(imaxlim3)] = float(self.dut['Band3TolPlus'])
        lower_limit_lf[int(imaxlim2):int(imaxlim3)] = - float(self.dut['Band3TolMin'])

        return upper_limit_lf, lower_limit_lf

    def calc_limits_hf(self):
        fstep_hf = config.FSTEP_HF

        # HF Limits
        imaxlim1 = int(self.dut['Band1EndFreq']) // fstep_hf + 1
        imaxlim2 = int(self.dut['Band2EndFreq']) // fstep_hf + 1
        imaxlim3 = int(self.dut['Band3EndFreq']) // fstep_hf + 1

        imax_hf = int(self.dut['max_freq'] // fstep_hf)

        upper_limit_hf = np.zeros(imax_hf+1, dtype=np.float64)
        lower_limit_hf = np.zeros(imax_hf+1, dtype=np.float64)
        upper_limit_hf[0:int(imaxlim1)] = float(self.dut['Band1TolPlus'])
        lower_limit_hf[0:int(imaxlim1)] = - float(self.dut['Band1TolMin'])
        upper_limit_hf[int(imaxlim1):int(imaxlim2)] = float(self.dut['Band2TolPlus'])
        lower_limit_hf[int(imaxlim1):int(imaxlim2)] = - float(self.dut['Band2TolMin'])
        upper_limit_hf[int(imaxlim2):int(imaxlim3)] = float(self.dut['Band3TolPlus'])
        lower_limit_hf[int(imaxlim2):int(imaxlim3)] = - float(self.dut['Band3TolMin'])

        return upper_limit_hf, lower_limit_hf

    def calc_imin_imax_lf(self):
        fstep_lf = self.analyzer.freqs[2] - self.analyzer.freqs[1]
        return int(self.dut['min_freq'] // fstep_lf), int(config.FREQ_LIMIT_LF // fstep_lf)

    def calc_imin_imax_hf(self):
        fstep_hf = self.analyzer.freqs[2] - self.analyzer.freqs[1]
        return int(config.FREQ_LIMIT_LF // fstep_hf), int(self.dut['max_freq'] // fstep_hf)

    def calc_ref_freq_response(self):
        if self.dut['Shakertype'] == '4808':
            f1 = config.F1SH4808
            f2 = config.F2SH4808
            fw = config.FWSH4808
            ash = config.ASH4808
        else:
            f1 = config.F1SH4809
            f2 = config.F2SH4809
            fw = config.FWSH4809
            ash = config.ASH4809

        freq_resp = self.analyzer.freq_response
        f = self.analyzer.freqs
        f_ref = self.dut['SensFreq']
        # volgens boek
        norm_val = abs(freq_resp[int(f_ref) // self.analyzer.fstep])

        corr = np.exp(-ash * np.log(f / f_ref)) * (1 - (f_ref / fw)**2) * (1 - (f / f1)**2) * (1 - (f / f2)**2) / \
               (norm_val * (1 - (f / fw)**2) * (1 - (f_ref / f1)**2) * (1 - (f_ref / f2)**2))
        corr_resp = abs(freq_resp) * corr
        return corr_resp, f

    def update_spectrum_dialogs(self):
        upper_lim = lower_lim = None
        if self.resp_display == DisplayChoice.FreqRespAmpLF:
            self.resp_dlg.set_title('dut response LF')
            imin, imax = self.calc_imin_imax_lf()
            iref = int(self.dut['SensFreq'] / config.FSTEP_LF)
            r, f = self.calc_amp_freq_response()
            resp = 100 * (r[imin:imax+1] / r[iref] - 1)
            freqs = f[imin:imax+1]
            ul, ll = self.calc_limits_lf()
            upper_lim = ul[imin:imax+1]
            lower_lim = ll[imin:imax+1]
            self.resp_dlg.hide_total_range()
            self.display_sens()
        elif self.resp_display == DisplayChoice.FreqRespAmpHF:
            self.resp_dlg.set_title('dut response HF')
            imin, imax = self.calc_imin_imax_hf()
            iref = int(self.dut['SensFreq'] / config.FSTEP_HF)
            r, f = self.calc_amp_freq_response()
            resp = 100 * (r[imin:imax+1] / r[iref] - 1)
            freqs = f[imin:imax+1]
            ul, ll = self.calc_limits_hf()
            upper_lim = ul[imin:imax+1]
            lower_lim = ll[imin:imax+1]
            self.resp_dlg.hide_total_range()
            self.display_sens()
        elif self.resp_display == DisplayChoice.FreqRespRefLF:
            self.resp_dlg.set_title('ref response LF')
            if self.dut['Shakertype'] == '4808':
                start_freq = 5
            else:
                start_freq = 10
            imin = int(start_freq / self.analyzer.fstep)
            imax = int(config.FREQ_LIMIT_LF / self.analyzer.fstep)
            r, f = self.calc_ref_freq_response()
            resp = 100 * (r[imin:imax+1] - 1)
            freqs = f[imin:imax+1]
            upper_lim = np.full_like(freqs, config.REF_SPEC_TOL)
            lower_lim = np.full_like(freqs, - config.REF_SPEC_TOL)
            self.resp_dlg.hide_total_range()
            self.sens_dlg.hide()
        elif self.resp_display == DisplayChoice.FreqRespRefHF:
            self.resp_dlg.set_title('ref response HF')
            imin = int(config.FREQ_LIMIT_LF / self.analyzer.fstep)
            imax = int(self.analyzer.stop_freq / self.analyzer.fstep)
            r, f = self.calc_ref_freq_response()
            resp = 100 * (r[imin:imax+1] - 1)
            freqs = f[imin:imax+1]
            upper_lim = np.full_like(freqs, config.REF_SPEC_TOL)
            lower_lim = np.full_like(freqs, - config.REF_SPEC_TOL)
            self.resp_dlg.hide_total_range()
            self.sens_dlg.hide()
        elif self.resp_display == DisplayChoice.CoherenceLF:
            self.resp_dlg.set_title('coherence')
            imin, imax = self.calc_imin_imax_lf()
            freqs = self.analyzer.freqs[imin:imax+1]
            resp = self.analyzer.coherence[imin:imax+1]
            if self.dut['Group'].lower() == 'vel':
                limit = config.VEL_COHERENCE_TOL
            else:
                limit = config.ACC_COHERENCE_TOL
            upper_lim = np.full_like(freqs, 1+limit)
            lower_lim = np.full_like(freqs, 1-limit)
        elif self.resp_display == DisplayChoice.CoherenceHF:
            self.resp_dlg.set_title('coherence')
            imin, imax = self.calc_imin_imax_hf()
            freqs = self.analyzer.freqs[imin:imax+1]
            resp = self.analyzer.coherence[imin:imax+1]
            if self.dut['Group'].lower() == 'vel':
                limit = config.VEL_COHERENCE_TOL
            else:
                limit = config.ACC_COHERENCE_TOL
            upper_lim = np.full_like(freqs, 1+limit)
            lower_lim = np.full_like(freqs, 1-limit)
        elif self.resp_display == DisplayChoice.FreqRespDutLF:
            self.resp_dlg.set_title('dut response LF')
            imin, imax = self.calc_imin_imax_lf()
            iref = int(self.dut['SensFreq'] / config.FSTEP_LF)
            r, f = self.calc_dut_freq_response()
            resp = 100 * (r[imin:imax+1] / r[iref] - 1)
            freqs = f[imin:imax+1]
            ul, ll = self.calc_limits_lf()
            upper_lim = ul[imin:imax+1]
            lower_lim = ll[imin:imax+1]
            self.resp_dlg.hide_total_range()
            self.display_sens()
        elif self.resp_display == DisplayChoice.FreqRespDutHF:
            self.resp_dlg.set_title('dut response HF')
            imin, imax = self.calc_imin_imax_hf()
            iref = int(self.dut['SensFreq'] / config.FSTEP_HF)
            r, f = self.calc_dut_freq_response()
            resp = 100 * (r[imin:imax+1] / r[iref] - 1)
            freqs = f[imin:imax+1]
            ul, ll = self.calc_limits_hf()
            upper_lim = ul[imin:imax+1]
            lower_lim = ll[imin:imax+1]
            self.resp_dlg.hide_total_range()
            self.display_sens()
        elif self.resp_display == DisplayChoice.AutoSpectrumATotalLF:
            if self.dut['Shakertype'] == '4808':
                wstd = config.WSTD_SENS_4808
            else:
                wstd = config.WSTD_SENS_4809
            self.resp_dlg.set_title('auto spectrum LF')
            imin = 2
            imax = int(config.FREQ_LIMIT_LF / self.analyzer.fstep)
            freqs = self.analyzer.freqs[imin:imax+1]
            resp = np.sqrt(self.analyzer.spectrum_A[imin:imax+1] * self.analyzer.fstep) / (wstd*config.LINE_DRIVE_SENS)
            self.resp_dlg.set_total_range(1, self.analyzer.stop_freq)
            self.resp_dlg.hide_limits()
            self.sens_dlg.hide()
        elif self.resp_display == DisplayChoice.AutoSpectrumATotalHF:
            if self.dut['Shakertype'] == '4808':
                wstd = config.WSTD_SENS_4808
            else:
                wstd = config.WSTD_SENS_4809
            self.resp_dlg.set_title('auto spectrum HF')
            imin = 2
            imax = int(self.analyzer.stop_freq / self.analyzer.fstep)
            freqs = self.analyzer.freqs[imin:imax+1]
            resp = np.sqrt(self.analyzer.spectrum_A[imin:imax+1] * self.analyzer.fstep) / (wstd*config.LINE_DRIVE_SENS)
            self.resp_dlg.set_total_range(1, self.analyzer.stop_freq)
            self.resp_dlg.hide_limits()
            self.sens_dlg.hide()
        else:
            self.resp_dlg.set_title('freq response')
            freqs = self.analyzer.freqs[1:]
            resp = self.analyzer.freq_response[1:]

        if upper_lim is not None:
            self.resp_dlg.display_limits(freqs, upper_lim, lower_lim)
        self.resp_dlg.display_response(freqs, resp)

    def display_sens(self):
        if self.dut['Group'] == 'amp':
            resp, freqs = self.calc_amp_freq_response()
        else:
            resp, freqs = self.calc_dut_freq_response()
        fstep = freqs[2] - freqs[1]
        iref = int(self.dut['SensFreq'] / fstep)
        imin = iref - 1
        imax = iref + 1
        upper_lim = np.full_like(freqs, self.dut['Sens'] + self.dut['SensTolPlus'])
        lower_lim = np.full_like(freqs, self.dut['Sens'] - self.dut['SensTolMin'])
        self.sens_dlg.display_limits(freqs[imin:imax + 1], upper_lim[imin:imax + 1], lower_lim[imin:imax + 1])
        self.sens_dlg.display_response(freqs[imin:imax + 1], resp[imin:imax + 1])
        self.sens_dlg.show()

    # Error meldingen
    coherence_error = 'Coherence fail! Controleer de meetopstelling.'
    reference_error = 'Reference Check fail! Controleer de meetopstelling.'
    excitation_error = 'Fout tijdens instellen Excitation Level! Controleer de meetopstelling.'
    db_error = 'Database Error! Fout tijdens ophalen gegevens.'


class DisplayChoice(object):
    FreqResponse = 1
    CoherenceLF = 2
    CoherenceHF = 3
    FreqRespDutLF = 4
    FreqRespDutHF = 5
    FreqRespRefLF = 6
    FreqRespRefHF = 7
    AutoSpectrumATotalLF = 8
    AutoSpectrumATotalHF = 9
    FreqRespAmpLF = 10
    FreqRespAmpHF = 11
