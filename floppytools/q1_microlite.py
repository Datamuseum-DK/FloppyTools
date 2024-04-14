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

   The error check is a trivial byte checksum, followed by 0x10.
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

from . import main
from . import disk
from . import fluxstream

def most_common(lst):
    ''' Return most common element '''

    return Counter(lst).most_common(1)[0][0]

class ClockRecovery(fluxstream.ClockRecovery):
    ''' MFM at non-standard rate '''

    SPEC = {
         77: "-|",
        115: "--|",
        154: "---|",
        192: "----|",
        231: "-----|",
    }

class Q1MicroLite(disk.DiskFormat):
    ''' Q1 Corporation MicroLite floppy disks '''

    SYNC = '|-' * 8 + '---|-'
    DATA_PATTERN = SYNC + fluxstream.make_mark(0x20, 0x9b)
    AM_PATTERN = SYNC + fluxstream.make_mark(0x20, 0x9e)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cyl_sect_len = {}

    def cache_was_read(self):
        ''' Do housekeeping after cache was read '''

        seen = set()
        for ds in list(self.media.disk_sectors.values()):
            if ds.chs[0]:
                continue
            if ds.chs in seen:
                continue
            data = ds.find_majority()
            if data is None:
                continue
            seen.add(ds.chs)
            self.catalog(ds.chs, data)

    def catalog(self, chs, data):
        ''' Process a catalog sector from track zero '''

        if len(data) != 40 or data[0] or data[1] or data[2] == 0:
            return
        fmt = "<H8sHHHHH"
        flds = struct.unpack(fmt, data[:struct.calcsize(fmt)])
        first = flds[5]
        last = flds[6]
        nsect = flds[4]
        count = flds[2]
        length = flds[3]
        # print("CAT", flds)
        last = max(last, 80)
        for cyl in range(first, last +1):
            self.cyl_sect_len[cyl] = length
            for sect in range(0, nsect):
                if count == 0:
                    return
                chs = (cyl, 0, sect)
                self.media.define_sector(chs, length)
                count -= 1

    def sector_length(self, chs):
        ''' sector length for this track '''

        if 0 and chs[0] == 0:
            return 40
        return self.cyl_sect_len.get(chs[0], None)

    def propose_sector(self, chs, sector_length, data):
        ''' Proposed sector '''

        if len(data) < sector_length + 2:
            return
        if data[sector_length + 1] != 0x10:
            return
        if (0x9b + sum(data[:sector_length])) & 0xff != data[sector_length]:
            return
        if chs[0] == 0:
            self.catalog(chs, data[:sector_length])
        #print("G", chs, sector_length, data[:sector_length].hex())
        yield disk.Sector(chs, data[:sector_length])

    def split_stream(self, stream):
        ''' Two level split of stream at AM and then Data '''
        # Done this way to aid manual recoveries

        flux = ClockRecovery().process(stream.iter_dt())

        for i in flux.split(self.AM_PATTERN)[1:]:
            j = i.split(self.DATA_PATTERN)
            # There must be a data part
            if len(j) < 2:
                continue
            # Close to the address mark
            if len(j[0]) > 10*16:
                continue
            yield j

    def am_to_chs(self, stream, flux):
        am_data = stream.flux_data_mfm(flux[:4*16])
        if len(am_data) != 4:
            return None
        if am_data[3] != 0x10:
            return None
        if (am_data[0] + am_data[1]) & 0xff != am_data[2]:
            return None
        return (am_data[0], 0, am_data[1])

    def flux_for_sector(self, chs, stream):
        ''' Return (candidate) flux for specific sector '''
        for fluxparts in self.split_stream(stream):
            i = self.am_to_chs(stream, fluxparts[0])
            if i is None:
                continue
            if i[0] != chs[0]:
                return
            if i != chs:
                continue
            yield fluxparts[1]

    def process(self, stream):
        ''' process a stream '''

        later = []
        for i in self.split_stream(stream):
            chs = self.am_to_chs(stream, i[0])
            if chs is None:
                continue

            sector_length = self.sector_length(chs)

            if sector_length is None:
                later.append((chs, i[1]))
            else:
                data = stream.flux_data_mfm(i[1][:(sector_length+2) * 16])
                yield from self.propose_sector(chs, sector_length, data)

        if not later:
            return

        # We dont know the sector lenght for this track (yet): Try to guess it

        # Find the most common flux-length for data part
        common_length = most_common(len(x[1])//16 for x in later) * 16

        # Convert from MFM to bytes and locate the last 0x10 value
        sectors = []
        tens = []
        for chs, data_flux in later:
            data = stream.flux_data_mfm(data_flux[:common_length])
            sectors.append((chs, data))
            ten_pos = data.rfind(b'\x10')
            if ten_pos > 0:
                tens.append(ten_pos)

        if tens:
            sector_length = most_common(tens) - 1
            for chs, data in sectors:
                yield from self.propose_sector(chs, sector_length, data)

if __name__ == "__main__":
    main.Main(Q1MicroLite)
