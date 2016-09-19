from math import log10, floor


def round_sig(x, sig=2):
    n = sig-int(floor(log10(x)))-1
    return '{number:.{dec}f}'.format(number=x, dec=n), n
