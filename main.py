#!/usr/bin/env python3

'''
   Main program for floppy tools
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import sys
import os
import glob
import math
import time

import disk
import fluxstream
import kryostream

# Dont touch files if mtime is newer than this
COOLDOWN = 2

def histo(data):
    ''' Render a utf8-art histogram of log(data) '''

    height = 3 * 8

    data = [math.log(max(1,x)) for x in data]
    peak = max(data)
    if peak == 0:
        return

    h = [int(height * x / peak) for x in data]

    for j in range(-height, 1, 8):
        t = []
        for i in h:
            r = int(min(max(0, i+j), 8))
            t.append(' ▁▂▃▄▅▆▇█'[r])
        yield "".join(t)

class MediaDir(disk.Media):
    ''' A Directory representing a Media '''

    def __init__(self, dirname, medianame, formats=None, load_cache=True, save_cache=True):
        super().__init__()
        if formats is None:
            formats = []
        self.dirname = dirname
        os.makedirs(self.dirname, exist_ok=True)
        self.medianame = medianame
        self.files_done = set()
        self.cache_file = None
        self.format_classes = formats
        assert len(self.format_classes) > 0
        if load_cache:
            self.read_cache()
        if save_cache:
            self.cache_file = open(self.file_name(), "a", encoding="utf8")
        self.histo = []

    def file_name(self, ext="ft_cache"):
        return os.path.join(self.dirname, self.medianame + "." + ext)

    def add_sector(self, read_sector):
        ''' Add a reading of a sector '''
        super().add_sector(read_sector)
        if self.cache_file:
            self.cache_file.write(" ".join(
                    [
                        "sector",
                        read_sector.source,
                    ] + read_sector.cache_record()
                ) + "\n"
            )

    def process_file(self, streamfilename):
        ''' Infer the media format by asking all classes '''

        rel_filename = os.path.relpath(streamfilename, self.dirname)
        if rel_filename in self.files_done:
            return False
        print("Doing", streamfilename)
        try:
            stream = kryostream.KryoStream(streamfilename)
        except kryostream.NotAKryofluxStream:
            stream = fluxstream.RawStream(streamfilename)
        if self.format_class:
            try:
                for read_sector in self.format_class.process(stream):
                    read_sector.source = rel_filename
                    self.add_sector(read_sector)
                if self.cache_file:
                    self.cache_file.flush()
            except disk.NotInterested:
                return False
        else:
            for cls in self.format_classes:
                fmt = cls()
                fmt.media = self
                try:
                    read_sectors = list(fmt.process(stream))
                except disk.NotInterested:
                    continue
                if len(read_sectors) == 0:
                    continue
                fmt.media = self
                fmt.define_geometry()
                if self.cache_file:
                    self.cache_file.write(
                        "format " + fmt.__class__.__name__ + "\n"
                    )
                for read_sector in read_sectors:
                    read_sector.source = rel_filename
                    self.add_sector(read_sector)
                if self.cache_file:
                    self.cache_file.flush()
                self.format_class = fmt
        self.histo = stream.histo
        self.files_done.add(rel_filename)
        if self.cache_file:
            self.cache_file.write("file " + rel_filename + "\n")
            self.cache_file.flush()
        return True

    def status(self, detailed=False):
        yield "Directory " + self.dirname
        yield from super().status(detailed)

    def write_result(self):
        ''' Write result and status files '''

        i = os.path.join(self.dirname, self.medianame + ".bin")
        self.write_bin_file(i)
        #media.write_imagedisk_file(dstname + ".imd")
        with open(self.file_name("status"), "w", encoding="utf8") as file:
            for line in self.status():
                file.write(line + "\n")
            file.write("Detailed defects:\n")
            for defect in self.defects(True):
                file.write("  " + defect + "\n")
        #with open(dstname + ".meta", "w", encoding="utf8") as file:
        #    for line in media.ddhf_meta(medianame):
        #        file.write(line + "\n")

    def read_cache(self):
        try:
            with open(self.file_name(), "r", encoding="utf8") as file:
                print("# read cache", self.file_name())
                for line in file:
                    line = line.split()
                    if line[0] == "format":
                        for cls in self.format_classes:
                            if cls.__name__ != line[1]:
                                continue
                            fmt = cls()
                            fmt.media = self
                            fmt.define_geometry()
                            self.format_class = fmt
                        if self.format_class is None:
                            print("Unknown Format", line)
                            exit(2)
                    elif line[0] == "file":
                        self.files_done.add(line[1])
                    elif line[0] == "sector":
                        chs = tuple(int(x) for x in line[2].split(","))
                        octets = bytes.fromhex(line[3])
                        if len(line) > 4:
                            extra = line[4]
                        else:
                            extra = ""
                        self.format_class.cached_sector(
                            disk.Sector(chs, octets, source=line[1], extra=extra)
                        )
                    else:
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
        self.mdir = None

        if os.isatty(sys.stdout.fileno()):
            self.esc_home = "\x1b[H"
            self.esc_eol = "\x1b[K"
            self.esc_eos = "\x1b[J"
        else:
            self.esc_home = ""
            self.esc_eol = ""
            self.esc_eos = ""

        if len(sys.argv) >= 3 and sys.argv[1] == '-d':
            self.dir_mode()
        elif len(sys.argv) in (2, 3) and sys.argv[1] == '-m':
            self.monitor_mode()
        elif len(sys.argv) in (2, 3) and sys.argv[1] == '-r':
            self.repair_mode()
        else:
            self.usage()

    def usage(self, err=None):
        ''' ... '''

        if err:
            print(err)
        print("Usage:")
        print("  ", self.myself, "-m [source_directory]")
        print("  ", self.myself, "-d media_directory [stream_files]…")
        sys.exit(2)

    def set_media(self, dirname = None, medianame = None):
        ''' Set the active media '''

        if self.mdir and self.mdir.medianame == medianame:
            return
        if self.mdir:
            self.defects[self.mdir.medianame] = self.mdir.list_defects()
            sys.stdout.write(self.esc_home)
            for i in self.mdir.status():
                print(i + self.esc_eol)
            self.mdir.write_result()
            sys.stdout.write(self.esc_eos)
            self.mdir = None
        if dirname is not None:
            self.mdir = MediaDir(dirname, medianame, formats=self.format_classes)

    def process_file(self, filename):
        ''' Process one track file '''

        if filename in self.files_done:
            return
        if self.mdir.process_file(filename):
            sys.stdout.write(self.esc_home)
            for line in self.mdir.status():
                print(line + self.esc_eol)
            for line in histo(self.mdir.histo):
                print(line + self.esc_eol)
            print("Did", filename, self.esc_eos)
            sys.stdout.flush()
        self.files_done.add(filename)

    def dir_mode(self):
        ''' Process a specific directory '''

        print("DIR MODE", sys.argv)
        assert len(sys.argv) >= 3
        sys.argv.pop(0)
        sys.argv.pop(0)
        dirname = sys.argv.pop(0)
        medianame = os.path.split(dirname)
        if medianame[1] == "":
            print("MN", medianame)
            medianame = os.path.split(medianame[0])
        if medianame[1] == "":
            medianame = medianame[0]
        else:
            medianame = medianame[1]
        if medianame in ("", ".", "..",):
            medianame = "XXX"

        if len(sys.argv) == 0:
            sys.argv = list(
                sorted(
                    glob.glob(os.path.join(dirname, "*", "*.raw"))
                )
            )

        if len(sys.argv) == 0:
            print("Nothing to do ?")
            exit(2)

        self.set_media(dirname, medianame)

        if len(sys.argv) == 0:
            sys.argv = list(sorted(glob.glob(dirname + "/*/*.raw")))
        sys.stdout.write(self.esc_home + self.esc_eos)
        for filename in sys.argv:
            self.process_file(filename)
        for line in self.mdir.status(detailed=True):
            print(line + self.esc_eol)
        sys.stdout.write(self.esc_eos+"\n")
        sys.stdout.flush()
        self.mdir.write_result()

    def repair_mode(self):
        ''' Attempt repair of missing sectors '''

        print("REPAIR MODE", sys.argv)
        assert len(sys.argv) >= 3
        sys.argv.pop(0)
        sys.argv.pop(0)
        dirname = sys.argv.pop(0)
        medianame = os.path.split(dirname)[1]
        if medianame == ".":
            medianame = "XXX"

        if len(sys.argv) == 0:
            sys.argv = list(
                sorted(
                    glob.glob(os.path.join(dirname, "*", "*.raw"))
                )
            )

        if len(sys.argv) == 0:
            print("Nothing to do ?")
            exit(2)

        self.set_media(dirname, medianame)

        if len(sys.argv) == 0:
            sys.argv = list(sorted(glob.glob(dirname + "/*/*.raw")))
        sys.stdout.write(self.esc_home + self.esc_eos)
        for filename in sys.argv:
            self.process_file(filename)
        for line in self.mdir.status(detailed=True):
            print(line + self.esc_eol)
        sys.stdout.write(self.esc_eos+"\n")
        sys.stdout.flush()
        self.mdir.write_result()

    def monitor_mode(self):
        ''' Monitor a directory while media are being read '''

        if len(sys.argv) > 2:
            os.chdir(sys.argv[2])
        self.path = "."

        m = 0
        sys.stdout.write(self.esc_home + self.esc_eos)
        while True:
            before = len(self.files_done)
            self.monitor_process_pending_files()
            after = len(self.files_done)
            sys.stdout.flush()
            if after > before:
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
            sys.stdout.flush()

    def monitor_process_pending_files(self):
        ''' Process pending files '''

        for fn in sorted(self.monitor_files_todo()):
            i = os.path.split(fn)
            # trackfile = i[1]
            i = os.path.split(i[0])
            # reading = i[1]
            i = os.path.split(i[0])
            medianame = i[1]
            self.set_media(medianame, medianame)
            self.process_file(fn)
            sys.stdout.flush()
        self.set_media()

    def monitor_files_todo(self):
        ''' Yield a list of new */*/*.raw files which have cooled down '''

        for path, _dirs, files in os.walk(self.path):
            if path.count("/") != 2:
                continue
            for fn in files:
                if fn[-4:] != ".raw":
                    continue
                rfn = os.path.join(path, fn)
                if rfn in self.files_done:
                    continue
                st = os.stat(rfn)
                if st.st_mtime + COOLDOWN < time.time():
                    yield rfn
