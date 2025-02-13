#!/usr/bin/env python3

'''
   Main program for floppy tools
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import os

from . import media_abc
from . import kryostream
from . import chsset

class Media(media_abc.MediaAbc):
    ''' A Directory representing a Media '''

    # ((first_c, first_h, first_s), (last_c, last_h, last_s), sector_size)
    GEOMETRY = None

    # Other names or groups this format belongs to.
    aliases = [ ]

    def __init__(self, dirname, load_cache=False, save_cache=False):
        super().__init__()
        self.dirname = dirname
        os.makedirs(self.dirname, exist_ok=True)
        self.medianame = os.path.basename(self.dirname)
        self.files_done = set()
        self.log_files = [
            (True, open("_.trace", "a")),
            (False, open(self.file_name(".trace"), "a")),
        ]
        print("DEFGEOM", type(self), self.GEOMETRY)
        if self.GEOMETRY is not None:
            self.define_geometry(*self.GEOMETRY)

        self.cache_file = None
        if load_cache:
            self.read_cache()
        if save_cache:
            self.cache_file = open(self.cache_file_name(), "a", encoding="utf8")

    def define_geometry(self, first_chs, last_chs, sector_size):
        ''' Define which sectors we expect to find '''
        for c in range(first_chs[0], last_chs[0] + 1, 1):
            for h in range(first_chs[1], last_chs[1] + 1, 1):
                for s in range(first_chs[2], last_chs[2] + 1, 1):
                    self.define_sector((c, h, s), sector_size)

    def defined_chs(self, chs):
        ''' Is this chs defined ? '''
        chs = (chs[0], chs[1], chs[2])
        ms = self.sectors.get(chs)
        if not ms:
            return None
        return ms.has_flag('defined')

    def file_name(self, ext):
        ''' Convenience function to create our file names '''
        return os.path.join(self.dirname, "_.ft." + self.name + ext)

    def cache_file_name(self):
        return self.file_name(".cache")

    def message(self, *args):
        txt = super().message(*args)
        self.trace(txt)

    def trace(self, *args):
        txt = " ".join(str(x) for x in args)
        for pfx, fn in self.log_files:
            if pfx:
                fn.write(self.dirname + ": ")
            fn.write(txt + "\n")
            fn.flush()

    def did_read_sector(self, chs, octets, source, flags=()):
        chs = (chs[0], chs[1], chs[2])
        rs = media_abc.ReadSector(chs, octets, source, flags)
        self.add_read_sector(rs)

    def add_read_sector(self, read_sector):
        ''' Add a reading of a sector '''
        super().add_read_sector(read_sector)
        if not self.cache_file:
            return
        l = ["sector", read_sector.source]
        l += ["%d,%d,%d" % read_sector.chs]
        l += [read_sector.octets.hex()]
        if not read_sector.flags:
            l += ["-"]
        else:
            l += [",".join(sorted(read_sector.flags))]
        self.cache_file.write(" ".join(l) + "\n")
        self.cache_file.flush()

    def process_file(self, streamfilename):
        ''' ... '''

        rel_filename = os.path.relpath(streamfilename, self.dirname)
        if rel_filename in self.files_done:
            self.trace("File already done", streamfilename, rel_filename)
            return False
        self.trace("Process", streamfilename, rel_filename)
        #try:
        if 1:
            stream = kryostream.KryoStream(streamfilename)
        #except kryostream.NotAKryofluxStream:
            #stream = fluxstream.RawStream(streamfilename)
        retval = self.process_stream(stream)
        if retval is None:
            self.trace("Ignored", streamfilename)
            return False
        if retval != None:
            for i in stream.dt_histogram():
                self.trace(i)
        if self.cache_file:
            self.cache_file.write("file " + rel_filename + "\n")
            self.cache_file.flush()
        return retval

    def read_cache_lines(self):
        try:
            with open(self.cache_file_name(), "r", encoding="utf8") as file:
                for line in file:
                    flds = line.split()
                    if len(flds) < 2 or flds[0][0] == '#':
                        continue
                    yield flds
        except FileNotFoundError:
            return

    def read_cache(self):
        for flds in self.read_cache_lines():
            if flds[0] == "file":
                self.files_done.add(flds[1])
            elif flds[0] == "sector":
                chs = tuple(int(x) for x in flds[2].split(","))
                octets = bytes.fromhex(flds[3])
                if flds[4] != '-':
                    flags = flds[4].split(',')
                else:
                    flags = []
                self.did_read_sector(chs, octets, flds[1], flags)
            else:
                print("Invalid cache line")
                print("   ", line)
                exit(2)
        self.trace("# cache read", self.cache_file_name())

    def write_result(self):
        geom = chsset.CHSSet()
        stretch = {}
        for ms in sorted(self.sectors.values()):
            ch = ms.chs[:2]
            if ch not in stretch:
                stretch[ch] = []
            stretch[ch].append(ms)
            if ms.has_flag("defined"):
                geom.add(ms.chs, ms.sector_length)
            else:
                maj = ms.find_majority()
                if maj:
                    geom.add(ms.chs, len(maj))
                else:
                    geom.add(ms.chs, 0)
        print("Geom", self.name)
        #for i in geom.seq():
            # print("G", i)
        for s, v in stretch.items():
            slo = min(x.chs[2] for x in v)
            shi = max(x.chs[2] for x in v)
            #print("S", s, slo, shi, len(v))
        return
        fn = self.file_name(".bin")
        with open(fn, "wb") as file:
           file.write(b'boo')
        return "BIN", fn
