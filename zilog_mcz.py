#/usr/bin/env python3

'''
   Zilog MCZ/1 8" floppies
   ~~~~~~~~~~~~~~~~~~~~~~~

   ref: 03-3018-03_ZDS_1_40_Hardware_Reference_Manual_May79.pdf
'''

import crcmod

import fm_mod
import sector
import main
import disk

crc16_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

class ZilogMCZ(disk.DiskFormat):

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (77, 0, 31)
    SECTOR_SIZE = 136

    def process(self):
        if self.stream.chs[1] not in (0, None):
            return
        fm = self.stream.to_fm_250()
        for sync in self.stream.iter_gaps(fm, minlen=136):
            sync -= 2
            data = fm_mod.tobytes(fm[sync:sync+16*136])
            if data is None:
                continue
            csum = crc16_func(data)
            if csum != 0:
                continue
            sector_nbr = data[0] & 0x7f
            if sector_nbr > 31:
                continue
            cyl_nbr = data[1]
            if cyl_nbr > 77:
                continue
            if self.stream.chs[0] not in (cyl_nbr, None):
                continue
            yield sector.Sector(
                (cyl_nbr, 0, sector_nbr),
                data,
                True,
                self.source,
            )

if __name__ == "__main__":
    main.Main(ZilogMCZ)
