#/usr/bin/env python3

'''
   IBM format
   ~~~~~~~~~~
'''

import crcmod

from ..base import media
from ..base import fluxstream as fs

MFM_LUT = {
    "--|--", #00
    "--|-|", #00
    "|-|--", #00
    "|-|-|", #00
    "|--|-", #01
    "---|-", #01
    "-|---", #10
    "-|--|", #10
    "-|-|-", #11
}


crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class IbmFm(media.Media):

    ''' IBM format 8" floppy disks '''

    #FIRST_CHS = (0, 0, 1)
    #LAST_CHS = (76, 1, 26)
    #SECTOR_SIZE = 128

    FM_ADDRESS_MARK = (0xc7, 0xfe)
    MFM_ADDRESS_MARK = ((0x0a, 0xa1), (0x0a, 0xa1), (0x0a, 0xa1), (0x00, 0xfe))
    DATA_MARK = (0xc7, 0xfb)
    DELETE_MARK = (0xc7, 0xf8)
    GAP1 = 16
    MAX_GAP2 = 100

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
                self.define_sector((c, chs[1], s), length)
        self.geometry[index] = True
        #if False not in self.geometry:
        #    self.media.defined_geometry = True

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

        chs = (address_mark[1], address_mark[2], address_mark[3])
        if chs[0] == 0 and chs[1] == 0 and 1 <= chs[2] <= 8:
            return chs
        if self.defined_chs(chs):
            return chs
        return chs

    def process_stream(self, stream):
        ''' ...  '''


        fm_am_pattern = '|---' * self.GAP1
        fm_am_pattern += fs.make_mark_fm(*self.FM_ADDRESS_MARK)

        mfm_am_pattern = '|-' * 32
        for i in self.MFM_ADDRESS_MARK:
            mfm_am_pattern += fs.make_mark(*i)

        flux = stream.fm_flux()
        am_list = list(stream.iter_pattern(flux, pattern=fm_am_pattern))

        if len(am_list) > 0:
            return self.fm_process(stream, flux, am_list)

        flux = stream.mfm_flux()

        am_list = list(stream.iter_pattern(flux, pattern=mfm_am_pattern))
        if len(am_list) > 0:
            #print("TRY MFM", len(am_list))
            self.fm_first = False
            return self.mfm_process(stream, flux, am_list)

        return False

    def mfm_process(self, stream, flux, am_list):

        data_pattern = '|-' * 16 * 2
                       #  1 0 1 0 0 0 0 1 1 0 1 0 0 0 0 1   xa1a1
        data_pattern += '-|---|--|---|--|-|---|--|---|--|'

        retval = False
        for am_pos in am_list:
            extra = ["mfm"]
            address_mark = stream.flux_data_mfm(flux[am_pos-64:am_pos+(6*16)])
            if address_mark is None:
                print("NOAM", am_pos)
                continue

            am_crc = crc_func(address_mark)

            #if 0 and self.repair and am_crc:
            #    am_crc, address_mark, how = self.mfm_fix(
            #        stream,
            #        flux[am_pos-16:am_pos+(6*16)+6],
            #        7*16,
            #        b'\xa1\xa1\xa1',
            #    )
            #    if am_crc == 0:
            #        extra.append(how)

            if am_crc:
                continue

            chs = self.validate_address_mark(address_mark[3:])
            if chs is None:
                #print("CHS", address_mark.hex())
                continue

            #if self.repair and chs not in self.repair:
            #    continue

            data_pos = flux.find(data_pattern, am_pos + 20 * 16, am_pos + 60 * 16)
            if data_pos < 0:
                #if self.repair:
                #    print(
                #        "REPAIR: NO DATA_POS",
                #        chs,
                #        am_pos,
                #        flux[am_pos + 20 * 16:am_pos + 60 * 16]
                #    )
                #    self.correlate(
                #        flux,
                #        am_pos,
                #        am_pos + 20 * 16,
                #        am_pos + 60 * 16 + len(data_pattern),
                #        data_pattern
                #    )
                continue
            data_pos += len(data_pattern)

            sector_size = 128 << address_mark[7]

            off = -2*16
            width = (6 + sector_size) * 16
            data = stream.flux_data_mfm(flux[data_pos+off:data_pos+width+off])
            if data is None:
                #if self.repair:
                #    print("REPAIR: NO DATA", chs, am_pos, data_pos, data_pos - am_pos)
                continue

            data_crc = crc_func(data)

            #if data_crc and self.repair:
            #    data_crc, data, how = self.mfm_fix(
            #        stream,
            #        flux[data_pos+16:data_pos+width+off+6],
            #        (3 + sector_size) * 16,
            #        b'\xa1\xa1\xa1',
            #    )
            #    if data_crc == 0:
            #        extra.append(how)

            if data_crc:
                #print("DCRC", "%04x" % data_crc, data[:16].hex(), data[-16:].hex())
                continue

            self.add_geometry(chs, sector_size, True)
            self.did_read_sector(chs, data[4:sector_size+4], stream, extra)
            retval = True
        return retval

    def mfm_invalid(self, flux):
        for n in range(0, len(flux)-5, 2):
            if flux[n:n+5] not in MFM_LUT:
                return n
        return -1

    def mfm_fix(self, stream, flux, length, prefix=b''):
        ''' Try to fix invalid MFM flux '''
        n = self.mfm_invalid(flux)
        print("FL %5d %5d %5d" % (n, len(flux), length), flux[:64])
        if n < 0:
            return 0xffff, b'', ""
        for i in range(n + 5, max(n-200, 0), -1):
            if flux[i:i+3] == '--|':
                ftry = flux[:i] + flux[i+1:]
                if self.mfm_invalid(ftry) < 0:
                    d = prefix + stream.flux_data_mfm(ftry[:length])
                    c = crc_func(d)
                    if not c:
                        print("FL REPAIR", "DEL", i, i - n, d[:32].hex())
                        return c, d, "DEL=%d" % i
                    print("FL TRY DEL", "%04x" % c, i - n, d[:32].hex(), ftry[:64])
            if flux[i] == '|':
                ftry = flux[:i] + '-' + flux[i:-2]
                #print("A", flux[i-10:i+10])
                #print("B", ftry[i-10:i+10])
                if self.mfm_invalid(ftry) < 0:
                    d = prefix + stream.flux_data_mfm(ftry[:length])
                    c = crc_func(d)
                    if not c:
                        print("FL REPAIR", "ADD", i, i - n, d[:32].hex())
                        return c, d, "ADR=%d" % i
                    print("FL TRY ADD", "%04x" % c, i - n, d[:32].hex(), ftry[:64])

        return 0xffff, b'', ""

    def correlate(self, flux, ref, start, stop, pattern):
        l = len(pattern)
        peak_i = []
        peak_n = 0
        for i in range(start, stop):
            n = 0
            for a, b in zip(pattern, flux[i:stop]):
                if a == b:
                    n += 1
            if n > peak_n:
                peak_n = n
                peak_i = [i]
            elif n == peak_n:
                peak_i.append(i)
        for i in peak_i:
            print("F", "%6d" % i, "%.4f" % (peak_n / l), flux[i:i+l])
        print("P", "%6d" % 0, "%.4f" % (0), pattern)

    def fm_process(self, stream, flux, am_list):
        data_pattern = '|---' * self.GAP1 + fs.make_mark_fm(*self.DATA_MARK)
        delete_pattern = '|---' * self.GAP1 + fs.make_mark_fm(*self.DELETE_MARK)

        retval = False
        for am_pos in am_list:
            self.trace("am_pos", "FM")
            address_mark = stream.flux_data_fm(flux[am_pos-32:am_pos+(6*32)])
            if address_mark is None:
                self.trace(am_pos, "NOAM")
                continue

            am_crc = crc_func(address_mark)
            if am_crc:
                self.trace(am_pos, address_mark, "AMCRC")
                continue

            chs = self.validate_address_mark(address_mark)
            if chs is None:
                self.trace(am_pos, chs, "INVAL CHS")
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
            self.did_read_sector(
                chs,
                data[1:sector_size+1],
                stream,
                flags=("fm",)
            )
            retval = True
        return retval

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
