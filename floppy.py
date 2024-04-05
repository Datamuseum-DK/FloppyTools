
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

class FloppySector():
    ''' A sector on the floppy '''

    def __init__(self, floppy, chs):
        self.floppy = floppy
        self.chs = chs
        self.bad_readings = []
        self.good_readings = []
        self.vals = {}

    def add_reading(self, readsect):
        if not readsect.good:
            self.bad_readings.append(readsect)
            return
        self.good_readings.append(readsect)
        b = bytes(readsect.octets)
        if not b in self.vals:
            self.vals[b] = []
        self.vals[b].append(readsect)

    def __repr__(self):
        i, j = self.negotiate()
        return i

    def data(self):
        i, j = self.negotiate()
        return j

    def negotiate(self):
        if not self.good_readings and self.bad_readings:
            return 'b', None
        if not self.good_readings:
            return '-', None
        if len(self.vals) == 1 and len(self.good_readings) > 9:
            return '#', self.good_readings[0].octets
        if len(self.vals) == 1:
            return '%d' % len(self.good_readings), self.good_readings[0].octets
        i = [(len(x),y) for y,x in self.vals.items()]
        i.sort()
        best = i.pop(-1)
        counter = sum(a for a,b in i)
        if best[0] > counter * 2:
            return 'M',best[1]
        if best[0] > counter:
            return 'm',best[1]
        return 'd', b'_UNREAD_' * (len(best[1]) // 8)

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
        if not i:
            i = FloppySector(self, sector.key)
            self.sectors[sector.key] = i
        i.add_reading(sector)

    def hasgood(self, cyl, hd, sect):
        retval = '-'
        isgood = None
        ngood = 0
        fs = self.sectors.get((cyl, hd, sect + self.sect0))
        if not fs:
            return '-'
        return str(fs)

    def getgood(self, cyl, hd, sect):
        isgood = None
        fs = self.sectors.get((cyl, hd, sect + self.sect0))
        if fs:
            return fs.data()
        return None

    def badsects(self):
        for cyl in range(self.cyl_no):
            for hd in range(self.hd_no):
                for sect in range(self.sect_no):
                    i = self.hasgood(cyl, hd, sect)
                    if i in 'd-':
                        yield i, (cyl, hd, sect + self.sect0)

    def pic_cyl_h(self, dst, just_summary):
        self.stats = {}
        for sect in range(self.sect_no):
            for hd in range(self.hd_no):
                t = ""
                for cyl in range(self.cyl_no):
                    i = self.hasgood(cyl, hd, sect)
                    j = self.stats.get(i, 0)
                    self.stats[i] = j + 1
                    t += i
                if just_summary:
                    continue
                miss = t.count("-")
                dst.write("%03d %2d %s /%2d\n" % (sect, hd, t, miss))
        if just_summary:
            return
        t = " " * 7
        for cyl in range(self.cyl_no):
            if cyl % 10 == 0:
                t += '|'
            else:
                t += ' '
        dst.write(t + "\n")

    def pic_cyl_v(self, dst, just_summary):
        self.stats = {}
        rpt = 0
        prev = ""
        for cyl in range(self.cyl_no):
            for hd in range(self.hd_no):
                t = ""
                for sect in range(self.sect_no):
                    i = self.hasgood(cyl, hd, sect)
                    j = self.stats.get(i, 0)
                    self.stats[i] = j + 1
                    t += i
                if just_summary:
                    continue
                miss = t.count('-')
                if t == prev:
                    rpt += 1
                    continue
                if rpt:
                    dst.write("* %d\n" % rpt)
                    rpt = 0
                dst.write("%03d %2d %s /%2d\n" % (cyl, hd, t, miss))
                prev = t
        if rpt:
            dst.write("* %d\n" % rpt)

    def status(self, dst=None, just_summary=False):
        if dst is None:
            dst = sys.stdout
        if self.cyl_no <= 85:
            self.pic_cyl_h(dst, just_summary)
        else:
            self.pic_cyl_v(dst, just_summary)
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
                        else:
                            file.write(sr)
