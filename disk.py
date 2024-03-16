#!/usr/bin/env python3

'''
   Disks and supporting classes
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

class CHSSet():
    ''' Summarize sets of CHS values '''

    def __init__(self):
        self.chs = []
        self.seen = set()

    def add_defect(self, chs):
        ''' add a defect in CHS format '''
        if chs in self.seen:
            return
        self.seen.add(chs)
        chs = list(chs)
        self.chs.append(chs)
        while len(self.chs) > 1:
            prev = self.chs[-2]
            last = self.chs[-1]
            diff = None
            for i, j in enumerate(zip(prev, last)):
                if j[0] == j[1]:
                    continue
                if diff is not None:
                    return
                if not isinstance(j[1], int):
                    return
                diff = i
            assert diff is not None
            if isinstance(prev[diff], int):
                if prev[diff] + 1 != last[diff]:
                    return
                prev[diff] = [prev[diff], last[diff]]
                self.chs.pop(-1)
            elif prev[diff][-1] + 1 != last[diff]:
                return
            else:
                prev[diff][-1] = last[diff]
                self.chs.pop(-1)

    def __len__(self):
        return len(self.chs)

    def __iter__(self):
        if len(self.chs) == 0:
            return
        for chs in self.chs:
            retval = []
            for i, j in zip(chs, "chs"):
                if isinstance(i, int):
                    retval.append(j + str(i))
                else:
                    retval.append(j + str(i[0]) + '…' + str(i[1]))
            yield ''.join(retval)

class DiskFormat():
    ''' Base class for disk formats '''

    FIRST_CHS = None
    LAST_CHS = None
    SECTOR_SIZE = None

    def __init__(self, stream, source):
        self.stream = stream
        self.source = source

    def define_geometry(self, media):
        ''' Propagate geometry (if any) to media '''
        if self.FIRST_CHS and self.LAST_CHS:
            media.define_geometry(
                self.FIRST_CHS,
                self.LAST_CHS,
                self.SECTOR_SIZE
            )

class DiskSector():
    ''' A sector on the disk image (keeps track of readings) '''

    def __init__(self, chs):
        self.chs = chs
        self.readings = []
        self.values = {}
        self.lengths = set()

    def __len__(self):
        return len(self.readings)

    def add_sector(self, read_sector):
        ''' Add a reading of this sector '''
        assert read_sector.chs == self.chs
        assert read_sector.good
        self.readings.append(read_sector)
        i = self.values.get(read_sector.octets)
        if i is None:
            i = []
            self.values[read_sector.octets] = i
        i.append(read_sector)
        self.lengths.add(len(read_sector.octets))

    def status(self):
        ''' Report status and visual aid '''
        if len(self.values) == 0:
            return False, '╳'
        if len(self.values) <= 1:
            return True, "╳▁▂▃▄▅▆▇█"[min(len(self.readings), 7)]
        return False, '▒'

    def write_data(self):
        ''' Return data to be written '''
        if len(self.values) == 0:
            return None
        assert len(self.values) == 1
        return list(self.values.keys())[0]

class Disk():
    ''' A disk media '''

    def __init__(self):
        self.disk_sectors = {}
        self.defined_geometry = False
        self.has_cylinders = set()
        self.has_heads = set()
        self.has_sectors = set()
        self.last_addition = (-1, -1, -1)
        self.format_class = None

    def __str__(self):
        return "{DISK " + self.geometry() + "}"

    def define_geometry(self, first_chs, last_chs, sector_size = None):
        ''' Define (part) of the geometry '''
        assert len(first_chs) == 3
        assert len(last_chs) == 3
        for cyl in range(first_chs[0], last_chs[0]+1):
            self.has_cylinders.add(cyl)
            for head in range(first_chs[1], last_chs[1]+1):
                self.has_heads.add(head)
                for sector in range(first_chs[2], last_chs[2]+1):
                    #self.has_sectors[sector] = sector_size
                    self.has_sectors.add(sector)
                    chs = (cyl, head, sector)
                    self.disk_sectors[chs] = DiskSector(chs)
        self.defined_geometry = True

    def add_sector(self, read_sector):
        ''' Add a reading of a sector '''
        self.last_addition = read_sector.chs
        disksector = self.disk_sectors.get(read_sector.chs)
        if disksector is None:
            disksector = DiskSector(read_sector.chs)
            self.disk_sectors[read_sector.chs] = disksector
            self.has_cylinders.add(read_sector.chs[0])
            self.has_heads.add(read_sector.chs[1])
            self.has_sectors.add(read_sector.chs[2])
        disksector.add_sector(read_sector)

    def sector_lengths(self):
        ''' return the sector lengths encountered '''
        lengths = set()
        for disk_sector in self.disk_sectors.values():
            lengths |= disk_sector.lengths
        return lengths

    def is_cubic(self):
        retval = []
        ncube = 1
        for j in (
            self.has_cylinders,
            self.has_heads,
            self.has_sectors,
        ):
            if len(j) == 0:
                return False
            retval.append(1 + max(j) - min(j))
            ncube *= retval[-1]
        if ncube != len(self.disk_sectors):
            return False
        i = self.sector_lengths()
        if len(i) != 1:
            return False
        retval.append(list(i)[0])
        return tuple(retval)

    def geometry(self):
        ''' Return media geometry '''
        dset = CHSSet()
        for chs in sorted(self.disk_sectors):
            dset.add_defect(chs)
        return "+".join(dset)

    def defects(self):
        ''' Report defect status '''
        ndef = 0
        dset = CHSSet()
        for chs, disk_sector in sorted(self.disk_sectors.items()):
            i, _j = disk_sector.status()
            if not i:
                ndef += 1
                dset.add_defect(chs)
        if ndef == 0:
            return
        yield str(ndef)

        if len(dset) > 5:
            dset = CHSSet()
            for chs, disk_sector in sorted(self.disk_sectors.items()):
                i, _j = disk_sector.status()
                if not i:
                    ndef += 1
                    dset.add_defect((chs[0],))

        yield from dset
        if not self.defined_geometry:
            yield "(possibly more: no defined geometry)"

    def horizontal_status(self):
        l1 = []
        for cylinder in sorted(self.has_cylinders):
            if cylinder == self.last_addition[0]:
                l1.append('↓')
            elif cylinder % 10 == 0:
                l1.append('%d' % (cylinder // 10))
            elif cylinder % 10 == 5:
                l1.append(':')
            else:
                l1.append('.')
        yield ''.join(l1)

        for head in sorted(self.has_heads):
            if len(self.has_heads) > 1:
                yield "head=%d" % head
            for sector in sorted(self.has_sectors):
                i = []
                for cylinder in sorted(self.has_cylinders):
                    chs = (cylinder, head, sector)
                    disk_sector = self.disk_sectors.get(chs)
                    if disk_sector is None:
                        i.append('╳')
                        continue
                    _j, k = disk_sector.status()
                    i.append(k)
                yield ''.join(i)
        i = list(self.defects())
        if len(i) > 0:
            yield "Defects: " + ", ".join(i)
        else:
            yield "Complete"

    def iter_chs(self):
        for cylinder in range(min(self.has_cylinders), max(self.has_cylinders) + 1):
            for head in range(min(self.has_heads), max(self.has_heads) + 1):
                for sector in range(min(self.has_sectors), max(self.has_sectors) + 1):
                    yield(cylinder, head, sector)

    def status(self):
        ''' Produce a status/progress display '''
        i = ["Status", str(self.geometry())]
        if self.format_class:
            i.append(self.format_class.__name__)
        yield "  ".join(i)
        if len(self.has_cylinders) <= 85:
            yield from self.horizontal_status()

    def write_bin_file(self, filename):
        lengths = self.sector_lengths()
        if len(lengths) == 0:
            return
        assert len(lengths) == 1
        sector_length = list(lengths)[0]
        unread = b'_UNREAD_' * (1 + (sector_length // 8))
        unread = unread[:sector_length]
        with open(filename, "wb") as fo:
            for chs in self.iter_chs():
                disk_sector = self.disk_sectors.get(chs)
                if disk_sector is None:
                    fo.write(unread)
                    continue
                data = disk_sector.write_data()
                if data is None:
                    fo.write(unread)
                    continue
                fo.write(data)

    def ddhf_meta(self, basename):
        ''' Emit DDHF bitstore metadata information '''
        yield 'Bitstore.Filename:'
        yield '\t' + basename + ".BIN"
        yield ''
        yield 'Bitstore.Format:'
        yield '\tBINARY'
        yield ''
        if self.format_class:
            yield 'Media.Summary:'
            yield '\t8" ' + self.format_class.__name__ + ' floppy ' + basename
            yield ''
        yield 'Media.Geometry:'
        yield '\t' + self.geometry()
        yield ''
        yield 'Media.Type:'
        yield '\t8" Floppy Disk'
        yield ''
        yield 'Media.Description:'
        if self.format_class:
            yield '\tFormat: ' + self.format_class.__name__
        i = list(self.defects())
        if i:
            yield '\tDefects: ' + ", ".join(i)
        yield ''
