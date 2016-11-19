import pyodbc
import os
import db


def db_query(query):
    dbase = db.DB('./' + DB_FILENAME)
    return dbase.query(query)


# PXI Devices
DAQ_DEVNAME = 'PXI4461'

# GPIB Devices
# MULTIPLEXER_ADDDRESS = 'GPIB0::7::INSTR'
MULTIPLEXER_ADDDRESS = 'ASRL4'

# Shakers
F1SH4808 = 34e3
F2SH4808 = 55e3
FWSH4808 = 39e3
ASH4808 = 0.008

F1SH4809 = 34e3
F2SH4809 = 74e3
FWSH4809 = 36e3
ASH4809 = 0

# Settings
SETTINGS_FILE = './/settings.ini'

# Wachtwoord
WACHTWOORD = 'Shake'

# Database
DB_FILENAME = 'Tril.mdb'

# DAQ
SAMPLE_FREQ_HF = 25.6E3
SAMPLE_FREQ_LF = 2.56E3
N_FFT_HF = 2560
N_FFT_LF = 5120
FSTEP_LF = SAMPLE_FREQ_LF / N_FFT_LF
FSTEP_HF = SAMPLE_FREQ_HF / N_FFT_HF
FREQ_LIMIT_LF = 400
N_OVERLAP = 0.75
NET_FILTER = True
RANDOM_NOISE_LEVEL = 1.
AVG_ACQ_LF = 32
AVG_ACQ_HF = 96
AVG_LEV = 3

# Constants
g = 9.81

# Excitation Level
G_LEVEL = 2.0
G_LEVEL_TOL = 0.2
MIN_G_LEVEL = 0.1
MAX_G_LEVEL = 3.0
MAX_ATT_SETTING_4808 = 1
MAX_ATT_SETTING_4809 = -5

# Working Std Sensitivity (pC/g)
WSTD_SENS_4808 = g * db_query("SELECT * FROM ref WHERE Name = 'Wstd'")[0]['Sens']
WSTD_SENS_4809 = g * db_query("SELECT * FROM ref WHERE Name = 'Ref2'")[0]['Sens']

# 2661 Line Driver Sens (V)
LINE_DRIVE_SENS = 1e-3

# Coherence
ACC_COHERENCE_TOL = 0.02
VEL_COHERENCE_TOL = 0.05
COHERENCE_LINE_SKIP = 0.025

# Ref Opnemer
REF_ACC = 'Ref1'
REF_SPEC_TOL = 3.0                          # %
REF_SPEC_PATH = '.\\Ref'
REF_VALID_TIME = 10                        # uur

# Excel rapport
PATH = os.path.abspath(__file__)
DIR = os.path.dirname(PATH)
EXCEL_REPORT_FILE = os.path.join(DIR, 'Kalibratiesjabloon', 'Voorblad_Teststation.xlsm')
STATION = 'Trilstation'
STD_FREQS = [5, 10, 15, 30, 50, 100, 160, 300, 400, 500, 600, 800, 1000]
[STD_FREQS.append(i) for i in range(1500, 20500, 500)]

# Versie
VERSION = '3.1.1'

# Van m/s naar inch per second
MS_TO_IPS = 0.0254

#TEDS
TEDS_PATH = r'D:\TEDS'

# Standard Capacitor (nF)
C = db_query("SELECT * FROM capacitor")[0]['Capacitance']
