import win32com.client
import win32gui
import config
from utilities import round_sig


class ExcelReport:
    def __init__(self, dut):
        xl = win32com.client.gencache.EnsureDispatch('Excel.Application')
        xl.Visible = True
        c = win32com.client.constants
        xl.DisplayAlerts = False

        # Excel op voorgrond
        handle = win32gui.FindWindow('XLMAIN', None)
        win32gui.SetForegroundWindow(handle)

        # Voorblad
        xl.Workbooks.Open(config.EXCEL_REPORT_FILE)
        workbook = xl.ActiveWorkbook
        xl.Sheets('voorblad').Range('kalnr').Value = str(dut['kalnummer'])
        xl.Sheets('voorblad').Range('nen3140resultaat').Value = 'N.V.T.'
        xl.Sheets('voorblad').Range('softwarerev').Value = config.VERSION
        xl.Sheets('voorblad').Range('type1').Value = config.STATION
        xl.Sheets('voorblad').OLEObjects("OptionButton1").Object.Value = True

        if dut['refsenspassfail'] == 'Pass' and dut['freqresppassfail'] == 'Pass':
            rslt = 'PASS'
        else:
            rslt = 'FAIL'
        xl.Sheets('voorblad').Range('resultaat').Value = rslt

        xl.ActiveWindow.Activate()
        xl.WindowState = c.xlMaximized

        # Resultaten
        rsltSheet = workbook.Worksheets.Add(After = workbook.Worksheets[workbook.Worksheets.Count])
        rsltSheet.Name = 'resultaten'
        rsltSheet.Columns('A:A').ColumnWidth = 2
        rsltSheet.Columns('B:B').ColumnWidth = 14

        xl.ActiveWindow.DisplayGridlines = False

        freq = dut['freqs']
        freq = freq.reshape((len(freq), 1))

        result = 100 * (abs(dut['result'] / dut['refsens']) - 1)
        result = result.reshape((len(result), 1))

        upperLim = dut['upper_lim']
        upperLim = upperLim.reshape((len(upperLim), 1))

        lowerLim = dut['lower_lim']
        lowerLim = lowerLim.reshape((len(lowerLim), 1))

        rsltSheet.Range('K1', 'K%s' % len(freq)).Value = freq.tolist()
        rsltSheet.Range('L1', 'L%s' % len(result)).Value = result.tolist()
        rsltSheet.Range('M1', 'M%s' % len(lowerLim)).Value = lowerLim.tolist()
        rsltSheet.Range('N1', 'N%s' % len(upperLim)).Value = upperLim.tolist()

        rsltSheet.Columns('K:N').Hidden = True

        rsltSheet.Range('B1').Value = 'Ref. Sensitivity @ %.f Hz:' % dut['SensFreq']
        rsltSheet.Range('D1').Value, num_dec = round_sig(abs(dut['refsens']), 4)
        if num_dec:
            rsltSheet.Range('D1').NumberFormat = '0,' + num_dec * '0'
        else:
            rsltSheet.Range('D1').NumberFormat = '0'
        rsltSheet.Range('E1').Value = dut['sensunit']
        if dut['refsenspassfail'] == 'Pass':
            rsltSheet.Range('G1').Value = 'Pass'
            rsltSheet.Range('G1').Font.ColorIndex = 10
        else:
            rsltSheet.Range('G1').Value = 'Fail'
            rsltSheet.Range('G1').Font.ColorIndex = 3

        if dut['IPS']:
            rsltSheet.Range('D2').Value, num_dec = round_sig(abs(config.MS_TO_IPS * dut['refsens']), 4)
            rsltSheet.Range('E2').Value = 'mV/(ips)'

        rsltSheet.Range('B3').Value = 'Freq. Response:'
        if dut['freqresppassfail'] == 'Pass':
            rsltSheet.Range('G3').Value = 'Pass'
            rsltSheet.Range('G3').Font.ColorIndex = 10
        else:
            rsltSheet.Range('G3').Value = 'Fail'
            rsltSheet.Range('G3').Font.ColorIndex = 3
        rsltSheet.Range('B1:B3').Font.Bold = True

        tblHeader = xl.ActiveSheet.Range('C20:D20')
        tblHeader.Value = ('Freq [Hz]', ('Sensitivity [%s]' % dut['sensunit']))
        tblHeader.Font.Bold = True
        tblHeader.Font.Underline = c.xlUnderlineStyleSingle
        tblHeader.HorizontalAlignment = c.xlRight
        tblHeader.EntireColumn.AutoFit()
        rsltSheet.Range('C21').Select()
        stdFreqs = config.STD_FREQS
        for i, f in enumerate(dut['freqs']):
            if f in stdFreqs:
                xl.ActiveCell.Value = float(f)
                rslt = xl.ActiveCell.GetOffset(0, 1)
                rslt.Value, num_dec = round_sig(abs(dut['result'][i]), 4)
                if num_dec:
                    rslt.NumberFormat = '0,' + num_dec * '0'
                else:
                    rslt.NumberFormat = '0'
                if i in dut['failindex']:
                    xl.ActiveCell.GetOffset(0, 4).Value = 'Fail'
                    xl.ActiveCell.GetOffset(0, 4).Font.ColorIndex = 3
                xl.ActiveCell.GetOffset(1, 0).Activate()

        rsltSheet.Shapes.AddChart(c.xlXYScatterLinesNoMarkers, 0, 50, 430, 170).Select()
        chart = xl.ActiveChart
        # chart.Parent.RoundedCorners = True
        chart.HasLegend = False
        chart.PlotVisibleOnly = False
        chart.Axes(c.xlCategory).HasTitle = True
        chart.Axes(c.xlCategory).AxisTitle.Text = 'freq [Hz]'
        chart.Axes(c.xlCategory).AxisTitle.Font.Bold = False
        chart.Axes(c.xlCategory).HasMinorGridlines = True
        chart.Axes(c.xlValue).HasTitle = True
        chart.Axes(c.xlValue).AxisTitle.Text = 'relative sensitivity [%]'
        chart.Axes(c.xlValue).AxisTitle.Font.Bold = False
        chart.Axes(c.xlCategory).ScaleType = c.xlLogarithmic
        chart.Axes(c.xlCategory).MinimumScale = float(freq[0, 0])
        chart.Axes(c.xlCategory).MaximumScale = float(freq[len(freq)-1, 0])
        # ymax = max([float(dut['Band1TolPlus']), float(dut['Band2TolPlus']), float(dut['Band3TolPlus'])])
        # chart.Axes(c.xlValue).MinimumScale = - ymax
        # chart.Axes(c.xlValue).MaximumScale = ymax
        chart.Axes(c.xlValue).CrossesAt = -100
        chart.ChartArea.Border.LineStyle = c.xlLineStyleNone

        for serie in chart.SeriesCollection():
            serie.Delete()

        resultSerie = chart.SeriesCollection().NewSeries()
        resultSerie.Name = 'sensitivity'
        resultSerie.XValues = xl.Sheets('resultaten').Range('K1', 'K%s'% len(freq))
        resultSerie.Values = xl.Sheets('resultaten').Range('L1', 'L%s'% len(freq))
        resultSerie.Format.Line.Weight = 1
        resultSerie.Border.ColorIndex = 5

        upperLimitSerie = chart.SeriesCollection().NewSeries()
        upperLimitSerie.Name = 'UpperLimit'
        upperLimitSerie.XValues = xl.Sheets('resultaten').Range('K1', 'K%s'% len(freq))
        upperLimitSerie.Values = xl.Sheets('resultaten').Range('M1', 'M%s'% len(freq))
        upperLimitSerie.Format.Line.Weight = 1
        upperLimitSerie.Border.ColorIndex = 3

        lowerLimitSerie = chart.SeriesCollection().NewSeries()
        lowerLimitSerie.Name = 'LowerLimit'
        lowerLimitSerie.XValues = xl.Sheets('resultaten').Range('K1', 'K%s'% len(freq))
        lowerLimitSerie.Values = xl.Sheets('resultaten').Range('N1', 'N%s'% len(freq))
        lowerLimitSerie.Format.Line.Weight = 1
        lowerLimitSerie.Border.ColorIndex = 3

        rsltSheet.Range('C5').Select()


if __name__ == '__main__':
    import numpy as np
    dut = {'freqs': np.arange(1, 2501), 'result': 10.0 + 1*(np.random.sample(2501) - 0.5), 'upper_lim': 10*np.ones(2501),
           'lower_lim': -10*np.ones(2501), 'refsens': 10.0, 'sensunit': u'mV/(m/s\u00B2)', 'SensFreq': 160.00,
           'refsenspassfail': 'Pass', 'freqresppassfail': 'Pass', 'failindex': [], 'kalnummer': 219427, 'IPS': False}
    xl = ExcelReport(dut)




