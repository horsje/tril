import numpy as np
import scipy.signal as signal
# import matplotlib.mlab as mlab
from PyQt4.QtCore import pyqtSignal, QObject
import ctypes
import config
import logging

logger = logging.getLogger('tril')

nidaq = ctypes.windll.nicaiu

int32 = ctypes.c_long
uInt32 = ctypes.c_ulong
uInt64 = ctypes.c_ulonglong
float64 = ctypes.c_double
TaskHandle = ctypes.c_int

DAQmx_Val_Cfg_Default = int32(-1)
DAQmx_Val_Volts = 10348
DAQmx_Val_Rising = 10280
DAQmx_Val_FiniteSamps = 10178
DAQmx_Val_GroupByChannel = 0
DAQmx_Val_GroupByScanNumber = 1
DAQmx_Val_Diff = 10106
DAQmx_Val_ZeroVolts = 12526
DAQmx_Val_ContSamps = 10123


def chk(err):
        if err < 0:
            buf_size = 100
            buf = ctypes.create_string_buffer(b'\000' * buf_size)
            nidaq.DAQmxGetErrorString(err, ctypes.byref(buf), buf_size)
            logger.critical('nidaq call failed: {}'.format(buf.value.decode()))
            raise IOError('nidaq call failed with error {}: {}'.format(err, buf.value.decode()))
        else:
            return 1


def analysis(y, x, NFFT=256, Fs=2, noverlap=0):
    freqs = np.fft.rfftfreq(NFFT, 1/Fs)[0:NFFT/2 + 1]
    nseg = int((len(x) - noverlap) / (NFFT - noverlap))
    window = np.hanning(NFFT)
    # Spectral Density
    norm = 0.5 * Fs * nseg * np.linalg.norm(window)**2
    # Spectral Power
    # norm = .5 * NFFT * nseg * np.linalg.norm(window)**2
    Gxy = np.zeros(NFFT/2+1, dtype=complex)
    Gxx = np.zeros(NFFT/2+1, dtype=complex)
    Gyy = np.zeros(NFFT/2+1, dtype=complex)
    for i in range(nseg):
        xw = window * x[i*(NFFT-noverlap):i*(NFFT-noverlap)+NFFT]
        yw = window * y[i*(NFFT-noverlap):i*(NFFT-noverlap)+NFFT]
        Xx = np.fft.rfft(xw, NFFT)
        Yy = np.fft.rfft(yw, NFFT)
        Gxy += Yy * np.conjugate(Xx)
        Gxx += Xx * np.conjugate(Xx)
        Gyy += Yy * np.conjugate(Yy)
    return Gxy / norm, abs(Gxx / norm), abs(Gyy / norm), freqs


