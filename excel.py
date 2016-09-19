import win32com.client
import numpy as np

xl = win32com.client.DispatchEx('Excel.Application')
xl.Visible = True
xl.Workbooks.Add()
xl.DisplayAlerts = False

a=np.arange(10).reshape((10,1))
xl.Range('A1', 'A10').Value = a

raw_input('Druk op Enter')
xl.Quit()