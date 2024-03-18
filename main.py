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
            fmt = cls()
            i = list(fmt.process(kryostream.KryoStream(streamfilename)))
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

    def finish_media(self, media, dstname, medianame="XXX"):
        media.write_bin_file(dstname)
        with open(dstname + ".status", "w", encoding="utf8") as file:
            for line in media.status():
                file.write(line + "\n")
        with open(dstname + ".meta", "w", encoding="utf8") as file:
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
                    self.finish_media(media, dstname)
                    media = None
                dstname = sys.argv.pop(0)
                continue
            if sys.argv[0][:2] == '-v':
                i = sys.argv.pop(0)
                for j in i[1:]:
                    if j == 'v':
                        self.verbose += 1
                        continue
                    self.usage('unknown flag "%s"' % j)
                if self.verbose > 1:
                    sys.stdout.write("\x1b[2J")
                continue
            filename = sys.argv.pop(0)
            print("#", filename)
            sys.stdout.flush()
            if media is None:
                media = self.infer_media(filename)
            else:
                proc = media.format_class()
                for sector in proc.process(kryostream.KryoStream(filename)):
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
                self.finish_media(media, dstname)

    def monitor_mode(self):
        if len(sys.argv) == 2:
            self.path = "."
        else:
            self.path = sys.argv[2]

        print("\x1b[H\x1b[2J")
        summary = False
        while True:
            n = self.workload()
            if n != 0:
                summary = True
                continue
            sys.stdout.write("Idle " + str(time.ctime()) + "\x1b[K\r")
            sys.stdout.flush()
            if not summary:
                time.sleep(1)
                continue
            print()
            print("Incomplete media (if any):")
            for name, media in sorted(self.media.items()):
                i = list(media.defects())
                if i:
                    print(" ", name, ", ".join(i))
                summary = False

    def workload(self):
        n = 0
        for fn in self.todo():
            print("Processing", fn + "\x1b[J")
            sys.stdout.flush()
            name_parts = fn.split('/')
            medianame = name_parts[-3]
            media = self.media.get(medianame)
            if media is None:
                media = disk.Disk()
                self.media[medianame] = media

            if not media.format_class:
                self.infer_media(fn, media=media)
            else:
                proc = media.format_class()
                for sector in proc.process(kryostream.KryoStream(fn)):
                    media.add_sector(sector)

            sys.stdout.write("\x1b[H")
            print(medianame + " after " + fn + "\x1b[K")
            for line in media.status():
                print(line + "\x1b[K")
            print("\x1b[J")
            sys.stdout.flush()

            dstname = '/'.join(name_parts[:-2]) + "/_" + name_parts[-3] + ".bin"
            self.finish_media(media, dstname, medianame=medianame)
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
        *ibm.ALL,
        dec_rx02.DecRx02,
        wang_wcs.WangWcs,
    )

if __name__ == "__main__":

    main()
