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

COOLDOWN = 2

class Main():
    ''' Common main() implementation '''

    def __init__(self, *strm_class):
        self.strm_class = strm_class
        self.files_done = set()
        self.media = {}
        self.myself = sys.argv[0]
        self.verbose = 0

        if len(sys.argv) in (2, 3) and sys.argv[1] == '-m':
            self.monitor_mode()
        elif len(sys.argv) > 1:
            self.file_list_mode()
        else:
            self.usage()

    def usage(self, err=None):
        if err:
            print(err)
        print("Usage:")
        print("  ", self.myself, "-m [source_directory]")
        print("  ", self.myself, "{-o dst_file|-v|stream_file}…")
        sys.exit(2)

    def infer_media(self, streamfilename, media=None):
        ''' Infer the media format by asking all classes '''
        for cls in self.strm_class:
            fmt = cls(kryostream.KryoStream(streamfilename), streamfilename)
            i = list(fmt.process())
            if len(i) == 0:
                continue
            if media is None:
                media = disk.Disk()
            fmt.define_geometry(media)
            for j in i:
                media.add_sector(j)
            media.format_class = cls
            return media
        return None

    def finish_media(self, media, dstname, verbose, medianame="XXX"):
        if verbose:
            for line in media.status():
                print(line)
        media.write_bin_file(dstname)
        with open(dstname + ".status", "w", "utf8") as file:
            for line in media.status():
                file.write(line + "\n")
        with open(dstname + ".meta", "w") as file:
            for line in media.ddhf_meta(medianame):
                file.write(line + "\n")

    def file_list_mode(self):
        media = None
        dstname = "/tmp/_.bin"
        sys.argv.pop(0)
        while sys.argv:
            if sys.argv[0] == '-o':
                sys.argv.pop(0)
                if not sys.argv:
                    self.usage('-o lacks argument')
                if media:
                    self.finish_media(media, dstname, self.verbose == 0)
                    media = None
                dstname = sys.argv.pop(0)
                continue
            if sys.argv[0] == '-v':
                sys.argv.pop(0)
                self.verbose += 1
                if self.verbose > 1:
                    sys.stdout.write("\x1b[2J")
                continue
            filename = sys.argv.pop(0)
            print("#", filename)
            sys.stdout.flush()
            if media is None:
                media = self.infer_media(filename)
            else:
                proc = media.format_class(
                    kryostream.KryoStream(filename),
                    filename
                )
                for sector in proc.process():
                    media.add_sector(sector)

            if media and self.verbose == 1:
                for line in media.status():
                    print(line)

            if media and self.verbose > 1:
                sys.stdout.write("\x1b[H")
                print(dstname, "\x1b[K")
                for line in media.status():
                    print(line + "\x1b[K")
                sys.stdout.write("\x1b[J")
                sys.stdout.flush()

        if media:
            self.finish_media(media, dstname, self.verbose == 0)

    def monitor_mode(self):
        if len(sys.argv) == 2:
            self.path = "."
        else:
            self.path = sys.argv[2]

        print("\x1B[H\x1b[2J")
        while True:
            n = self.workload()
            if n == 0:
                time.sleep(1)
                print(time.time())

    def workload(self):
        n = 0
        for fn in self.todo():
            print(fn + "\x1b[K")
            name_parts = fn.split('/')
            medianame = name_parts[-3]
            media = self.media.get(medianame)
            if media is None:
                media = disk.Disk()
                self.media[medianame] = media

            if not media.format_class:
                self.infer_media(fn, media=media)
            else:
                proc = media.format_class(kryostream.KryoStream(fn), fn)
                for sector in proc.process():
                    media.add_sector(sector)

            sys.stdout.write("\x1b[H")
            print(medianame + "\x1b[K")
            for line in media.status():
                print(line + "\x1b[K")
            sys.stdout.flush()

            dstname = '/'.join(name_parts[:-2]) + "/_" + name_parts[-3] + ".bin"
            self.finish_media(media, dstname, False, medianame=medianame)
            self.files_done.add(fn)
            n += 1
        return n

    def todo(self):
        for fn in sorted(glob.glob(self.path + "/*/*/*.raw")):
            if fn in self.files_done:
                continue
            st = os.stat(fn)
            if st.st_mtime + COOLDOWN > time.time():
                continue
            yield fn

def main():
    Main(
        dg_nova.DataGeneralNova,
        zilog_mcz.ZilogMCZ,
        ibm.IBM,
    )

if __name__ == "__main__":

    main()
