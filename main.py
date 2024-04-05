#!/usr/bin/env python3

'''
   Main program for floppy tools
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import sys
import os
import glob
import time

import disk
import kryostream

import zilog_mcz
import dg_nova
import ibm
import dec_rx02
import wang_wcs
import hp98xx

COOLDOWN = 2

import math

def histo(data):
    H = 24

    data = [math.log(max(1,x)) for x in data]
    peak = max(data)
    if peak == 0:
        return

    h = [int(H * x / peak) for x in data]
    
    for j in range(-H, 1, 8):
        t = []
        for i in h:
            r = int(min(max(0, i+j), 8))
            t.append(' ▁▂▃▄▅▆▇█'[r])
        yield "".join(t)


class MediaDir():
    ''' A Directory representing a Media '''

    def __init__(self, dirname, formats=[], load_cache=True, save_cache=True):
        self.dirname = dirname
        os.makedirs(self.dirname, exist_ok=True)
        self.basename = os.path.basename(os.path.abspath(self.dirname))
        self.media = disk.Media()
        self.files_done = set()
        self.cache_file = None
        self.format_classes = formats
        assert len(self.format_classes) > 0
        if load_cache:
            self.read_cache()
        if save_cache:
            self.cache_file = open(self.cache_file_name(), "a")
        self.histo = []

    def add_sector(self, read_sector):
        self.media.add_sector(read_sector)
        if self.cache_file:
            self.cache_file.write(" ".join(
                    [
                        "sector",
                        read_sector.source,
                    ] + read_sector.cache_record()
                ) + "\n"
            )

    def process_file(self, streamfilename, force=False):
        ''' Infer the media format by asking all classes '''
        rel_filename = os.path.relpath(streamfilename, self.dirname)
        if rel_filename in self.files_done and not force:
            # print("##", streamfilename, "(already in cache)")
            return False
        stream = kryostream.KryoStream(streamfilename)
        if self.media.format_class:
            try:
                for read_sector in self.media.format_class.process(stream):
                    read_sector.source = rel_filename
                    self.add_sector(read_sector)
            except disk.NotInterested:
                return False
        else:
            for cls in self.format_classes:
                fmt = cls()
                fmt.media = self.media
                try:
                    read_sectors = list(
                        fmt.process(kryostream.KryoStream(streamfilename))
                    )
                except disk.NotInterested:
                    return False
                if len(read_sectors) == 0:
                    continue
                fmt.define_geometry(self.media)
                if self.cache_file:
                    self.cache_file.write(
                        "format " + fmt.__class__.__name__ + "\n"
                    )
                for read_sector in read_sectors:
                    read_sector.source = rel_filename
                    self.add_sector(read_sector)
                self.media.format_class = fmt
                fmt.media = self.media
        self.histo = stream.histo
        self.files_done.add(rel_filename)
        if self.cache_file:
            self.cache_file.write("file " + rel_filename + "\n")
            self.cache_file.flush()
        return True

    def status(self, detailed=False):
        yield "Directory " + self.dirname
        yield from self.media.status(detailed)

    def cache_file_name(self):
        return os.path.join(self.dirname, self.basename + ".ft_cache")

    def read_cache(self):
        try:
            print("# read cache", self.cache_file_name())
            with open(self.cache_file_name(), "r") as file:
                for line in file:
                     line = line.split()
                     if line[0] == "format":
                         for cls in self.format_classes:
                             if cls.__name__ != line[1]:
                                continue
                             fmt = cls()
                             fmt.define_geometry(self.media)
                             self.media.format_class = fmt
                             fmt.media = self.media
                         continue
                     if line[0] == "file":
                         self.files_done.add(line[1])
                         continue
                     if line[0] == "sector":
                         chs = tuple(int(x) for x in line[2].split(","))
                         octets = bytes.fromhex(line[3])
                         if len(line) > 4:
                             extra = line[4]
                         else:
                             extra = ""
                         self.media.format_class.cached_sector(
                             disk.Sector(chs, octets, source=line[1], extra=extra)
                         )
                         continue
                     print("Invalid cache line")
                     print("   ", line)
                     exit(2)
        except FileNotFoundError:
            pass

class Main():
    ''' Common main() implementation '''

    def __init__(self, *format_classes):
        self.format_classes = format_classes
        self.files_done = set()
        self.myself = sys.argv[0]
        self.verbose = 0
        self.defects = {}

        if os.isatty(sys.stdout.fileno()):
            self.HOME = "\x1b[H"
            self.EOL = "\x1b[K"
            self.EOS = "\x1b[J"
        else:
            self.HOME = ""
            self.EOL = ""
            self.EOS = ""

        if len(sys.argv) >= 3 and sys.argv[1] == '-d':
            self.dir_mode()
        elif len(sys.argv) in (2, 3) and sys.argv[1] == '-m':
            self.monitor_mode()
        else:
            self.usage()

    def usage(self, err=None):
        if err:
            print(err)
        print("Usage:")
        print("  ", self.myself, "-m [source_directory]")
        print("  ", self.myself, "-d media_directory [stream_files]…")
        sys.exit(2)

    def finish_media(self, media, dstname, medianame="XXX"):
        media.media.write_bin_file(dstname + ".bin")
        #media.media.write_imagedisk_file(dstname + ".imd")
        with open(dstname + ".status", "w", encoding="utf8") as file:
            for line in media.status():
                file.write(line + "\n")
            file.write("Detailed defects:\n")
            for defect in media.media.defects(True):
                file.write("  " + defect + "\n")
        #with open(dstname + ".meta", "w", encoding="utf8") as file:
        #    for line in media.ddhf_meta(medianame):
        #        file.write(line + "\n")

    def dir_mode(self):
        print("DIR MODE", sys.argv)
        assert len(sys.argv) >= 3
        sys.argv.pop(0)
        sys.argv.pop(0)
        self.dirname = sys.argv.pop(0)
            
        mdir = MediaDir(self.dirname, self.format_classes)
        if len(sys.argv) == 0:
            sys.argv = list(
                sorted(
                    glob.glob(os.path.join(self.dirname, "*", "*.raw"))
                )
            )

        if sys.argv and sys.argv[0] == '-r':
            sys.argv.pop(0)
            for disk_sector in mdir.media.iter_sectors():
                i, j = disk_sector.status()
                if not i:
                    mdir.media.format_class.repair.add(disk_sector.chs)
            #print("Trying to repair:", mdir.media.format_class.repair)
            print("Trying to repair")
            repair=True
        else:
            repair=False

        if len(sys.argv) == 0:
            sys.argv = list(sorted(glob.glob(self.dirname + "/*/*.raw")))
        sys.stdout.write(self.HOME + self.EOS)
        for filename in sys.argv:
            if mdir.process_file(filename, force=repair):
                sys.stdout.write(self.HOME)
                for line in mdir.status():
                    print(line + self.EOL)
                for line in histo(mdir.histo):
                    print(line + self.EOL)
                sys.stdout.write(self.EOS+"\n")
                sys.stdout.flush()
        for line in mdir.status(detailed=True):
            print(line + self.EOL)
        sys.stdout.write(self.EOS+"\n")
        sys.stdout.flush()
        self.finish_media(mdir, mdir.dirname + "/" + mdir.basename)

    def monitor_mode(self):
        if len(sys.argv) == 2:
            self.path = "."
        else:
            self.path = sys.argv[2]

        summary = False
        m = 0
        sys.stdout.write(self.HOME + self.EOS)
        while True:
            n = self.workload()
            sys.stdout.flush()
            if n != 0:
                m = 0
                continue
            m += 1
            if m != 10:
                time.sleep(1)
                continue
            print()
            print("Incomplete media (if any):")
            for dirname, defects in sorted(self.defects.items()):
                if defects:
                    print(" ", dirname, defects)
            m += 1
            sys.stdout.flush()

    def workload(self):
        n = 0
        cur_media = None
        mdir = None
        for fn in self.todo():
            relname = os.path.relpath(fn, self.path)
            medianame = os.path.split(os.path.split(relname)[0])[0]
            if medianame != cur_media: 
                if mdir:
                    self.defects[cur_media] = mdir.media.list_defects()
                    sys.stdout.write(self.HOME)
                    for i in mdir.status():
                        print(i + self.EOL)
                    self.finish_media(mdir, mdir.dirname + "/" + mdir.basename)
                    sys.stdout.write(self.EOS)
                mdir = MediaDir(medianame, formats=self.format_classes)
                cur_media = medianame
            show_status = mdir.process_file(fn)
            self.files_done.add(fn)
            n += 1
            if show_status:
                sys.stdout.write(self.HOME)
                for i in mdir.status():
                    print(i + self.EOL)
                for line in histo(mdir.histo):
                    print(line + self.EOL)
                sys.stdout.write(self.EOS)
            print("FN", fn, show_status)
            sys.stdout.flush()
        if mdir:
            self.defects[cur_media] = mdir.media.list_defects()
            self.finish_media(mdir, mdir.dirname + "/" + mdir.basename)
        return n

    def todo(self):
        for fn in sorted(glob.glob(os.path.join(self.path, "*", "*", "*.raw"))):
            if fn in self.files_done:
                continue
            st = os.stat(fn)
            if st.st_mtime + COOLDOWN > time.time():
                continue
            yield fn

def main():
    Main(
        *ibm.ALL,
        dg_nova.DataGeneralNova,
        zilog_mcz.ZilogMCZ,
        dec_rx02.DecRx02,
        wang_wcs.WangWcs,
        *hp98xx.ALL,
    )

if __name__ == "__main__":
    main()
