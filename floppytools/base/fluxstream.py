#/usr/bin/env python3

'''
   Base class for flux streams
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

def fm_gap(length):
    ''' Return a '0*length+1' FM gap string '''
    return '|---' * length + '|-|-'

def make_mark(clock, data, pad=""):
    ''' Interleave clock and data bits '''
    clock = bin(256|clock)[3:]
    data = bin(256|data)[3:]
    retval = []
    for i, j in zip(clock, data):
        if i == '1':
            retval.append('|' + pad)
        else:
            retval.append('-' + pad)
        if j == '1':
            retval.append('|' + pad)
        else:
            retval.append('-' + pad)
    return ''.join(retval)

def make_mark_fm(*args, **kwargs):
    ''' Interleave clock and data bits with FM modulation '''
    return make_mark(*args, **kwargs, pad="-")

def flux_data(flux, start=1, stride=1):
    ''' extract data bits every start + N * stride '''
    i = []
    for j in range(start, len(flux), stride):
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

class ClockRecovery():
    ''' Configurable adaptive Clock/Data separator '''

    # Hand tuned
    RATE = 80e-3

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

    def __init__(self, rate = 50):
        self.SPEC = {
            rate: "-|",
            rate*2: "---|",
        }

class ClockRecoveryMFM(ClockRecovery):
    ''' Classic MFM '''

    def __init__(self, rate = 50):
        self.SPEC = {
            rate:      "-|",
            3*rate//2: "--|",
            2*rate:    "---|",
        }

class ClockRecoveryM2FM(ClockRecovery):
    ''' Classic M2FM '''

    def __init__(self, rate=50):
        self.SPEC = {
            rate:      "-|",
            4*rate//2: "--|",
            2*rate:    "---|",
            5*rate//2: "----|",
        }

class FluxStream():
    ''' ... '''


    def __init__(self):
        self.config_histogram()
        self.fm_cache = {}
        self.mfm_cache = {}
        self.m2fm_cache = {}

    def serialize(self):
        return "-"

    def config_histogram(self, width=None, scale=None):
        if width is None:
            width = 80
        if scale is None:
            scale = 3
        self.histo = [0] * width
        self.histo_scale = scale

    def fm_flux(self, rate=50):
        ''' Return FM flux string '''
        if rate not in self.fm_cache:
            self.fm_cache[rate] = ClockRecoveryFM(rate).process(self.iter_dt())
        return self.fm_cache[rate]

    def mfm_flux(self, rate=50):
        ''' Return MFM flux string '''
        if rate not in self.mfm_cache:
            self.mfm_cache[rate] = ClockRecoveryMFM(rate).process(self.iter_dt())
        return self.mfm_cache[rate]

    def m2fm_flux(self, rate=50):
        ''' Return M2FM flux string '''
        if rate not in self.m2fm_cache:
            self.m2fm_cache[rate] = ClockRecoveryM2FM(rate).process(self.iter_dt())
        return self.m2fm_cache[rate]

    def flux_data_fm(self, flux):
        ''' Convert FM flux-string to data '''
        return flux_data(flux, 2, 4)

    def flux_data_mfm(self, flux):
        ''' Convert MFM flux-string to data '''
        return flux_data(flux, 1, 2)

    def iter_pattern(self, fm, gaplen=128, minlen=128, pattern=None):
        ''' Iterate through all gaps in fm-string '''
        off = 0
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

    def peak_dt(self, lo, hi):
        peak = 0
        dt = None
        for probe in range((lo // self.histo_scale), min(hi//self.histo_scale, len(self.histo)-2)):
            if self.histo[probe] > peak:
                peak = self.histo[probe]
                dt = probe * self.histo_scale
        return dt

class RawStream(FluxStream):
    ''' Raw stream file '''

    # As found in https://github.com/MattisLind/q1decode/tree/main/Q1DISKS
    # (CatWeasel ?)

    def __init__(self, filename):
        self.chs = (None, None, None)

        self.filename = filename
        self.histo = [0] * 80

    def __str__(self):
        return "<RawStream " + self.filename + ">"

    def __lt__(self, other):
        return self.filename < other.filename

    def iter_dt(self):
        for i in open(self.filename, "rb").read():
            i &= 0x7f
            dt = int(i * 2.5)
            self.histo[min(dt//3, 79)] += 1
            yield dt
