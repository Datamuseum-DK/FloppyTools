#/usr/bin/env python3

'''
   IBM format
   ~~~~~~~~~~
'''

import crcmod

import sector
import main
import disk

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

        cyl_nbr = address_mark[1]
        if cyl_nbr > self.LAST_CHS[0]:
            return None
        if self.stream.chs[0] not in (cyl_nbr, None):
            return None

        head_nbr = address_mark[2]
        if head_nbr > self.LAST_CHS[1]:
            return None

        sector_nbr = address_mark[3]
        if sector_nbr < self.FIRST_CHS[2]:
            return None
        if sector_nbr > self.LAST_CHS[2]:
            return None

        return (cyl_nbr, head_nbr, sector_nbr)

    def process(self):
        ''' ...  '''

        am_pattern = '|---' * self.GAP1 + self.stream.make_mark(*self.ADDRESS_MARK)
        data_pattern = '|---' * self.GAP1 + self.stream.make_mark(*self.DATA_MARK)
        delete_pattern = '|---' * self.GAP1 + self.stream.make_mark(*self.DELETE_MARK)

        flux = self.stream.flux_250_fm()

        for am_pos in self.stream.iter_pattern(flux, pattern=am_pattern):
            address_mark = self.stream.flux_data_fm(flux[am_pos-32:am_pos+(6*32)])
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

            data = self.stream.flux_data_fm(flux[data_pos-32:data_pos+((2+self.SECTOR_SIZE)*32)])
            if data is None:
                continue

            data_crc = crc_func(data)
            if data_crc:
                continue

            yield sector.Sector(
                chs,
                data[1:self.SECTOR_SIZE+1],
                True,
                self.source
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
    IbmFm128Ds,
    IbmFm256Ss,
    IbmFm256Ds,
    IbmFm512Ss,
    IbmFm512Ds,
)

if __name__ == "__main__":
    main.Main(*ALL)
