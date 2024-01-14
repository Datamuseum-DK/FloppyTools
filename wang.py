
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
            if 75 <= j < 125:
                b.append('--')
            elif 25 < j < 75:
                b.append('#')
            else:
                b.append(' ')
            l = x
        self.b = ''.join(b)

    def iter_sec(self, tn):
        gaplen = 96
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
            x = self.b[j + pfxlen: j + pfxlen + 5100]
            if len(x) > 4900:
                yield j, x
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
    #print("\x1b[2J")
    log = open(args[1] + ".log", "w")
    for pattern in args[2:]:
        rdg = floppy.Reading(flp, pattern)
        flp.add_reading(rdg)
        for fn in sorted(glob.glob(pattern + "/*57.0.raw")):
            #print("\x1b[H")
            #flp.status()
        
            tn = int(fn.split("bin")[1][:2])
            print("FN", fn, tn)
            ws = WangStream(fn)

            ws.tobits()
            for idx, bits in ws.iter_sec(tn):
                #print("B %5d" % len(bits), idx, bits)
                bhdr = bits[:128]
                bgap = bits[128:270]
                bdata = bits[270:]
    
                hdr = octets(bhdr)
                if sum(hdr[2:]):
                    # False address mark, ignore
                    continue
    
                p = '-' * 32 + '####'
                i = bdata.find(p)
                if i < 0:
                    print("No sync2", bdata)
                    #print("  h", bhdr)
                    #print("  g", bgap)
                    #print("  b", bdata)
                    continue
                o = octets(bdata[i+4+8*2:])
                if len(o) < 260:
                    continue
                    print("Short", len(bits), len(bdata), i, len(o), bdata)
                    #print("  h", bhdr)
                    #print("  g", bgap)
                    #print("  b", bdata[i+4+8*2:])
                    #print("  o", hdr.hex(), o.hex())
                    continue
                field = o[:259]
                csum = crc_func(field)
                if csum != 0:
                    print("Bad CRC", hex(csum))
                    #print("  h", bhdr)
                    #print("  g", bgap)
                    #print("  b", bdata[i+4+8*2:])
                    #print("  o", hdr.hex(), o.hex())
                    log.write("CRC " + hdr.hex() + " " + bdata[i+4+8*2:] + "\n")
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
    log.close()
    flp.write_bin(args[1] + ".flp", 256)

if __name__ == "__main__":
    main(sys.argv)
