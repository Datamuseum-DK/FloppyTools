#!/usr/bin/env python3

'''
   Take a KryoFlux stream file apart
   ---------------------------------
'''

import struct
import crcmod

import fluxstream

crc16_func = crcmod.predefined.mkCrcFun('crc-16-buypass')

#sck=24027428.5714285
#ick=3003428.5714285625

class NotAKryofluxStream(Exception):
    ''' ... '''

class KryoStream(fluxstream.FluxStream):
    ''' A Kryoflux Stream file '''
    def __init__(self, filename):
        i = filename.split('.')
        if i[-1] != 'raw':
            raise NotAKryofluxStream("Does not end in ….raw")
        if not i[-2].isdigit():
            raise NotAKryofluxStream("Does not end in ….%d.raw")
        if not i[-3][3:].isdigit():
            raise NotAKryofluxStream("Does not end in …bin%d.%d.raw")
        if i[-3][:3] != "bin":
            raise NotAKryofluxStream("Does not end in …bin%d.%d.raw")
        self.chs = (int(i[-3][3:]), int(i[-2]), None)

        self.filename = filename
        self.flux = {}
        self.strm = {}
        self.index = []
        self.oob = []
        self.stream_end = None
        self.result_code = None
        self.sck = None
        self.ick = None

        self.deframe()
        if hasattr(self, "kfinfo_sck"):
            self.sck = float(self.kfinfo_sck)
        if hasattr(self, "kfinfo_ick"):
            self.ick = float(self.kfinfo_ick)

    def __str__(self):
        return "<KryoStream " + self.filename + ">"

    def __lt__(self, other):
        return self.filename < other.filename

    def iter_dt(self):
        last = 0
        for i in self.strm.values():
            yield i - last
            last = i

    def do_index(self):
        for idx in self.index:
            samp = self.strm.get(idx[3])
            yield samp - idx[4]

    def handle_oob(self, _strm, oob):
        if oob[1] == 2:
            i = struct.unpack("<BBHLLL", oob)
            self.index.append(i)
        elif oob[1] == 3:
            i = struct.unpack("<BBHLL", oob)
            self.stream_end = i[3]
            self.result_code = i[4]
        elif oob[1] == 4:
            txt = oob[4:-1].decode("utf-8")
            for fld in txt.split(", "):
                i = fld.split('=', 1)
                setattr(self, "kfinfo_" + i[0], i[1])

    def deframe(self):
        samp = 0
        strm = 0
        idx = 0
        octets = open(self.filename, "rb").read()
        while idx < len(octets):
            blkhd = octets[idx]
            if blkhd <= 0x07:
                i = octets[idx] * 256 + octets[idx + 1]
                samp += i
                self.flux[samp] = strm
                self.strm[strm] = samp
                idx += 2
                strm += 2
            elif blkhd == 0x08:
                # NOP1 ignore
                idx += 1
                strm += 1
            elif blkhd == 0x09:
                # NOP2 ignore
                idx += 2
                strm += 2
            elif blkhd == 0x0a:
                # NOP3 ignore
                idx += 3
                strm += 3
            elif blkhd == 0x0b:
                # +64K clocks
                idx += 1
            elif blkhd == 0x0d:
                i = struct.unpack("<BBH", octets[idx:idx+4])
                self.handle_oob(strm, octets[idx: idx + 4 + i[2]])
                idx += 4 + i[2]
            elif 0xe <= blkhd <= 0xff:
                i = idx
                while i < len(octets) and 0xe <= octets[i] <= 0xff:
                    samp += octets[i]
                    self.flux[samp] = strm
                    self.strm[strm] = samp
                    i += 1
                    strm += 1
                idx = i
            else:
                print ("?", blkhd, self.filename)
                idx += 1
                break
