#!/usr/bin/env python3

'''
   Abstract Base Class for disk-like media
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

from .chsset import CHSSet
from collections import Counter

class ReadSector():
    ''' One reading of a sector '''

    def __init__(self, chs, octets, source, flags=(), good=True,):
        assert len(chs) == 3
        self.chs = chs
        self.octets = octets
        if hasattr(source, "serialize"):
            self.source = source.serialize()
        else:
            self.source = str(source)
        self.good = good
        self.flags = set(flags)
        if not good:
            self.flags.add("bad")

    def __str__(self):
        return str(("ReadSector", self.chs, self.good, len(self.octets)))

    def __eq__(self, other):
        return self.octets == other.octets and self.good == other.good

    def __len__(self):
        return len(self.octets)

class MediaSector():

    ''' What we know about a sector on the media '''

    def __init__(self, chs, sector_length=None):
        assert len(chs) == 3
        self.chs = chs
        self.readings = []
        self.values = {}
        self.sector_length = sector_length
        self.lengths = set()
        self.flags = set()
        self.status_cache = {}

    def __str__(self):
        return str(("MediaSector", self.chs, self.sector_length, self.flags))

    def __lt__(self, other):
        return self.chs < other.chs

    def set_flag(self, flag):
        self.flags.add(flag)

    def has_flag(self, flag):
        return flag in self.flags

    def add_read_sector(self, read_sector):
        ''' Add a reading of this sector '''

        assert read_sector.chs == self.chs
        self.readings.append(read_sector)
        i = self.values.get(read_sector.octets)
        if i is None:
            i = []
            self.values[read_sector.octets] = i
        i.append(read_sector)
        self.lengths.add(len(read_sector.octets))
        self.status_cache = {}

    def find_majority(self):
        t = self.status_cache.get("majority")
        if t:
            return t
        chosen = None
        majority = 0
        count = 0
        for i, j in self.values.items():
            if self.sector_length and len(i) != self.sector_length:
                continue
            count += 1
            if len(j) > majority:
                majority = len(j)
                chosen = i
        minority = count - majority
        retval = None
        if majority > 2 * minority:
            retval = chosen
        self.status_cache["majority"] = retval
        return retval

    def real_sector_status(self):
        ''' Report status and visual aid '''

        if len(self.values) == 0:
            return False, 'x', None
        maj = self.find_majority()
        if len(self.values) > 1 and maj:
            return True, "░", len(maj)
        if len(self.values) > 1:
            return False, '╬', None
        if self.sector_length:
            k = list(self.values.keys())[0]
            if len(k) > self.sector_length:
                return False, '>', len(maj)
            if len(k) < self.sector_length:
                return False, '<', len(maj)
        return True, "×▁▂▃▄▅▆▇█"[min(len(self.readings), 7)], len(maj)

    def sector_status(self):
        ''' Report status and visual aid '''

        i = self.status_cache.get("sector")
        if not i:
            i = self.real_sector_status()
            self.status_cache["sector"] = i
        return i

class MediaAbc():
    '''
       An abstract disk-like media.

       This is the superclass by the actual formats
    '''

    def __init__(self, name=None):
        if name is None:
            name = self.__class__.__name__
        self.name = name
        self.sectors = {}
        self.cyl_no = set()
        self.hd_no = set()
        self.sec_no = set()
        self.lengths = set()
        self.messages = set()
        self.n_expected = 0
        self.status_cache = {}

    def __str__(self):
        return "{MEDIA " + self.__class__.__name__ + " " + self.name + "}"

    def __getitem__(self, chs):
        return self.sectors.get(chs)

    def message(self, *args):
        txt = " ".join(str(x) for x in args)
        if txt in self.messages:
            return txt
        self.messages.add(txt)
        return txt

    def get_sector(self, chs):
        assert len(chs) == 3
        ms = self.sectors.get(chs)
        if ms is None:
            ms = MediaSector(chs)
            self.sectors[chs] = ms
        return ms

    def add_read_sector(self, rs):
        assert len(rs.chs) == 3
        if rs.chs not in self.sectors:
            self.sectors[rs.chs] = MediaSector(rs.chs)
        self.sectors[rs.chs].add_read_sector(rs)
        self.cyl_no.add(rs.chs[0])
        self.hd_no.add(rs.chs[1])
        self.sec_no.add(rs.chs[2])
        self.lengths.add(len(rs))
        self.status_cache = {}

    def define_sector(self, chs, sector_length=None):
        ms = self.sectors.get(chs)
        if ms is None:
            ms = MediaSector(chs, sector_length)
            self.sectors[chs] = ms
        if not ms.has_flag("defined"):
            ms.sector_length = sector_length
            ms.set_flag("defined")
            self.n_expected += 1
        elif ms.sector_length is None:
            ms.sector_length = sector_length
        else:
            if ms.sector_length != sector_length:
                self.trace("Different defined sector lengths", chs, sector_length, ms)
                self.message("SECTOR_LENGTH_CONFUSION")
        self.cyl_no.add(chs[0])
        self.hd_no.add(chs[1])
        self.sec_no.add(chs[2])
        return ms

    def picture(self):
        yield from self.picture_sec_x()

    def sector_status(self, media_sector):
        return media_sector.sector_status()

    def pic_sec_x_line(self, cyl_no, head_no):
        l = []
        if len(self.hd_no) == 1:
            l.append("%4d " % cyl_no)
        else:
            l.append("%4d,%2d " % (cyl_no, head_no))
        lens = []
        nsec = 0
        for sec_no in range(min(self.sec_no), max(self.sec_no) + 1):
            ms = self.sectors.get((cyl_no, head_no, sec_no))
            if ms is None:
                l.append(' ')
            else:
                nsec += 1
                _i, j, k = self.sector_status(ms)
                l.append(j)
                if k is not None:
                    lens.append(k)
        if lens:
            i = Counter(lens).most_common()
            l.insert(1, ("%d*%d" % (nsec, i[0][0])).ljust(9))
        else:
            l.insert(1, " " * 9)
        return l

    def picture_sec_x(self):
        if not self.hd_no or not self.cyl_no:
            return
        l = []
        for cyl_no in range(min(self.cyl_no), max(self.cyl_no) + 1):
            l.append(list())
            for head_no in range(min(self.hd_no), max(self.hd_no) + 1):
                l[-1].append("".join(self.pic_sec_x_line(cyl_no, head_no)))
        w = []
        for col in range(len(l[0])):
            w.append(max(len(x[col]) for x in l))
        for line in l:
            x = []
            for width,col in zip(w, line):
                x.append(col.ljust(width + 3))
            yield "".join(x).rstrip()

    def missing(self):
        why = {}
        for ms in self.sectors.values():
            i, j, k = self.sector_status(ms)
            if i:
                continue
            if j not in why:
                why[j] = CHSSet()
            why[j].add(ms.chs)
        for i, j in sorted(why.items()):
            for x in j:
                yield i, x

    def summary(self):
        retval = self.status_cache.get("summary")
        if retval is None:
            ngood = 0
            nextra = 0
            badones = {}
            goodset = CHSSet()
            badset = CHSSet()
            l = [ self.name ]
            for ms in self.sectors.values():
                i, j, k = self.sector_status(ms)
                defd = ms.has_flag("defined")
                if i and defd:
                    ngood += 1
                    goodset.add(ms.chs)
                elif i:
                    nextra += 1
                    goodset.add(ms.chs)
                else:
                    badset.add(ms.chs)
                    if j not in badones:
                        badones[j] = []
                    badones[j].append(ms)
            if ngood == 0 and nextra == 0:
                l.append("NOTHING")
            elif self.n_expected and ngood == self.n_expected:
                l.append("COMPLETE")
                if nextra:
                    l.append("EXTRA")
            else:
                if not self.n_expected and not badones:
                    l.append("SOMETHING")
                    l.append("")
                    for x in goodset:
                        if len(l[-1]) + len(x) < 64:
                            l[-1] += "," + x
                        else:
                            l[-1] += "[…]"
                            break
                    l[-1] = l[-1][1:]
                else:
                    l.append("MISSING")
                    l.append(badset.cylinders())
                l.append("✓: %d" % ngood)
                for c in sorted(badones):
                    l.append(c + ": %d" % len(badones[c]))
            retval = "  ".join(l)
            self.status_cache["summary"] = retval
        return retval

    def any_good(self):
        for ms in sorted(self.sectors.values()):
            i, _j, k = self.sector_status(ms)
            if i:
                return True
        return False

    def process_stream(self, _source):
        ''' ... '''
        print(self, "lacks process_stream method")
        assert False
