#!/usr/bin/env python3

'''
   Disks and supporting classes
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import time

class NotInterested(Exception):
    ''' ... '''

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

    media = None
    repair = set()

    def define_geometry(self, media):
        ''' Propagate geometry (if any) to media '''
        if self.FIRST_CHS and self.LAST_CHS:
            media.define_geometry(
                self.FIRST_CHS,
                self.LAST_CHS,
                self.SECTOR_SIZE
            )

    def cached_sector(self, read_sector):
        ''' ... '''
        self.media.add_sector(read_sector)

    def validate_chs(self, chs, none_ok=False, stream=None):
        ''' Validate a CHS against the geometry '''
        for n, i in enumerate(chs):
            if none_ok and i is None:
                continue
            if self.FIRST_CHS is not None and i < self.FIRST_CHS[n]:
                return None
            if self.LAST_CHS is not None and i > self.LAST_CHS[n]:
                return None
            if stream and stream.chs[n] not in (None, i):
                return None
        return tuple(chs)

class Sector():
    ''' A single sector, read by a Reading '''

    def __init__(self, chs, octets, good=True, source=None, extra=""):
        assert len(chs) == 3
        self.chs = chs
        self.octets = octets
        self.good = good
        self.source = source
        self.extra = extra

    def __str__(self):
        return str((self.chs, self.good, len(self.octets)))

    def __eq__(self, other):
        return self.octets == other.octets and self.good == other.good

    def cache_record(self):
        return [
            "%d,%d,%d" % self.chs,
            self.octets.hex(),
            str(self.extra)
        ]

class MediaSector():

    ''' A sector on the disk image (keeps track of readings) '''

    def __init__(self, chs):
        self.chs = chs
        self.readings = []
        self.values = {}
        self.lengths = set()

    def __len__(self):
        return len(self.readings)

    def __lt__(self, other):
        return self.chs < other.chs

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

    def find_majority(self):
        chosen = None
        majority = 0
        for i, j in self.values.items():
            if len(j) > majority:
                majority = len(j)
                chosen = i
        minority = len(self.readings) - majority
        if majority > 2 * minority:
            return chosen
        # print(self.chs, "majority", majority, "minority", minority, "candidates", len(self.values))
        return None

    def status(self):
        ''' Report status and visual aid '''
        if len(self.values) == 0:
            return False, '×'
        if len(self.values) <= 1:
            return True, "×▁▂▃▄▅▆▇█"[min(len(self.readings), 7)]
        if self.find_majority():
            return True, "░"
        return False, '╬'

    def write_data(self):
        ''' Return data to be written '''
        if len(self.values) == 0:
            return None
        if len(self.values) == 1:
            return list(self.values.keys())[0]
        return self.find_majority()

class Media():
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
        return "{MEDIA " + self.geometry() + "}"

    def iter_sectors(self):
        yield from sorted(self.disk_sectors.values())

    def define_geometry(self, first_chs, last_chs, sector_size = None):
        ''' Define (part) of the geometry '''
        assert len(first_chs) == 3
        assert len(last_chs) == 3
        for cyl in range(first_chs[0], last_chs[0]+1):
            for head in range(first_chs[1], last_chs[1]+1):
                for sector in range(first_chs[2], last_chs[2]+1):
                    chs = (cyl, head, sector)
                    self.define_sector(chs)
        self.defined_geometry = True

    def define_sector(self, chs):
        if chs not in self.disk_sectors:
            self.has_cylinders.add(chs[0])
            self.has_heads.add(chs[1])
            self.has_sectors.add(chs[2])
            self.disk_sectors[chs] = MediaSector(chs)

    def add_sector(self, read_sector):
        ''' Add a reading of a sector '''
        self.last_addition = read_sector.chs
        disksector = self.disk_sectors.get(read_sector.chs)
        if disksector is None:
            disksector = MediaSector(read_sector.chs)
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

    def defects(self, detailed=False):
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

        if detailed:
            yield from dset
            return

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
        for head in sorted(self.has_heads):
            if len(self.has_heads) > 1:
                yield "head=%d" % head

            l1 = []
            for cylinder in sorted(self.has_cylinders):
                if cylinder == self.last_addition[0] and head == self.last_addition[1]:
                    l1.append('↓')
                elif cylinder % 10 == 0:
                    l1.append('%d' % (cylinder // 10))
                elif cylinder % 10 == 5:
                    l1.append(':')
                else:
                    l1.append('.')
            yield ''.join(l1)

            for sector in sorted(self.has_sectors):
                i = []
                for cylinder in sorted(self.has_cylinders):
                    chs = (cylinder, head, sector)
                    disk_sector = self.disk_sectors.get(chs)
                    if disk_sector is None:
                        i.append(' ')
                        continue
                    _j, k = disk_sector.status()
                    i.append(k)
                yield ''.join(i)

    def list_defects(self, detailed=False):
        i = list(self.defects(detailed))
        if len(i) > 0:
            return "Defects: " + ", ".join(i)
        return None

    def iter_ch(self):
        for cylinder in range(min(self.has_cylinders), max(self.has_cylinders) + 1):
            for head in range(min(self.has_heads), max(self.has_heads) + 1):
                yield(cylinder, head)

    def iter_chs(self):
        for cylinder in range(min(self.has_cylinders), max(self.has_cylinders) + 1):
            for head in range(min(self.has_heads), max(self.has_heads) + 1):
                for sector in range(min(self.has_sectors), max(self.has_sectors) + 1):
                    yield(cylinder, head, sector)

    def status(self, detailed=False):
        ''' Produce a status/progress display '''
        i = []
        if self.format_class:
            yield "Format " + self.format_class.__class__.__name__
        yield "Geometry " + str(self.geometry())
        if len(self.has_cylinders) <= 85:
            yield from self.horizontal_status()
        i = self.list_defects()
        if not i:
            yield "Complete"
        elif not detailed:
            yield i
        else:
            yield "Defects:"
            yield from ("\t" + x for x in sorted(self.defects(detailed)))

    def write_bin_file(self, filename):
        lengths = self.sector_lengths()
        if len(lengths) == 0:
            return
        if len(lengths) != 1:
            return
        assert len(lengths) == 1
        sector_length = list(lengths)[0]
        unread = b'_UNREAD_' * (1 + (sector_length // 8))
        unread = unread[:sector_length]
        assert len(unread) == sector_length
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

    def write_imagedisk_file(self, filename):
        hdr = 'IMD 1.19 ' + time.strftime('%d/%m/%Y %H:%M:%S\r\n', time.gmtime())
        with open(filename, "wb") as fo:
            fo.write(hdr.encode('ascii'))
            fo.write("DataMuseum.dk/FloppyTools\r\n".encode('ascii'))
            fo.write(b'\x1a')
            tracks = {}
            tracklen = {}
            trackdata = {}
            for chs in self.iter_chs():
                trk = chs[:2]
                disk_sector = self.disk_sectors.get(chs)
                if disk_sector is None:
                    continue
                data = disk_sector.write_data()
                if trk not in tracks:
                    tracks[trk] = []
                    tracklen[trk] = set()
                    trackdata[trk] = []
                tracks[trk].append(disk_sector)
                tracklen[trk] |= disk_sector.lengths
                trackdata[trk].append(data)
            for trk in sorted(tracks):
                length = tracklen[trk]
                if len(length) != 1:
                    print("TL", trk, length)
                    length = [ 1024 ]
                assert len(length) == 1
                length = list(length)[0]
                assert length is not None
                sectors = tracks[trk]
                chs = sectors[0].chs
                trkhead = []
                trkhead.append(0)
                trkhead.append(chs[0])
                trkhead.append(chs[1])
                trkhead.append(len(sectors))
                trkhead.append(
                    {
                    128: 0,
                    256: 1,
                    512: 2,
                    1024: 3,
                    2048: 4,
                    4096: 5,
                    8192: 6,
                    }[length]
                )
                fo.write(bytes(trkhead))
                for sec in sectors:
                    fo.write(bytes(sec.chs[2:])) # sector number map
                for data in trackdata[trk]:
                    if data is None:
                        data = b'_UNREAD_' * (length // 8)
                    assert len(data) == length
                    fo.write(b'\x01') # Normal sector data
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
