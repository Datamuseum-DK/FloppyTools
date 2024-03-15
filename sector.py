#/usr/bin/env python3

'''
   A single data sector
   ~~~~~~~~~~~~~~~~~~~~
'''

class Sector():
    ''' A single sector, read by a Reading '''

    def __init__(self, chs, octets, good=True, source=""):
        assert len(chs) == 3
        self.chs = chs
        self.octets = octets
        self.good = good
        self.source = source

    def __str__(self):
        return str((self.chs, self.good, len(self.octets)))

    def __eq__(self, other):
        return self.octets == other.octets and self.good == other.good
