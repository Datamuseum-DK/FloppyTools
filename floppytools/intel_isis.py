
'''
   Decode Intel ISIS double density 8" floppies
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import crcmod

import main
import disk
import fluxstream as fs

crc_func = crcmod.predefined.mkCrcFun('xmodem')

class IntelIsis(disk.DiskFormat):

    ''' Intel ISIS format 8" floppy disks '''

    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 52)
    SECTOR_SIZE = 128

    def validate_address_mark(self, address_mark):
        ''' ... '''

        return self.validate_chs(address_mark[1:4])

    def process(self, stream):
        ''' ...  '''

        if not self.validate_chs(stream.chs, none_ok=True):
            print("Ignoring", stream)
            return

        am_pattern =   '|-' * 16 + fs.make_mark(0x87, 0x70)
        data_pattern =   '|-' * 16 + fs.make_mark(0x85, 0x70)

        flux = stream.m2fm_flux()

        for am_pos in stream.iter_pattern(flux, pattern=am_pattern):

            am_flux = flux[am_pos-16:am_pos+(7*16)]
            address_mark = stream.flux_data_mfm(am_flux[1:])
            if address_mark is None:
                continue

            am_crc = crc_func(address_mark)
            if am_crc:
                continue

            chs = self.validate_address_mark(address_mark)
            if chs is None:
                continue

            data_pos = flux.find(data_pattern, am_pos + 200)
            if data_pos < 0:
                continue
            if data_pos > am_pos + 1000:
                continue

            data_pos += len(data_pattern)
            data_pos -= 16

            #print(flux[data_pos-100:data_pos+16])
            data_flux = flux[data_pos:data_pos+(132*16)]
            data = stream.flux_data_mfm(data_flux[1:])
            if data is None:
                continue

            data_crc = crc_func(data[:131])
            if data_crc:
                continue

            yield disk.Sector(
                chs,
                data[1:self.SECTOR_SIZE+1],
                source=stream.filename,
            )

if __name__ == "__main__":
    main.Main(IntelIsis)
