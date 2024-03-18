#/usr/bin/env python3

'''
   Data General Nova 8" floppy disks
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import main
import disk
import fluxstream

class DataGeneralNova(disk.DiskFormat):

    ''' Data General Nova 8" floppy disks '''

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (76, 0, 7)
    SECTOR_SIZE = 512

    GAP1 = '|---' * 16 + '|-|-'
    GAP2 = '|---' * 2 + '|-|-'

    def process(self, stream):
        if not self.validate_chs(stream.chs, none_ok=True):
            return

        flux = fluxstream.ClockRecoveryFM().process(stream.iter_dt())

        for am_pos in stream.iter_pattern(flux, pattern=self.GAP1):
            address_mark = stream.flux_data_fm(flux[am_pos:am_pos+2*32])
            if address_mark is None:
                continue

            chs = self.validate_chs(
                (address_mark[0], 0, address_mark[1]>>2),
                stream=stream,
            )
            if not chs:
                continue

            data_pos = flux.find(self.GAP2, am_pos + 5*32)
            if data_pos < 0 or data_pos - am_pos > 10*32:
                continue
            data_pos += len(self.GAP2)

            data = stream.flux_data_fm(flux[data_pos:data_pos+((2+self.SECTOR_SIZE)*32)])
            if data is None or len(data) < self.SECTOR_SIZE+2:
                continue


            data_crc = self.bogo_crc(data[:self.SECTOR_SIZE])
            disc_crc = (data[self.SECTOR_SIZE]<<8) | data[self.SECTOR_SIZE + 1]
            if data_crc != disc_crc:
                continue

            yield disk.Sector(
                chs,
                data[:self.SECTOR_SIZE],
                source=stream.filename,
            )

    def bogo_crc(self, data):
        '''
           The worlds second worst CRC-16 algorithm
           ========================================

           Meet the worlds second-worst CRC-16 error detection function:
          
           x16 + x8 +1 aka 0x8080 aka 0x10101
         
           See page 1, top left corner of:
           http://bitsavers.org/pdf/dg/disc/4046_4047_4049/4046_4047_schematic.pdf
          
           This CRC16 has staggeringly bad performance according to Prof. Koopman:
           0x8080  HD=3  len=8  Example: Len=9 {0} (0x8000) (Bits=2)
           0x8080  HD=4  NONE  Example: Len=1 {0} (0x8080) (Bits=3)
          
           For comparison the standarized CCITT CRC16 has:
           0x8810  HD=3  len=32751  Example: Len=32752 {0} (0x8000) (Bits=2)
           0x8810  HD=4  len=32751  Example: Len=32752 {0} (0x8000) (Bits=2)
           0x8810  HD=5  NONE  Example: Len=1 {0} (0x8810) (Bits=4)
          
           But it is even worse than that, bceause it does not even detect
           all two-bit errors, both of these inputs gets the result 0x0100:
          
               0x01 0x00 0x00 0x00
               0x00 0x00 0x00 0x01
          
           Because the tap is between the two bytes of the CRC, the function
           reduces to the following:
        '''

        crc = 0
        for n, b in enumerate(data):
            if (n % 3) == 0:
                crc ^= b
                crc ^= b << 8
            elif (n % 3) == 1:
                crc ^= b
            else:
                crc ^= b << 8

        return crc

if __name__ == "__main__":
    main.Main(DataGeneralNova)
