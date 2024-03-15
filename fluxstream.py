#/usr/bin/env python3

'''
   Base class for flux streams
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

class FluxStream():
    ''' ... '''

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

    def iter_gaps(self, fm, gaplen=128, minlen=128):
        ''' Iterate through all gaps in fm-string '''
        off = 0
        gap = '--' * gaplen + "##"
        minlen *= 16 + len(gap)
        while True:
            nxt = fm.find(gap, off)
            if nxt < 0 or len(fm) - nxt < minlen:
                return
            yield nxt + len(gap)
            off = nxt + 1

    def iter_dt(self):
        if False:
            yield None
