#/usr/bin/env python3

'''
   Q1 Microlite floppies
   ~~~~~~~~~~~~~~~~~~~~~

   This is in top five of strange floppy formats.

   Please note that the following information is based on analysis
   of a single floppy-disk.

   Each file has a record length, and the tracks allocated to that
   file are formatted with that sector length.  The surplus space
   seems to be distributed evenly between sectors.

   Modulation is MFM with an atypical frequency.

   Synchronization is (64?) zeros, 3½ bit times with a clock-violation,
   followed by either 0x9e (address-mark) or 0x9b (data)

   The error check is a trivial byte checksum.
   For address-marks the 0x9e is not included, for data the 0x9b is.

   Track zero has 40 byte sectors, each of which contains the catalog
   entry for a single file, containing the filename, first and last
   tracks, length of records, number of records per track and the
   record after the last one.

   Unused sectors, including the sectors past end of file, has address
   marks, but the data may not pass the error check.

'''

import struct

from collections import Counter

from ..base import media
from ..base import fluxstream

def most_common(lst):
    ''' Return most common element '''

    return Counter(lst).most_common(1)[0][0]


class Q1MicroLiteCommon(media.Media):
    ''' ... '''

    aliases = ["Q1"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog_todo = []
        self.catalog_entries = {}
        self.cyl_contains = [""] * 77
        self.cyl_skew = False
        for chs, ms in list(self.sectors.items()):
            if chs[0] > 0:
                continue
            for rs in ms.readings:
                self.catalog_entry(chs, rs.octets)

    def split_stream(self, flux):
        ''' Two level split of stream at AM and then Data '''

        for i in flux.split(self.AM_PATTERN)[1:]:
            j = i.split(self.DATA_PATTERN)
            # There must be a data part
            if len(j) < 2:
                self.trace("no DATA_PATTERN", len(i), [len(x) for x in j])
                continue
            # Close to the address mark
            if len(j[0]) > self.GAPLEN:
                self.trace("Too much gap", len(j[0]), self.GAPLEN)
                continue
            yield j

    def sector_length(self, stream, chs):
        if chs[0] != stream.chs[0] and not self.cyl_skew:
            self.message("CYL_SKEW")
            self.trace(
                "Cylinder skew",
                "AM is",
                chs,
                "Stream",
                stream,
            )
            self.cyl_skew = True
        if chs[0] == 0:
            return None, 40
        ms = self.sectors.get(chs)
        if ms:
            return ms, ms.sector_length
        return None, None

    def actually_do_catalog_entry(self, chs, data):
        if chs[2] == 0:
            pass
        elif chs not in self.sectors:
            print("CAT bad chs", chs)
            return
        elif self.sectors[chs].has_flag("unused"):
            return

        fmt = "<H8sHHHHH"
        flds = struct.unpack(fmt, data[:struct.calcsize(fmt)])
        status = flds[0]
        if status != 0:
            print("CAT non-zero status", chs, flds)
            return
        name = flds[1]
        if chs[2] == 0:
            assert name == b'INDEX   '
        count = flds[2]
        length = flds[3]
        first = flds[5]
        last = flds[6]
        nsect = flds[4]
        if chs not in self.catalog_entries:
            self.trace("CATALOG", "%2d,%3d" % (chs[0], chs[2]), flds)
            self.catalog_entries[chs] = flds
        if last >= 80:
            self.trace("LAST", str(last))
            return
       
        for cyl in range(first, last +1):
            self.cyl_contains[cyl] = name.decode('ascii')
            for sect in range(0, nsect):
                i = (cyl, 0, sect)
                ms = self.define_sector(i, length)
                if count == 0:
                    ms.set_flag("unused")
                else:
                    count -= 1

    def catalog_entry(self, chs, data):
        '''
           Process a catalog sector from track zero

           We pile up entries until we have seen an "INDEX"
           entry in sector zero, so avoid processing junk
           in a sector outside INDEX.count.
        '''

        if chs[2] != 0 and self.catalog_todo is not None:
            self.catalog_todo.append((chs, data))
            return

        self.actually_do_catalog_entry(chs, data)

        if self.catalog_todo is None:
            return

        todo = self.catalog_todo
        self.catalog_todo = None
        for i, j in todo:
            self.actually_do_catalog_entry(i, j)

    def attempt_sector(self, chs, data, stream, ms=None, sector_length=None, also_bad=False):
        good = True
        flags = []
        if ms:
            sector_length = ms.sector_length
        if sector_length is None:
            return False

        if len(data) < sector_length + 2:
            if ms:
                self.trace(chs, "short", len(data), sector_length + 2)
            good=False
            flags.append("Short")
        elif ms and ms.has_flag('unused'):
            good=True
            flags.append("unused")
        elif not self.good_checksum(data, sector_length):
            if ms:
                self.trace(chs, "bad checksum", data.hex())
            good=False
            flags.append("SumError")

        if good:
            self.did_read_sector(
                stream,
                "0",
                chs,
                data[:sector_length],
                flags=flags,
            )
            if not self.defined_chs((0, 0, 0)):
                self.define_sector((0, 0, 0), 40)
        if good and chs[0] == 0:
            self.catalog_entry(chs, data)

        return good

    def sector_status(self, media_sector):
        x = media_sector.sector_status()
        i, j, k = media_sector.sector_status()
        unused = media_sector.has_flag("unused")
        if j == 'x' and unused:
            j = 'u'
        if j == '╬' and unused:
            j = 'ü'
        if unused:
            i = True
        return i, j, k

    def picture(self, *args, **kwargs):
        yield from self.picture_sec_x(*args, **kwargs)

    def pic_sec_x_line(self, cyl_no, head_no):
        l = super().pic_sec_x_line(cyl_no, head_no)
        l.insert(1, self.cyl_contains[cyl_no].ljust(10))
        return l

    def guess_sector_length(self, stream, later, conv):
        # We dont know the sector lenght for this track (yet): Try to guess it

        # Find the most common flux-length for data part

        common_length = most_common(len(x[1][1])//16 for x in later)
        self.trace("Most common length", common_length)

        # Convert from MFM to bytes and locate the last 0x10 value
        sectors = []
        tens = []
        retval = False
        for chs, parts in later:
            data = conv(parts[1][:(common_length+2) * 16])
            sectors.append((chs, data))
            ten_pos = data.rfind(b'\x10')

            if ten_pos > 0:
                tens.append(ten_pos)

        if tens:
            sector_length = most_common(tens) - 1
            self.trace("Sector_length", sector_length)
            for chs, data in sectors:
                #self.trace(chs, data.hex())
                if self.attempt_sector(chs, data, stream, None, sector_length):
                    retval = True
        return retval

    def metadata_media_description(self):
        yield ""
        yield "Catalog Entries:"
        yield "\tName      Used  Rec-Len  Alloc  Tracks"
        yield "\t--------  ----  -------  -----  ------"
        for i, j in sorted(self.catalog_entries.items()):
            l = [
                j[1].decode('ascii').ljust(8),
                "",
                "%4d" % j[2],
                "",
                "%7d" % j[3],
                "",
                "%5d" % j[4],
                "",
                ("%d-%d" % (j[5], j[6])).rjust(6),
            ]
            yield "\t" + " ".join(l)

class Q1MicroLiteFM(Q1MicroLiteCommon):
    '''
        Q1 Corporation MicroLite FM format floppy disks

	Bla

	FOo
    '''

    SYNC = '|---' * 16
    AM_PATTERN = SYNC + fluxstream.make_mark_fm(0xc7, 0xfe)
    DATA_PATTERN = SYNC + fluxstream.make_mark_fm(0xc7, 0xfb)
    GAPLEN = 100*32

    def good_checksum(self, data, sector_length):
        csum = sum(data[:sector_length + 1]) & 0xff
        return csum == 0

    def am_to_chs(self, stream, flux):
        am_data = stream.flux_data_fm(flux[:6*32])
        if len(am_data) != 6:
            return None
        if am_data[0] != 0x00:
            return None
        if am_data[1] != 0x00:
            return None
        if am_data[5] != 0x10:
            return None
        if sum(am_data[:5]) & 0xff:
            return None
        return (am_data[2], 0, am_data[3])

    def process_stream(self, stream):
        ''' process a stream '''

        if stream.chs[1] != 0:
            return None
        later = []
        retval = False

        flux = stream.fm_flux()
        for parts in self.split_stream(flux):
            chs = self.am_to_chs(stream, parts[0])
            if chs is None:
                continue
            ms, sector_length = self.sector_length(stream, chs)

            if sector_length:
                data = stream.flux_data_fm(parts[1][:(sector_length+2)*32])
                if self.attempt_sector(
                    chs,
                    data,
                    stream,
                    ms,
                    sector_length,
                ):
                    retval = True
            else:
                later.append((chs, parts))

        if later and self.guess_sector_length(stream, later, stream.flux_data_fm):
            retval = True
        return retval

class ClockRecoveryMFM(fluxstream.ClockRecovery):
    ''' MFM at non-standard rate '''

    def __init__(self, dt=None):
        if dt is None:
            dt = 28
        self.SPEC = {}
        self.SPEC[2*dt] = "-|"
        self.SPEC[3*dt] = "--|"
        self.SPEC[4*dt] = "---|"
        self.SPEC[5*dt] = "----|"
        self.SPEC[6*dt] = "-----|"


class Q1MicroLiteMFM28(Q1MicroLiteCommon):
    '''
        Q1 Corporation MicroLite MFM format floppy disks
    '''

    SYNC = '|-' * 8 + '---|-'
    AM_PATTERN = SYNC + fluxstream.make_mark(0x20, 0x9e)
    DATA_PATTERN = SYNC + fluxstream.make_mark(0x20, 0x9b)
    GAPLEN = 10*16

    CLOCK = 28

    def am_to_chs(self, stream, flux):
        am_data = stream.flux_data_mfm(flux[:4*16])
        if len(am_data) != 4:
            return None
        if am_data[3] != 0x10:
            return None
        if (am_data[0] + am_data[1]) & 0xff != am_data[2]:
            return None
        return (am_data[0], 0, am_data[1])

    def good_checksum(self, data, sector_length):
        csum = (0x9b + sum(data[:sector_length])) & 0xff
        return csum == data[sector_length]

    def process_stream(self, stream):
        ''' process a stream '''

        if stream.chs[1] != 0:
            return None
        later = []
        retval = False

        flux = ClockRecoveryMFM(self.CLOCK).process(stream.iter_dt())
        for parts in self.split_stream(flux):
            chs = self.am_to_chs(stream, parts[0])
            if chs is None:
                continue

            ms, sector_length = self.sector_length(stream, chs)

            if sector_length:
                data = stream.flux_data_mfm(parts[1][:(sector_length+2) * 16])
                if self.attempt_sector(
                    chs,
                    data,
                    stream,
                    ms,
                    sector_length,
                ):
                    retval = True
            else:
                later.append((chs, parts))

        if later and self.guess_sector_length(stream, later, stream.flux_data_mfm):
            retval = True
        return retval

class Q1MicroLiteMFM39(Q1MicroLiteMFM28):
    '''
        Q1 Corporation MicroLite MFM format floppy disks
    '''
    CLOCK = 39

ALL = [
    Q1MicroLiteMFM28,
    Q1MicroLiteMFM39,
    Q1MicroLiteFM,
]
