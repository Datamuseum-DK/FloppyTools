#/usr/bin/env python3

'''
   DEC RX01/RX02 formats
   ~~~~~~~~~~~~~~~~~~~~~
'''

import crcmod

from . import main
from . import disk
from . import fluxstream as fs

crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class DecRx02(disk.DiskFormat):

    ''' IBM format 8" floppy disks '''

    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 26)
    SECTOR_SIZE = 256

    ADDRESS_MARK = (0xc7, 0xfe)
    HDDATA_MARK = (0xc7, 0xfd)
    GAP1 = 32
    DATA_WIN_LO = 550
    DATA_WIN_HI = 800

    def validate_address_mark(self, address_mark):
        ''' ... '''

        return self.validate_chs(address_mark[1:4])

    def process(self, stream):
        ''' ...  '''

        am_pattern = '|---' * self.GAP1 + fs.make_mark_fm(*self.ADDRESS_MARK)
        hddata_pattern = '|---' * self.GAP1 + fs.make_mark_fm(*self.HDDATA_MARK)

        flux = stream.mfm_flux()

        for am_pos in stream.iter_pattern(flux, pattern=am_pattern):

            address_mark = stream.flux_data_fm(flux[am_pos-32:am_pos+(6*32)])
            #print("AM", address_mark.hex(), flux[am_pos-32:am_pos+(6*32)])
            if address_mark is None:
                continue

            am_crc = crc_func(address_mark)
            if am_crc:
                continue

            chs = self.validate_address_mark(address_mark)
            if chs is None:
                continue

            data_pos = flux.find(
                hddata_pattern,
                am_pos + self.DATA_WIN_LO,
                am_pos + self.DATA_WIN_HI
            )
            if data_pos < 0:
                continue
            data_pos += len(hddata_pattern)

            data_flux = flux[data_pos:data_pos+(2 + self.SECTOR_SIZE) * 16 + 32]
            if ' ' in data_flux:
                continue

            data = bytes([0xfd]) + self.flux_to_bytes(data_flux[1:])

            data_crc = crc_func(data)
            if not data_crc:
                yield disk.Sector(chs, data[1:self.SECTOR_SIZE+1])

    def flux_to_bytes(self, flux):
        ''' RX02 uses a modified MFM encoding '''
        l = []
        i = 0
        fflux = flux + '||||||||||||||||'
        while i < 2*(2+self.SECTOR_SIZE)*8:
            if fflux[i] == '|':
                j = '1'
            elif fflux[i:i+10] == '-|---|---|':
                j = '01111'
            else:
                j = '0'
            l.append(j)
            i += len(j) * 2
        l = "".join(l)
        j = []
        for i in range(0, len(l), 8):
            j.append(int(l[i:i+8], 2))
        data = bytes(j)
        return data

if __name__ == "__main__":
    main.Main(DecRx02)
