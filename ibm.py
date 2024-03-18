#/usr/bin/env python3

'''
   IBM format
   ~~~~~~~~~~
'''

import crcmod

import main
import disk
import fluxstream

crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class IbmFm(disk.DiskFormat):

    ''' IBM format 8" floppy disks '''

    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 26)
    SECTOR_SIZE = 128

    ADDRESS_MARK = (0xc7, 0xfe)
    DATA_MARK = (0xc7, 0xfb)
    DELETE_MARK = (0xc7, 0xf8)
    GAP1 = 16
    MAX_GAP2 = 250

    def validate_address_mark(self, address_mark):
        ''' ... '''

        return self.validate_chs(address_mark[1:4])

    def process(self, stream):
        ''' ...  '''

        am_pattern = '|---' * self.GAP1 + stream.make_mark(*self.ADDRESS_MARK)
        data_pattern = '|---' * self.GAP1 + stream.make_mark(*self.DATA_MARK)
        delete_pattern = '|---' * self.GAP1 + stream.make_mark(*self.DELETE_MARK)

        flux = fluxstream.ClockRecoveryFM().process(stream.iter_dt())

        for am_pos in stream.iter_pattern(flux, pattern=am_pattern):
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
                if data_pos < am_pos + self.MAX_GAP2 * 4:
                    data_pos += len(pattern)
                    break
                data_pos = -1
            if data_pos < 0:
                continue

            data = stream.flux_data_fm(flux[data_pos-32:data_pos+((2+self.SECTOR_SIZE)*32)])
            if data is None:
                continue

            data_crc = crc_func(data)
            if data_crc:
                continue

            yield disk.Sector(
                chs,
                data[1:self.SECTOR_SIZE+1],
                source=stream.filename,
            )

class IbmFm128Ss(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 26)
    SECTOR_SIZE = 128

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
