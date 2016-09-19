from PyQt4 import QtCore, QtGui, uic
from guiqwt.builder import make

form_class, base_class = uic.loadUiType('response.ui')


class ResponseDlg(base_class, form_class):

    def __init__(self, *args):
        super(ResponseDlg, self).__init__(*args)

        self.setupUi(self)

        self.plotWidget.plot.set_axis_limits('left', 0, 2)
        self.plotWidget.plot.set_axis_limits('bottom', 1, 400)
        self.plotWidget.plot.set_axis_title('bottom', 'freq [Hz]')
        self.plotWidget.plot.set_axis_scale('bottom', 'log')
        self.plotWidget.register_all_curve_tools()

        self.resultTrace = make.curve([], [], 'Spectrum', color='b')
        self.plotWidget.plot.add_item(self.resultTrace)
        self.upper_limit = make.curve([], [], 'UL', color='r')
        self.plotWidget.plot.add_item(self.upper_limit)
        self.lower_limit = make.curve([], [], 'LL', color='r')
        self.plotWidget.plot.add_item(self.lower_limit)

        self.rng = make.range(0, 0)
        self.math = make.computations(self.rng, "TR",
                             [(self.resultTrace, "total=%.2f", lambda x, y: (y**2).sum()**.5)])
        self.plotWidget.plot.add_item(self.rng)
        self.plotWidget.plot.add_item(self.math)
        self.hide_total_range()

    def display_limits(self, freqs, upper, lower):
        self.upper_limit.set_data(freqs, upper)
        self.lower_limit.set_data(freqs, lower)
        self.plotWidget.plot.show_items([self.upper_limit, self.lower_limit])

    def display_response(self, freqs, response):
        self.resultTrace.set_data(freqs, response)
        self.plotWidget.plot.set_axis_scale('left', 'lin', autoscale=True)
        self.plotWidget.plot.replot()

    def set_title(self, value):
        self.plotWidget.plot.set_axis_title('left', value)

    def set_freq_axis(self, start, stop):
        self.plotWidget.plot.set_axis_limits('bottom', start, stop)

    def set_total_range(self, start, stop):
        # if not self.rng:
        #     self.rng = make.range(start, stop)
        #     self.math = make.computations(self.rng, "TR",
        #                          [(self.resultTrace, "total=%.2f", lambda x, y: (y**2).sum()**.5)])
        #     self.plotWidget.plot.add_item(self.rng)
        #     self.plotWidget.plot.add_item(self.math)
        self.rng.set_range(start, stop)
        self.plotWidget.plot.show_items([self.rng, self.math])

    def hide_limits(self):
        self.plotWidget.plot.hide_items([self.upper_limit, self.lower_limit])

    def show_limits(self):
        self.plotWidget.plot.show_items([self.upper_limit, self.lower_limit])

    def hide_total_range(self):
        self.plotWidget.plot.hide_items([self.rng, self.math])



