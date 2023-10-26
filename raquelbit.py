
import struct
import glob
import sys

import floppy

def crc16_ccitt(crc, data):
    msb = crc >> 8
    lsb = crc & 255
    for c in data:
        #x = ord(c) ^ msb
        x = c ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
        lsb = (x ^ (x << 5)) & 255
    return (msb << 8) + lsb

def decode(s):
    t = ""
    while s:
        assert s[0] == "1"
        t += s[1]
        s = s[2:]
    return t

def hexdecode(s):
    t = []
    x = decode(s)
    b = []
    while len(x) > 7:
        b.append(int(x[:8], 2))
        t.append("%02x" % b[-1])
        x = x[8:]
    print(x)
    # assert not x
    if b:
        print(b)
        b = bytes([0xfe]) + bytes(b)
        print("CRC1-2 %04x" % crc16_ccitt(0xffff, b[:-2]))
    return " ".join(t)  + x

def bits2bytes(s):
    # assert not len(s) & 15
    b = []
    for o in range(0, len(s), 16):
        t = ""
        for i in range(0, 16, 2):
            if s[o + i] != "1":
                print("Missing clock")
                print(s)
                print(" " * (o+i) + "^" + " " * (len(s) - i))
                #raise Exception("Missing clock")
                s = s[:o+i] + "1" + s[o + i:]
            t += s[o + i + 1]
        b.append(int(t, 2))
    return bytes(b)

ADDRESSMARKS = {}

class AddressMark():

    def __init__(self, name, data, clock):
        self.name = name
        ADDRESSMARKS[name] = self
        self.data = data
        self.clock = clock
        t = ""
        m = 0x80
        while m:
            t += "1" if self.clock & m else "0"
            t += "1" if self.data & m else "0"
            m = m >> 1
        self.bits = t
        print(self.name, "%02x" % self.data, "%02x" % self.clock, t)

IXAM = AddressMark("IXAM", 0xfc, 0xd7)
IDAM = AddressMark("IDAM", 0xfe, 0xc7)
DAM = AddressMark("DAM", 0xfb, 0xc7)
DDAM = AddressMark("DDAM", 0xf8, 0xc7)

class RaquelBitCylinder():

    def __init__(self, up, nbr, raw):
        self.up = up
        self.nbr = nbr
        self.raw = raw
        self.bits = []
        for i in raw:
            if not i:
                continue
            for j in range(7, -1, -1):
                self.bits.append("01"[(i >> j) & 1])
        self.bits = "".join(self.bits)
        print("CYL", nbr, len(raw), len(self.bits))
        self.decode()

    def decode(self):

        prev = 0
        b = self.bits.split(IDAM.bits)
        print("IDAM-split", len(b))
        for i in b[1:]:
            sec_id = bits2bytes(i[:96])
            crc = crc16_ccitt(0xffff, bytes([IDAM.data]) + sec_id)
            if crc:
                crca = crc16_ccitt(0xffff, bytes([IDAM.data]) + sec_id[:-2])
                crcb = (sec_id[-2] << 8) | sec_id[-1]
                print("HEADER ERROR:", i[:96], sec_id, "%04x" % crca, "%04x" % crcb, "%04x" % (crca ^ crcb), "CRCERROR")
                continue
            slen = 128 << sec_id[3]
            print("  Cyl %d Head %d Sec %d X %d (= %d)" % (sec_id[0], sec_id[1], sec_id[2], sec_id[3], slen))
            j = i = i[96:]
            i = i[12 * 8 * 2:]
            dd = i.find(DDAM.bits)
            d = i.find(DAM.bits)
            if dd < 0 and d < 0:
                dd = j.find(DDAM.bits)
                d = j.find(DAM.bits)
                k = j.find("0")
                print("    No Data Address Mark", dd, d, i[:180])
                # continue
            if dd > 0 and dd < d:
                print("    Deleted Address Mark", "*" * 20)
                continue
            i = i[d + len(DAM.bits):]
            if len(i) < (slen + 2) * 16:
                print("    Short data, have", len(i), "need", (slen + 2) * 16)
                continue
            data = bits2bytes(i[:(slen + 2) * 16])
            crca = crc16_ccitt(0xffff, bytes([DAM.data]) + data)
            if crca:
                print("    CRC mismatch %04x" % crca)
                continue
            print("  SEC", *sec_id[:3], len(i), len(data), "%04x" % crca)
            flsect = floppy.ReadSector(
                sec_id[0],
                sec_id[1],
                sec_id[2],
                data[:-2],
                True
            )
            self.up.read_sector(flsect)


class RaquelBit(floppy.Reading):

    def read(self):
        print(self.pathname)
        print("-" * len(self.pathname))
        self.img = open(self.pathname, "rb").read()
        self.ncyl, self.nsect, self.nbyte, self.nhd = struct.unpack("<4H", self.img[31:39])
        self.hdr = struct.unpack("<28s3BHHHH10B19sB", self.img[:69])
        # print(self.ncyl, self.nsect, self.nbyte, self.nhd, self.hdr)
        print("HDR", self.hdr)
        self.cylinder = []
        o = 69
        for c in range(self.ncyl):
            ll = struct.unpack("<H", self.img[o:o+2])
            o += 2
            self.cylinder.append(
                RaquelBitCylinder(self, c, self.img[o:o + ll[0] * 2])
            )
            o += ll[0] * 2
        assert o == len(self.img)

