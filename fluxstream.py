#/usr/bin/env python3

'''
   Base class for flux streams
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

def fm_gap(length):
    ''' Return a '0*length+1' FM gap string '''
    return '|---' * length + '|-|-'

class ClockRecovery():
    ''' Configurable adaptive Clock/Data separator '''

    # Hand tuned
    RATE = 70e-3

    # Half a period on traditional 8" floppies
    LIMIT = 12.5

    SPEC = {
        50: "-|",
        100: "---|",
    }

    def process(self, iterator):
        ''' Generate flux-string '''
        b = []

        # Half the interval works best
        limit = self.LIMIT**2

        # Hand tuned
        rate = self.RATE

        th = [list(sorted(self.SPEC.keys()))] * len(self.SPEC)
        tokens = [y for x,y in sorted(self.SPEC.items())]
        thr = th[0]
        b = []
        for n, i in enumerate(iterator):
            j = [(i - x)**2 for x in thr]
            lo = min(j)
            for n, x in enumerate(thr):
                if j[n] != lo:
                    continue
                b.append(tokens[n])
                if j[n] < limit:
                    thr[n] += (i - thr[n]) * rate
                break
        return ''.join(b)

class ClockRecoveryFM(ClockRecovery):
    ''' Classic FM '''

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

    def iter_pattern(self, fm, gaplen=128, minlen=128, pattern=None):
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

    def iter_dt(self):
        if False:
            yield None