class Analyzer(QObject):

    data_ready = pyqtSignal()
    avg_ready = pyqtSignal()

    def __init__(self, dev_name, start_freq=0, stop_freq=10e3, dut_input_range=10):
        QObject.__init__(self)
        self.dev_name = dev_name
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.dut_input_range = dut_input_range
        self.fs = config.SAMPLE_FREQ_HF
        self.nfft = config.N_FFT_HF
        self.navg = 1
        self.input_task = None
        self.output_task = None
        self.output_level = config.RANDOM_NOISE_LEVEL
        self.netfilter_enabled = config.NET_FILTER
        self.cross_spectrum = None
        self.spectrum_A = None
        self.spectrum_B = None
        self.freq_response = None
        self.coherence = None
        self.freqs = None
        self.stored_response = None
        self.excitation = None
        self.acq_ready = False
        self.error = None

        self.reset()

    def __del__(self):
        if self.input_task:
            chk(nidaq.DAQmxClearTask(self.input_task))
        if self.output_task:
            chk(nidaq.DAQmxClearTask(self.output_task))

    def reset(self):
        chk(nidaq.DAQmxResetDevice(bytes(self.dev_name, 'ascii')))
        self.acq_ready = False
        self.error = None

    @property
    def fstep(self):
        return self.fs / self.nfft

    def acquire_data(self):
        self.input_task = TaskHandle(0)
        read = int32()
        ns = self.nfft
        samples = np.zeros((ns, 2), dtype=np.float64)

        sum_x = 0
        sum_y = 0

        range_input0 = 1.0
        range_input1 = self.dut_input_range

        # t.b.v. threading
        self.acq_ready = False

        chk(nidaq.DAQmxCreateTask("", ctypes.byref(self.input_task)))
        chk(nidaq.DAQmxCreateAIVoltageChan(self.input_task, bytes(self.dev_name + "/ai0", 'ascii'), "", DAQmx_Val_Diff, float64(-range_input0),
                              float64(range_input0), DAQmx_Val_Volts, None))
        chk(nidaq.DAQmxCreateAIVoltageChan(self.input_task, bytes(self.dev_name + "/ai1", 'ascii'), "", DAQmx_Val_Diff, float64(-range_input1),
                               float64(range_input1), DAQmx_Val_Volts, None))
        chk(nidaq.DAQmxCfgSampClkTiming(self.input_task, "", float64(self.fs), DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, uInt64(int(self.navg) * ns)))
        chk(nidaq.DAQmxStartTask(self.input_task))

        for n in range(int(self.navg)):
            chk(nidaq.DAQmxReadAnalogF64(self.input_task, ns, float64(10), DAQmx_Val_GroupByScanNumber, samples.ctypes.data, 2*ns, ctypes.byref(read), None))

            x = samples[:, 0]
            y = samples[:, 1]

            sum_x = np.append(sum_x, x)
            sum_y = np.append(sum_y, y)

            nov = config.N_OVERLAP * self.nfft

            self.cross_spectrum, self.spectrum_A, self.spectrum_B, self.freqs = analysis(sum_y, sum_x, NFFT=self.nfft, Fs=self.fs, noverlap=nov)

            # self.cross_spectrum, f = mlab.csd(sum_y, sum_x, NFFT=self.nfft, Fs=self.fs, noverlap=nov)
            # self.spectrum_A, f = mlab.psd(sum_x, NFFT=self.nfft, Fs=self.fs, noverlap=nov)
            # self.spectrum_B, f = mlab.psd(sum_y, NFFT=self.nfft, Fs=self.fs, noverlap=nov)
            #
            # self.freqs = f

            self.freq_response = abs(self.cross_spectrum / self.spectrum_A)
            self.coherence = abs(self.cross_spectrum) ** 2 / (self.spectrum_A * self.spectrum_B)

            if self.netfilter_enabled:
                self.freq_response = self.net_filter(self.freq_response)
                self.coherence = self.net_filter(self.coherence)

            if (self.fs > self.nfft) and (n % 4 != 0):
                pass
            else:
                self.data_ready.emit()



        chk(nidaq.DAQmxStopTask(self.input_task))
        chk(nidaq.DAQmxClearTask(self.input_task))
        self.input_task.value = 0

        self.acq_ready = True
        self.avg_ready.emit()

    @property
    def freqs(self):
        if not self.error:
            return self._freqs
        else:
            raise IOError(self.error)

    @freqs.setter
    def freqs(self, value):
        self._freqs = value

    @property
    def freq_response(self):
        if not self.error:
            return self._freq_response
        else:
            raise IOError(self.error)

    @freq_response.setter
    def freq_response(self, value):
        self._freq_response = value

    @property
    def coherence(self):
        if not self.error:
            return self._coherence
        else:
            raise IOError(self.error)

    @coherence.setter
    def coherence(self, value):
        self._coherence = value

    def start_random_noise(self):
        ns = int(self.navg * self.nfft)
        # Noise
        noise_rms = self.output_level
        noise = np.random.normal(scale=noise_rms, size=ns) 

        # Lowpass Filter
        wn = 2 * self.stop_freq / self.fs
        b, a = signal.butter(4, wn)
        filtered = signal.lfilter(b, a, noise)
        filtered = np.clip(filtered, -4 * noise_rms, 4 * noise_rms)   # 4 * std_dev

        # Output
        self.output_task = TaskHandle(0)
        written = int32()
        chk(nidaq.DAQmxCreateTask("", ctypes.byref(self.output_task)))
        chk(nidaq.DAQmxCreateAOVoltageChan(self.output_task, bytes(self.dev_name + "/ao0", 'ascii'), "", float64(-4.0), float64(4.0), DAQmx_Val_Volts, None))
        chk(nidaq.DAQmxCfgSampClkTiming(self.output_task, "", float64(self.fs), DAQmx_Val_Rising, DAQmx_Val_ContSamps, uInt64(ns)))
        chk(nidaq.DAQmxWriteAnalogF64(self.output_task, int32(ns), 0, float64(10), DAQmx_Val_GroupByChannel, filtered.ctypes.data, ctypes.byref(written), None))
        chk(nidaq.DAQmxSetAOIdleOutputBehavior(self.output_task,  bytes(self.dev_name + "/ao0", 'ascii'), DAQmx_Val_ZeroVolts))
        chk(nidaq.DAQmxStartTask(self.output_task))

    def stop_random_noise(self):
        if self.output_task:
            chk(nidaq.DAQmxStopTask(self.output_task))
            chk(nidaq.DAQmxClearTask(self.output_task))
            self.output_task.value = 0

    def calc_total_value(self, input=0):
        if not self.error:
            #jw
            imax = int(self.stop_freq // self.fstep)
            # total = 0
            # for i in range(2, imax):
            #     if input == 0:
            #         total += self.spectrum_A[i] * self.fstep
            #     else:
            #         total += self.spectrum_B[i] * self.fstep
            total = np.sum(self.spectrum_A[2:] * self.fstep)
            return np.sqrt(total)
        else:
            raise IOError(self.error)

    @property
    def equalized_response(self):
        return self.freq_response / self.stored_response

    def net_filter(self, data):
        max_line = int(self.stop_freq // self.fstep)
        hum_line = int(50 // self.fstep)
        for i in range(1, max_line):
            if i % hum_line == 0:
                mean = (data[i-2] + data[i+2]) / 2
                data[i-1] = (data[i-2] + mean) / 2
                data[i] = mean
                data[i+1] = (data[i+2] + mean) / 2
        return data


if __name__ == '__main__':
    try:
        analyzer = Analyzer(dev_name=config.DAQ_DEVNAME)
        analyzer.start_random_noise()
        analyzer.acquire_data()
        analyzer.stop_random_noise()
    except IOError as err:
        print('IOError: %s' % err)
