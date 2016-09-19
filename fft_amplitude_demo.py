from matplotlib.mlab import window_none
import numpy as np
from scipy import signal, interpolate
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab


def picket_fence_corr(val):
    x = np.array([0,1,2,3,4,5,6])
    y = np.array([1.42, 0.97, 0.61, 0.33, 0.14, 0.04, 0])
    interp = interpolate.interp1d(x, y)
    if val <0 or val > 6:
        return 0
    else:
        return interp(val)


fs = 25.6e3; fc = 100; nfft = 2560

t = np.arange(0, 60, 1/fs)
y = np.cos(2*np.pi*fc*t) + 0.001*np.cos(2*np.pi*4*fc*t) + np.cos(2*np.pi*40.13*fc*t)
y += np.random.normal(scale=0.001, size=len(t))

p, f = mlab.psd(y, NFFT=nfft, Fs=fs, noverlap=nfft*0.75)
fstep = f[2]-f[1]

# Correctie voor hanning window
p *= 1.5 * fstep

p = 10 * np.log10(p)

# Picket Fence correctie
new_p = np.zeros(1 + nfft/2)
for i, j in enumerate(p):
    if i == 0 or i == nfft/2:
        new_p[i] = j
    else:
        max1 = max(p[i], p[i-1])
        max2 = max(p[i-1], p[i+1])
        diff = abs(max1 - max2)
        new_p[i] = j + picket_fence_corr(diff)


plt.plot(f, new_p, 'b-')
plt.show()
