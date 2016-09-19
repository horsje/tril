import config
import numpy as np
import matplotlib.pyplot as plt

f1 = 34e3
f2 = 55e3
fw = 39e3
ash = 0.008
min_line = int(10 / config.fstep_hf)

ref_spec = np.load('.\\ref_resp_check.npz')

freq_resp = ref_spec['resp']
f = ref_spec['freqs']
f_ref = 160
norm_val = abs(freq_resp[(int(f_ref) // config.fstep_hf)])
#norm_val = self.ref['Sens'] * self.ref['V_Unit_0,01'] * config.g / (wstd_sens * config.LINE_DRIVE_SENS * 1000)  #jw Checkt ook instelling cond. amp
print ('norm_val: ', norm_val)


# Zie blz. 109 Manual 9610
corr = np.exp(-ash * np.log(f / f_ref)) * (1 - (f_ref / fw)**2) * (1 - (f / f1)**2) * (1 - (f / f2)**2) / \
   (norm_val * (1 - (f / fw)**2) * (1 - (f_ref / f1)**2) * (1 - (f_ref / f2)**2))
corr_resp = abs(freq_resp) * corr

plt.plot(f, corr_resp)
#plt.ylim([.95, 1.05])
plt.xlim([0, 5000])
plt.show()