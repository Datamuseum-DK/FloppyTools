#/usr/bin/env python3

'''
   DEC RX01/RX02 formats
   ~~~~~~~~~~~~~~~~~~~~~
'''

import crcmod

import sector
import main
import disk

crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class DecRx02(disk.DiskFormat):

    ''' IBM format 8" floppy disks '''

    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 26)
    SECTOR_SIZE = 128

    ADDRESS_MARK = (0xc7, 0xfe)
    DATA_MARK = (0xc7, 0xfb)
    HDDATA_MARK = (0xc7, 0xfd)
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
        hddata_pattern = '|---' * self.GAP1 + self.stream.make_mark(*self.HDDATA_MARK)
        delete_pattern = '|---' * self.GAP1 + self.stream.make_mark(*self.DELETE_MARK)

        flux = self.stream.flux_250_mfm()

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

            for pattern, density, dm_value in (
                (data_pattern, 0, 0xfb),
                (hddata_pattern, 1, 0xfd),
                (delete_pattern, 0, 0xf8)
            ):
                data_pos = flux.find(pattern, am_pos)
                if data_pos < 0:
                    continue
                if data_pos < am_pos + self.MAX_GAP2 * 4:
                    data_pos += len(pattern)
                    break
                data_pos = -1
            if data_pos < 0:
                continue
 
            if density:
                datalen = (2 + 2 * self.SECTOR_SIZE) * 16
                data_flux = flux[data_pos:data_pos+datalen]
                if ' ' in data_flux:
                    continue
                l = []
                for i in range(1, len(data_flux), 4):
                    j = data_flux[i:i+3]
                    l.append(
                        {
                        "---": "11",
                        "--|": "01",
                        "-|-": "00",
                        "-||": "d",
                        "|--": "10",
                        "|-|": "11",
                        "||-": "g",
                        "|||": "h",
                        }[j]
                    )
                l = "".join(l)
                j = [dm_value]
                for i in range(0, len(l), 8):
                    j.append(int(l[i:i+8], 2))
                data = bytes(j)
                data_crc = crc_func(data)
            else:
                datalen = (2 + self.SECTOR_SIZE) * 32
                data = self.stream.flux_data_fm(flux[data_pos-32:data_pos+datalen])
                data_flux = ''
                if data is None:
                    continue
                data_crc = crc_func(data)


            i = []
            for j in data:
                if 32 <= j <= 126:
                    i.append("%c" % j)
                else:
                    i.append('…')
            # print(address_mark.hex(), "%02x" % dm_value, "%04x" % data_crc, data[-2:].hex(), len(data), ["".join(i)])

            if data_crc:
                #print(data.hex())
                #print(data_flux)
                continue

            yield sector.Sector(
                chs,
                data[1:self.SECTOR_SIZE+1],
                True,
                self.source
            )

class DecRx02128Ss(DecRx02):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 26)
    SECTOR_SIZE = 128

class DecRx02128Ds(DecRx02):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 26)
    SECTOR_SIZE = 128

class DecRx02256Ss(DecRx02):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 15)
    SECTOR_SIZE = 256

class DecRx02256Ds(DecRx02):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 15)
    SECTOR_SIZE = 256

class DecRx02512Ss(DecRx02):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 8)
    SECTOR_SIZE = 512

class DecRx02512Ds(DecRx02):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 8)
    SECTOR_SIZE = 512

if __name__ == "__main__":
    main.Main(DecRx02)
