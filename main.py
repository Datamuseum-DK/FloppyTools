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

COOLDOWN = 2

class Main():

    def __init__(self, *strm_class):
        self.strm_class = strm_class
        self.files_done = set()
        self.media = {}

        if len(sys.argv) == 1:
            print("Usage...")
            return

        if len(sys.argv) > 1 and sys.argv[1] == '-m':
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
            return

        self.file_list()

    def file_list(self):
        media = None
        for fn in sys.argv[1:]:
            print("#", fn)
            if media is None:
                for cls in self.strm_class:
                    proc = cls(kryostream.KryoStream(fn), fn)
                    i = list(proc.process())
                    if len(i) > 0:
                        if len(self.strm_class) > 1:
                            print("ID'ed as", cls)
                        media = disk.Disk("tmp")
                        media.define_geometry(
                            cls.FIRST_CHS,
                            cls.LAST_CHS,
                        )
                        for j in i:
                            media.add_sector(j)
                        break
            else:
                proc = cls(kryostream.KryoStream(fn), fn)
                for sector in proc.process():
                    media.add_sector(sector)
        for line in media.status():
            print(line)
        media.write_bin_file("/tmp/_.bin")

    def workload(self):
        n = 0
        for fn in self.todo():
            print(fn + "\x1b[K")
            name_parts = fn.split('/')
            medianame = name_parts[-3]
            media = self.media.get(medianame)
            if media is None:
                time.sleep(3)
                media = disk.Disk(medianame)
                self.media[medianame] = media

            if not media.format:
                for cls in self.strm_class:
                    proc = cls(kryostream.KryoStream(fn), fn)
                    i = list(proc.process())
                    if len(i) > 0:
                        if len(self.strm_class) > 1:
                            print("ID'ed as", cls)
                        media.format = cls
                        media.define_geometry(
                            cls.FIRST_CHS,
                            cls.LAST_CHS,
                        )
                        for j in i:
                            media.add_sector(j)
                        break
            else:
                proc = media.format(kryostream.KryoStream(fn), fn)
                for sector in proc.process():
                    media.add_sector(sector)

            self.files_done.add(fn)

            sys.stdout.write("\x1b[H")
            for line in media.status():
                print(line + "\x1b[K")
            sys.stdout.flush()
            media.write_bin_file('/'.join(name_parts[:-2]) + "/_" + name_parts[-3] + ".bin")
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
    )

if __name__ == "__main__":

    main()
