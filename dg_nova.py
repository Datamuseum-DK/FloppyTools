#/usr/bin/env python3

'''
   Data General Nova 8" floppy disks
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import fm_mod
import sector
import main

class DataGeneralNova():

    ''' Data General Nova 8" floppy disks '''

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (76, 0, 7)

    def __init__(self, stream, source):
        self.stream = stream
        self.source = source

    def process(self):
        if self.stream.chs[1] not in (0, None):
            return
        fm = self.stream.to_fm_250()

        for sync in self.stream.iter_gaps(fm, minlen=525):
            if ' ' in fm[sync:sync+32]:
                continue

            cyl_nbr = fm_mod.FM_TO_BIN.get(fm[sync:sync+16])
            if cyl_nbr is None:
                continue
            if cyl_nbr > 76:
                continue
            if self.stream.chs[0] not in (cyl_nbr, None):
                continue

            sector_nbr = fm_mod.FM_TO_BIN.get(fm[sync+16:sync+32])
            if sector_nbr is None:
                continue
            sector_nbr >>= 2
            if sector_nbr > 7:
                continue

            read_gate = 80
            # adr_mark = fm[sync:sync+read_gate]
            data_sync = fm.find("#", sync + read_gate)
            if data_sync < 0:
                continue
            gap2 = data_sync - sync
            if gap2 > 140:
                continue
            data_sync += 2

            data = fm_mod.tobytes(fm[data_sync:data_sync+16*515])
            if data is None:
                continue
            if len(data) != 515:
                continue
            if data[514]:
                print("514", data[514])
                continue

            # Meet the worlds second-worst CRC-16 error detection function:
            #
            # x16 + x8 +1 aka 0x8080 aka 0x10101
            #
            # See page 1, top left corner of:
            # http://bitsavers.org/pdf/dg/disc/4046_4047_4049/4046_4047_schematic.pdf
            #
            # This CRC16 has staggeringly bad performance according to Prof. Koopman:
            # 0x8080  HD=3  len=8  Example: Len=9 {0} (0x8000) (Bits=2)
            # 0x8080  HD=4  NONE  Example: Len=1 {0} (0x8080) (Bits=3)
            #
            # For comparison the standarized CCITT CRC16 has:
            # 0x8810  HD=3  len=32751  Example: Len=32752 {0} (0x8000) (Bits=2)
            # 0x8810  HD=4  len=32751  Example: Len=32752 {0} (0x8000) (Bits=2)
            # 0x8810  HD=5  NONE  Example: Len=1 {0} (0x8810) (Bits=4)
            #
            # But it is even worse than that, bceause it does not even detect
            # all two-bit errors, both of these inputs gets the result 0x0100:
            #
            #     0x01 0x00 0x00 0x00
            #     0x00 0x00 0x00 0x01
            #
            # Because the tap is between the two bytes of the CRC, the function
            # reduces to the following:

            calc_sum = 0
            for n, b in enumerate(data[:512]):
                if (n % 3) == 0:
                    calc_sum ^= b
                    calc_sum ^= b << 8
                elif (n % 3) == 1:
                    calc_sum ^= b
                else:
                    calc_sum ^= b << 8

            disc_sum = (data[512]<<8) | data[513]

            yield sector.Sector(
                (cyl_nbr, 0, sector_nbr),
                data[:512],
                calc_sum == disc_sum,
                self.source
            )

if __name__ == "__main__":
    main.Main(DataGeneralNova)
