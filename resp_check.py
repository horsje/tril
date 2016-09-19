import numpy as np
import matplotlib.pyplot as plt


spec = np.load('.\\coh_check.npz')
resp = spec['resp']

f = spec['freqs']

plt.semilogx(f, resp)

plt.show()