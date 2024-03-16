
'''
	742-0652_928_Sys-10-20-30_Vol3_Theory_Of_Operation_19840817.pdf
		pg 73

'''
import crcmod

import fm_mod
import sector
import main
import disk

crc_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

AM_GAP = '--' * 32 + '##' * 2
DATA_GAP = '--' * 24 + '##' * 2

class WangWcs(disk.DiskFormat):

    ''' WANG WCS format 8" floppy disks '''

    FIRST_CHS = (0, 0, 0)
    LAST_CHS = (76, 0, 15)
    SECTOR_SIZE = 256

    def process(self):
        if self.stream.chs[1] not in (0, None):
            return
        fm = self.stream.to_fm_250()

        for sync in self.stream.iter_gaps(fm, gap=AM_GAP):
            amark = fm_mod.tobytes(fm[sync:sync+6*16])
            if amark is None:
                continue
            if max(amark[2:]):
                continue

            cyl_nbr = amark[0]
            if cyl_nbr > 76:
                continue
            if self.stream.chs[0] not in (cyl_nbr, None):
                continue

            sector_nbr = amark[1]
            if sector_nbr > 0xf:
                continue

            dsync = fm.find(DATA_GAP, sync + 260)
            if dsync < 0 or sync + 400 < dsync:
                continue
            dsync += len(DATA_GAP)
            data = fm_mod.tobytes(fm[dsync:dsync+258*16])
            if data is None:
                print(amark.hex(), "NDATA")
                continue
            dsum = crc_func(data)
            if dsum != 0x3f30:
                print(amark.hex(), "CRC", hex(dsum))
                continue

            yield sector.Sector(
                (cyl_nbr, 0, sector_nbr),
                data[:256],
                True,
                self.source
            )

if __name__ == "__main__":
    main.Main(WangWcs)
