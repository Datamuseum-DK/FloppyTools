#!/usr/bin/env python3

'''
   Cache file input/output
   ~~~~~~~~~~~~~~~~~~~~~~~
'''

from . import media_abc

class CacheFile():
    ''' ... '''

    def __init__(self, fname, mode):
        self.fname = fname
        self.mode = mode
        assert mode in ("r", "a")
        self.cache_file = open(fname, mode, encoding="utf8")

    def read(self):
        self.cache_file.seek(0)
        for line in self.cache_file:
            flds = line.split()
            if not flds or flds[0][0] == '#':
                continue

            if flds[0] == "file":
                yield "file", flds[1]
                continue

            assert flds[0] == "sector"
            yield "sector", media_abc.ReadSector(
                source=flds[1],
                rel_pos=int(flds[2]),
                phys_chs=tuple(int(x) for x in flds[3].split(",")),
                am_chs=tuple(int(x) for x in flds[4].split(",")),
                octets=bytes.fromhex(flds[5]),
                flags=flds[6:],
            )

    def write_sector(self, read_sector):
        ''' ... '''

        l = [
            "sector",
            read_sector.source,
            str(read_sector.rel_pos),
            "%d,%d,%d" % read_sector.phys_chs,
            "%d,%d,%d" % read_sector.am_chs,
            read_sector.octets.hex(),
        ] + list(sorted(read_sector.flags))
        self.cache_file.write(" ".join(l) + "\n")
        self.cache_file.flush()

    def write_file(self, filename):
        self.cache_file.write("file " + filename + "\n")
        self.cache_file.flush()
