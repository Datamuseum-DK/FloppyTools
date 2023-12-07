
import sys

class ReadSector():
    ''' A sector read by a Reading '''

    def __init__(self, cyl_no, hd_no, sect_no, octets, good):
        self.cyl_no = cyl_no
        self.hd_no = hd_no
        self.sect_no = sect_no
        self.key = (cyl_no, hd_no, sect_no)
        self.octets = octets
        self.good = good
        self.reading = None

    def __str__(self):
        return str((self.key, self.good))

    def __eq__(self, other):
        return self.octets == other.octets and self.good == other.good

class Reading():
    ''' A reading of a physical floppy '''

    def __init__(self, floppy, pathname=None):
        self.floppy = floppy
        self.pathname = pathname
        self.sectors = {}
        floppy.add_reading(self)

    def read_sector(self, sector):
        ''' A sector has been read '''
        sector.reading = self
        i = self.sectors.get(sector.key)
        if i:
             i.append(sector)
        else:
             self.sectors[sector.key] = [ sector ]
        self.floppy.read_sector(sector)

class Floppy():
    ''' A physical floppy disk '''

    sect0 = 1

    def __init__(self, cyl_no=None, hd_no=None, sect_no=None):
        self.cyl_no = cyl_no
        self.hd_no = hd_no
        self.sect_no = sect_no
        self.sectors = {}
        self.readings = []
        self.stats = {}

    def add_reading(self, reading):
        self.readings.append(reading)

    def read_sector(self, sector):
        i = self.sectors.get(sector.key)
        if i:
             i.append(sector)
        else:
             self.sectors[sector.key] = [ sector ]

    def hasgood(self, cyl, hd, sect):
        retval = '-'
        isgood = None
        ngood = 0
        for sr in self.sectors.get((cyl, hd, sect + self.sect0), []):
            if not sr.good:
                if retval == '-':
                    retval = 'b'
                continue
            if retval == '-':
                retval = '+'
            if isgood is None:
                isgood = sr
            if sr != isgood:
                print("SR0", sr.key, sr.octets)
                print("SR1", isgood.key, isgood.octets)
                return "d"
            else:
                ngood += 1
        if retval == '+' and ngood > 9:
            return "#"
        if retval == '+':
            return "%d" % ngood
        return retval

    def getgood(self, cyl, hd, sect):
        isgood = None
        for sr in self.sectors.get((cyl, hd, sect + self.sect0), []):
            if sr.good and isgood is None:
                isgood = sr
            if sr.good and sr != isgood:
                return None
        return isgood

    def badsects(self):
        for cyl in range(self.cyl_no):
            for hd in range(self.hd_no):
                for sect in range(self.sect_no):
                    i = self.hasgood(cyl, hd, sect)
                    if i in 'd-':
                        yield i, (cyl, hd, sect + self.sect0)

    def status(self, dst=None, just_summary=False):
        if dst is None:
            dst = sys.stdout
        self.stats = {}
        for cyl in range(self.cyl_no):
            for hd in range(self.hd_no):
                t = ""
                for sect in range(self.sect_no):
                    i = self.hasgood(cyl, hd, sect)
                    j = self.stats.get(i, 0)
                    self.stats[i] = j + 1
                    t += i
                miss = len(t.replace("+", ""))
                if not just_summary:
                    dst.write("%03d %2d %s /%2d\n" % (cyl, hd, t, miss))
        total = 0
        for i, j in sorted(self.stats.items()):
            total += j
            dst.write("'%s' %4d\n" % (i, j))
        
        dst.write("Tot %4d\n" % total)

    def missing(self, dst=None):
        if dst is None:
            dst = sys.stdout
        for cyl in range(self.cyl_no):
            for hd in range(self.hd_no):
                for sect in range(self.sect_no):
                    i = self.hasgood(cyl, hd, sect)
                    if i == '+':
                        continue
                    dst.write("  %2d %2d %2d %c\n" % (cyl, hd, sect, i))

    def write_bin(self, dstfn, secsize=128):
        filler = bytes(b'_UNREAD_' * (secsize // 8))
        bogus = bytes(b'_BOGUS__' * (secsize // 8))
        with open(dstfn, "wb") as file:
            for cyl in range(self.cyl_no):
                for hd in range(self.hd_no):
                    for sect in range(self.sect_no):
                        sr = self.getgood(cyl, hd, sect)
                        if sr is None:
                            file.write(filler)
                        elif sr.octets is None or len(sr.octets) != secsize:
                            file.write(bogus)
                        else:
                            file.write(sr.octets)
