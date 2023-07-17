
'''
   Decode Zilog MCZ/1 floppies from Kryoflux Stream files

   ref: 03-3018-03_ZDS_1_40_Hardware_Reference_Manual_May79.pdf
'''

import sys

import crcmod

import kryostream

# Tolerance of pulse-width, may need tweaking
TOLERANCE = 1.33

crc16_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

class MczStream(kryostream.KryoStream):

    def mcz(self):
        # May need tweaking
        ll = int((2e-6 / TOLERANCE) * self.sck)
        lh = int((2e-6 * TOLERANCE) * self.sck)
        hl = int((4e-6 / TOLERANCE) * self.sck)
        hh = int((4e-6 * TOLERANCE) * self.sck)

        l = 0
        t = [3]
        for _i, j in sorted(self.strm.items()):
            x = j
            j -= l
            if ll <= j <= lh:
                if t[-1] == 2:
                    t[-1] = 1
                else:
                    t.append(2)
            elif hl <= j <= hh:
                t.append(0)
            else:
                t.append(3)
            l = x
        t = "".join("%d" %x for x in t)

        preamble = "0" * 128 + "1"
        while len(t) > (16 + 1 + 1 + 128 + 4 + 2) * 8:
            try:
                y = t.index(preamble)
                t = t[y + len(preamble) - 1:]
            except ValueError:
                break
            t2 = t[:(1 + 1 + 128 + 4 + 2) * 8]
            #print(">", len(t), t2)
            bx = bytearray()
            for z in range(0, len(t2), 8):
                try:
                    bx.append(int(t2[z:z+8], 2))
                except ValueError:
                    pass
            if len(bx) != 136:
                t = t[1:]
                continue
            crc = crc16_func(bx)
            if crc:
                t = t[1:]
                continue
            yield crc, bx
            t = t[1024+64:]

class MCZSector():
    def __init__(self, octets):
        self.octets = octets
        self.adr = (octets[1], octets[0] & 0x7f)
        self.prevadr = (octets[131], octets[130])
        self.nextadr = (octets[133], octets[132])
        self.crc = (octets[134], octets[135])

    def __str__(self):
        t = []
        t.append("%02x,%02x" % self.adr)
        t.append("%02x,%02x" % self.nextadr)
        t.append("%02x,%02x" % self.prevadr)
        return "|".join(t)

    def __eq__(self, other):
        return self.octets == other.octets

    def __lt__(self, other):
        return self.adr < other.adr

    def render(self):
        t = []
        for i in self.octets[2:130]:
            if i == 0:
                t.append("…")
            elif i == 0x09:
                t.append("\t")
            elif i == 0x0a:
                t.append("\\n")
            elif i == 0x0d:
                t.append("\n")
            elif 32 <= i <= 126:
                t.append("%c" %i)
            else:
                t.append("\\%02x" %i)
        return "".join(t)



class MCZ():
    def __init__(self, srcfiles, dstfn):
        self.sectors = {}
        for filename in srcfiles:
            oldlen = len(self.sectors)
            ks = MczStream(filename)
            for crc, octets in ks.mcz():
                if crc or len(octets) != 136:
                    print("C", crc, len(octets))
                    continue
                sec = MCZSector(octets)
                i = self.sectors.get(sec.adr)
                if i and i == sec:
                    continue
                if i:
                    print("DIFF")
                    print("  ", i)
                    print("  ", sec)
                self.sectors[sec.adr] = sec
            nsect = len(self.sectors) - oldlen
            print(nsect, "sectors in", filename)

        print(len(self.sectors), "Total sectors")
        if len(self.sectors) != 78 * 32:
            nmiss = 0
            for cyl in range(78):
                for sect in range(32):
                    if (cyl, sect) not in self.sectors:
                        print("Missing c=%d,s=%d" % (cyl, sect))
                        nmiss += 1
            for sec in sorted(self.sectors.values()):
                if sec.adr[0] >= 78 or sec.adr[1] > 31:
                    print("Extra", sec)
            exit(2)
        with open(dstfn, "wb") as file:
            for cyl in range(78):
                for sect in range(32):
                    sec = self.sectors[(cyl,sect)]
                    file.write(sec.octets)

def main(argv):
    dst = argv.pop(0)
    MCZ(sorted(argv), dst)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.stderr.write('''Usage:
	python3 zilog_mcz.py <destination file> <kryoflux stream files>
''')
        exit(2)
    main(sys.argv[1:])
