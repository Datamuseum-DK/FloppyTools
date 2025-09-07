#!/usr/bin/env python3

'''
   Main program for floppy tools
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import os

import time

from . import media_abc
from . import kryostream
from . import chsset
from . import cache_file

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
        # print("DEFGEOM", type(self), self.GEOMETRY)
        if self.GEOMETRY is not None:
            self.define_geometry(*self.GEOMETRY)

        self.cache_file = None
        if load_cache:
            self.read_cache()
        if save_cache:
            self.cache_file = cache_file.CacheFile(self.cache_file_name(), "a")

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

    def bin_file_name(self):
        suf = os.path.basename(self.dirname)
        return self.file_name("." + suf + ".bin")

    def meta_file_name(self):
        return self.bin_file_name() + ".meta"

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

    def did_read_sector(self, source, rel_pos, am_chs, octets, flags=()):
        rs = media_abc.ReadSector(source, rel_pos, am_chs, octets, flags)
        self.add_read_sector(rs)
        return rs

    def add_read_sector(self, read_sector):
        ''' Add a reading of a sector '''
        super().add_read_sector(read_sector)
        if not self.cache_file:
            return
        self.cache_file.write_sector(read_sector)

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
            self.cache_file.write_file(rel_filename)
        return retval

    def read_cache(self):
        try:
             for kind, obj in cache_file.CacheFile(self.cache_file_name(), "r").read():
                 if kind == "file":
                     self.files_done.add(obj)
                 elif kind == "sector":
                     self.add_read_sector(obj)
                 else:
                     assert False
             self.trace("# cache read", self.cache_file_name())
        except FileNotFoundError:
            return

    def metadata_media_description(self):
        yield from []

    def write_result(self, metaproto=""):
        geom = chsset.CHSSet()
        kit = {}
        for ms in sorted(self.sectors.values()):
            maj = ms.find_majority()
            chs = ms.phys_chs
            if maj:
                geom.add(chs, len(maj))
                kit[chs] = maj
            elif ms.has_flag("unused"):
                kit[chs] = b'\x00' * ms.sector_length
                geom.add(chs, ms.sector_length)
            elif ms.has_flag("defined"):
                geom.add(chs, ms.sector_length)
            else:
                # ???
                geom.add(chs, 0)

        badsects = chsset.CHSSet()
        with open(self.bin_file_name(), "wb") as binfile:

            for pr in geom.cuboids():
                assert len(pr.b) == 1
                sector_length = list(pr.b)[0]
                for c,h,s,b in pr:
                    t = kit.get((c,h,s))
                    if t is None:
                        badsects.add((c,h,s), payload=sector_length)
                        fill = (b'_UNREAD_' * (sector_length // 8 + 1))[:sector_length]
                        binfile.write(fill)
                    else:
                        binfile.write(t)

        with open(self.meta_file_name(), "w") as metafile:
            metafile.write("BitStore.Metadata_version:\n")
            metafile.write("\t1.0\n")

            metafile.write("\nBitStore.Access:\n")
            metafile.write("\tpublic\n")
  
            metafile.write("\nBitStore.Filename:\n")
            metafile.write("\t" + self.dirname + ".BIN\n")

            metafile.write("\nBitStore.Format:\n")
            metafile.write("\tBINARY\n")

            metafile.write("\nMedia.Geometry:\n")
            for pr in geom.cuboids():
                for fmt in pr.metadata_format():
                    metafile.write("\t" + fmt + "\n")

            if "Media.Summary:" not in metaproto:
                metafile.write("\nMedia.Summary:\n")
                metafile.write("\t" + self.dirname + "\n")

            if metaproto:
                metafile.write(metaproto)

            if "Media.Description:" not in metaproto:
                metafile.write("\nMedia.Description:\n")

            metafile.write("\tFloppyTools format: " + self.name + "\n")

            for i in self.metadata_media_description():
                metafile.write("\t" + i + "\n")

            if badsects:
                metafile.write("\t\n\tBad (unread) sectors:\n")
                for cl in badsects.cluster():
                    for fmt in cl.metadata_format():
                        metafile.write("\t\t" + fmt + "\n")

            metafile.write("\n*END*\n")
