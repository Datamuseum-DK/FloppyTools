#/usr/bin/env python3

'''
   Base class for flux streams
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

class FluxStream():
    ''' ... '''

    def make_mark(self, clock, data):
        clock = bin(256|clock)[3:]
        data = bin(256|data)[3:]
        retval = []
        for i, j in zip(clock, data):
            if i == '1':
                retval.append('|-')
            else:
                retval.append('--')
            if j == '1':
                retval.append('|-')
            else:
                retval.append('--')
        return ''.join(retval)

    def to_fm_250(self):
        ''' Decode as 250 kHz FM '''
        b = []
        for i in self.iter_dt():
            if 75 <= i <= 125:
                b.append('--')
            elif 25 <= i <= 75:
                b.append('#')
            else:
                b.append(' ')
        return ''.join(b)

    def flux_250_fm(self):
        ''' Generate FM flux-strig '''
        b = []
        pll = 1.00
        for i in self.iter_dt():
            j = i * pll
            if 75 <= j <= 125:
                delta = j - 100
                b.append('---|')
            elif 26 <= j <= 74:
                delta = j - 50
                b.append('-|')
            else:
                delta = 0
                b.append(' ')
            pll -= delta * 1e-6
        return ''.join(b)

    def flux_250_mfm(self):
        ''' Generate MFM flux-strig '''
        b = []
        pll = 1.00
        for n, i in enumerate(self.iter_dt()):
            j = i * pll
            if 88 <= j <= 112:
                delta = j - 100
                b.append('---|')
            elif 63 <= j <= 87:
                delta = j - 75
                b.append('--|')
            elif 38 <= j <= 62:
                delta = j - 50
                b.append('-|')
            else:
                delta = 0
                b.append(' ')
            pll -= delta * 1e-6
        return ''.join(b)

    def flux_data_fm(self, flux):
        ''' Convert FM flux-string to data '''
        i = []
        for j in range(2, len(flux), 4):
            i.append(flux[j])
        i = ''.join(i)
        i = i.replace('|', '1')
        i = i.replace('-', '0')
        if ' ' in i:
            return None
        j = []
        for k in range(0, len(i), 8):
            j.append(int(i[k:k+8], 2))
        return bytes(j)

    def flux_data_mfm(self, flux):
        ''' Convert MFM flux-string to data '''
        i = []
        for j in range(1, len(flux), 2):
            i.append(flux[j])
        i = ''.join(i)
        i = i.replace('|', '1')
        i = i.replace('-', '0')
        if ' ' in i:
            return None
        j = []
        for k in range(0, len(i), 8):
            j.append(int(i[k:k+8], 2))
        return bytes(j)

    def iter_pattern(self, fm, gaplen=128, minlen=128, pattern=None, gap=None):
        ''' Iterate through all gaps in fm-string '''
        off = 0
        if pattern is None:
            pattern = gap
        if pattern is None:
            pattern = '--' * gaplen + "##"
        minlen *= 16 + len(pattern)
        while True:
            nxt = fm.find(pattern, off)
            if nxt < 0 or len(fm) - nxt < minlen:
                return
            yield nxt + len(pattern)
            off = nxt + 1

    def iter_gaps(self, *args, **kwargs):
        yield from self.iter_pattern(*args, **kwargs)

    def iter_dt(self):
        if False:
            yield None
