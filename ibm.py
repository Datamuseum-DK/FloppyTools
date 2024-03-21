#/usr/bin/env python3

'''
   IBM format
   ~~~~~~~~~~
'''

import sys

import crcmod

import main
import disk
import fluxstream

crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class MfmRecovery(fluxstream.ClockRecovery):

    # Hand tuned
    RATE = 50e-3

    # Half a period on traditional 8" floppies
    LIMIT = 12.5


    SPEC = {
        50: "-|",
        75: "--|",
        100: "---|",
    }

class IbmFm(disk.DiskFormat):

    ''' IBM format 8" floppy disks '''

    #FIRST_CHS = (0, 0, 1)
    #LAST_CHS = (76, 1, 26)
    #SECTOR_SIZE = 128

    ADDRESS_MARK = (0xc7, 0xfe)
    DATA_MARK = (0xc7, 0xfb)
    DELETE_MARK = (0xc7, 0xf8)
    GAP1 = 16
    MAX_GAP2 = 50

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.geometry = [False] * 4

    def add_geometry(self, chs, length, mfm):
        if chs[0] == 0 and chs[1] == 0:
            index = 0
        elif chs[0] == 0 and chs[1] == 1:
            index = 1
        elif chs[1] == 0:
            index = 2
        else:
            index = 3
        if self.geometry[index]:
            return
        if length == 128 and not mfm:
            nsec = 26
        elif length == 256 and not mfm:
            nsec = 15
        elif length == 256 and mfm:
            nsec = 26
        elif length == 512 and not mfm:
            nsec = 8
        elif length == 512 and mfm:
            nsec = 15
        elif length == 1024 and mfm:
            nsec = 8
        else:
            print("Cannot figure out geometry", chs, length, mfm)
            return
        if chs[0] == 0:
            r = range(1)
        else:
            r = range(1, 77)
        for c in r:
            for s in range(1, nsec + 1):
                self.media.define_sector((c, chs[1], s))
        self.geometry[index] = True
        if False not in self.geometry:
            self.media.defined_geometry = True

    def cached_sector(self, read_sector):
        ''' ... '''
        self.media.add_sector(read_sector)
        self.add_geometry(
            read_sector.chs,
            len(read_sector.octets),
            read_sector.extra == "mfm"
        )

    def validate_address_mark(self, address_mark):
        ''' ... '''

        return self.validate_chs(address_mark[1:4])

    def process(self, stream):
        ''' ...  '''

        fm_am_pattern = '|---' * self.GAP1 + stream.make_mark(*self.ADDRESS_MARK)

        mfm_am_pattern = '|-' * 32
                         #  1 0 1 0 0 0 0 1 1 0 1 0 0 0 0 1   xa1a1
        mfm_am_pattern += '-|---|--|---|--|-|---|--|---|--|'
                         #  1 0 1 0 0 0 0 1 1 1 1 1 1 1 1 0   xa1fe
        mfm_am_pattern += '-|---|--|---|--|-|-|-|-|-|-|-|--'

        flux = fluxstream.ClockRecoveryFM().process(stream.iter_dt())
        am_list = list(stream.iter_pattern(flux, pattern=fm_am_pattern))

        if len(am_list) > 0:
            print("FM", len(am_list))
            sys.stdout.flush()
            yield from self.fm_process(stream, flux, am_list)
            return
    
        flux = MfmRecovery().process(stream.iter_dt())

        am_list = list(stream.iter_pattern(flux, pattern=mfm_am_pattern))
        if len(am_list) > 0:
            print("MFM", len(am_list))
            sys.stdout.flush()
            self.fm_first = False
            yield from self.mfm_process(stream, flux, am_list)
            return

    def mfm_process(self, stream, flux, am_list):

        data_pattern = '|-' * 32
                       #  1 0 1 0 0 0 0 1 1 0 1 0 0 0 0 1   xa1a1
        data_pattern += '-|---|--|---|--|-|---|--|---|--|'

        for am_pos in am_list:
            address_mark = stream.flux_data_mfm(flux[am_pos-64:am_pos+(6*16)])
            if address_mark is None:
                #print("NOAM", am_pos)
                continue

            am_crc = crc_func(address_mark)
            if am_crc:
                #print("AMCRC", "%04x" % am_crc, address_mark.hex())
                continue

            chs = self.validate_address_mark(address_mark[3:])
            if chs is None:
                print("CHS", address_mark.hex())
                continue

            data_pos = flux.find(data_pattern, am_pos)
            if data_pos < 0:
                #print("NO DATA_POS", am_pos)
                continue
            if data_pos > am_pos + self.MAX_GAP2 * 16:
                #print("DP>", data_pos - am_pos)
                continue
            data_pos += len(data_pattern)

            sector_size = 128 << address_mark[7]

            off = -2*16
            width = (6 + sector_size) * 16
            data = stream.flux_data_mfm(flux[data_pos+off:data_pos+width+off])
            if data is None:
                #print("NO DATA", am_pos, data_pos, data_pos - am_pos)
                continue

            data_crc = crc_func(data)

            if data_crc:
                #print("DCRC", "%04x" % data_crc, data[:16].hex(), data[-16:].hex())
                continue

            self.add_geometry(chs, sector_size, True)
            yield disk.Sector(
                chs,
                data[1:sector_size+1],
                source=stream.filename,
                extra="mfm",
            )

    def fm_process(self, stream, flux, am_list):
        data_pattern = '|---' * self.GAP1 + stream.make_mark(*self.DATA_MARK)
        delete_pattern = '|---' * self.GAP1 + stream.make_mark(*self.DELETE_MARK)

        for am_pos in am_list:
            address_mark = stream.flux_data_fm(flux[am_pos-32:am_pos+(6*32)])
            if address_mark is None:
                continue

            am_crc = crc_func(address_mark)
            if am_crc:
                continue

            chs = self.validate_address_mark(address_mark)
            if chs is None:
                continue

            for pattern in (data_pattern, delete_pattern):
                data_pos = flux.find(pattern, am_pos)
                if data_pos < 0:
                    continue
                if data_pos < am_pos + self.MAX_GAP2 * 32:
                    data_pos += len(pattern)
                    break
                data_pos = -1
            if data_pos < 0:
                continue

            sector_size = 128 << address_mark[4]

            data = stream.flux_data_fm(flux[data_pos-32:data_pos+((2+sector_size)*32)])
            if data is None:
                continue

            data_crc = crc_func(data)
            if data_crc:
                continue

            self.add_geometry(chs, sector_size, False)
            yield disk.Sector(
                chs,
                data[1:sector_size+1],
                source=stream.filename,
                extra="fm",
            )

class IbmFm128Ss(IbmFm):
    ''' ... '''
    #FIRST_CHS = (0, 0, 1)
    #LAST_CHS = (76, 1, 26)
    #SECTOR_SIZE = 128

class IbmFm128Ds(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 26)
    SECTOR_SIZE = 128

class IbmFm256Ss(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 15)
    SECTOR_SIZE = 256

class IbmFm256Ds(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 15)
    SECTOR_SIZE = 256

class IbmFm512Ss(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 8)
    SECTOR_SIZE = 512

class IbmFm512Ds(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 8)
    SECTOR_SIZE = 512

ALL = (
    IbmFm128Ss,
    #IbmFm128Ds,
    #IbmFm256Ss,
    #IbmFm256Ds,
    #IbmFm512Ss,
    #IbmFm512Ds,
)

if __name__ == "__main__":
    main.Main(*ALL)
