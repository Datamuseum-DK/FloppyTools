
'''
	742-0652_928_Sys-10-20-30_Vol3_Theory_Of_Operation_19840817.pdf
		pg 73

'''
import sys
import glob
import kryostream

import crcmod

import floppy

crc_func = crcmod.predefined.mkCrcFun('modbus')
crc_func = crcmod.predefined.mkCrcFun('xmodem')
crc_func = crcmod.predefined.mkCrcFun('crc-16-buypass')


class WangStream(kryostream.KryoStream):
    ''' ... '''

    def tobits(self):
        l = 0
        b = []
        for _i, j in sorted(self.strm.items()):
            x = j
            j -= l
            if 75 < j < 125:
                b.append('--')
            elif 25 < j < 75:
                b.append('#')
            else:
                b.append(' ')
            l = x
        self.b = ''.join(b)

    def iter_sec(self, tn):
        gaplen = 128
        p = '-' * gaplen + '####'
        pfxlen = len(p)
        i = bin(256|tn)[3:]
        for j in i:
            if j == '0':
                p += '--'
            else:
                p += '##'
        i = 0
        while True:
            j = self.b.find(p, i)
            if j < 0:
                return
            yield j, self.b[j + pfxlen: j + pfxlen + 5100]
            i = j + 1

def octets(s):

    l = []
    for i in range(0, len(s) - 15, 16):
        o = 0
        for j in range(0, 16, 2):
            o <<= 1
            if s[i+j:i+j+2] == '##':
                o += 1
        l.append(o)
    return bytes(l)

def main(args):
    flp = floppy.Floppy(77, 1, 16)
    flp.sect0 = 0
    for pattern in args[1:]:
        rdg = floppy.Reading(flp, pattern)
        flp.add_reading(rdg)
        for fn in sorted(glob.glob(pattern)):
        
            tn = int(fn.split("bin")[1][:2])
            print("FN", fn, tn)
            ws = WangStream(fn)

            ws.tobits()
            for idx, bits in ws.iter_sec(tn):
                bhdr = bits[:128]
                bgap = bits[128:280]
                bdata = bits[280:]
    
                hdr = octets(bhdr)
    
                p = '-' * 32 + '####'
                i = bdata.find(p)
                if i < 0:
                    print("No sync2", bdata)
                    continue
                o = octets(bdata[i+4+8*2:])
                field = o[:259]
                csum = crc_func(field)
                if csum != 0:
                    print("Bad CRC", bdata[i:])
                    continue
                data = field[1:257]
                rdg.read_sector(
                    floppy.ReadSector(
                        hdr[0],
                        0,
                        hdr[1],
                        data,
                        csum == 0
                    )
                )
        flp.status()
    flp.write_bin("/tmp/_wang.flp", 256)

main(
    [
        "",
        "/critter/DDHF/20231130_Wang/fiks11/*.0.raw",
        "/critter/DDHF/20231207_Wang/wang0/*.0.raw",
        "/critter/DDHF/20231207_Wang/wang1/*.0.raw",
    ]
)
