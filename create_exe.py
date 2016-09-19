from guidata import disthelpers as dh

def create_exe():
    dist = dh.Distribution()
    dist.setup('Trillingstation', '0.0.0.1', 'trillingstation', 'trilstation.pyw', icon='./icon.ico')
    dist.add_modules('guidata', 'guiqwt')
    dist.add_data_file('settings.ini')
    dist.add_data_file('Tril.mdb')
    dist.add_data_file('logo.png')
    dist.build_cx_freeze(packages='win32com.gen_py')  # guidata.disthelpers aangepast voor option packages

if __name__ == '__main__':
    create_exe()