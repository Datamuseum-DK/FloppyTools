#!/usr/bin/env python3

'''
   Main program for floppy tools
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

import sys
import os
import glob
import time

from .formats import index

# Dont touch files if mtime is newer than this
COOLDOWN = 2

class Main():
    ''' Common main() implementation '''

    def __init__(self):
        self.files_done = set()
        self.verbose = 0
        self.defects = {}
        self.mdir = None


        run_mode = None
        self.ignore_cache = False
        self.just_try = False
        self.end_when_complete = False
        format_names = []
        ttymode = os.isatty(sys.stdout.fileno())
        while len(sys.argv) > 1:
            sys.argv.pop(0)
            if sys.argv[0] == '-a':
                self.ignore_cache = True
            elif sys.argv[0] == '-d':
                run_mode = self.dir_mode
            elif sys.argv[0] == '-e':
                self.end_when_complete = True
            elif sys.argv[0] in ('-h', '-?', '--help'):
                self.usage()
                sys.exit(0)
            elif sys.argv[0][:2] == '-f' and len(sys.argv[0]) > 2:
                format_names += sys.argv[0][2:].split(",")
            elif sys.argv[0] == '-f':
                format_names += sys.argv.pop(1).split(",")
            elif sys.argv[0] == '-m':
                run_mode = self.monitor_mode
            elif sys.argv[0] == '-n':
                self.just_try = True
            elif sys.argv[0] == '-t':
                ttymode = True
            elif sys.argv[0][0] == '-':
                print("Unknown flag", sys.argv[0])
                self.usage()
                sys.exit(2)
            else:
                break

        if ttymode:
            self.esc_home = "\x1b[H"
            self.esc_eol = "\x1b[K"
            self.esc_eos = "\x1b[J"
        else:
            self.esc_home = ""
            self.esc_eol = ""
            self.esc_eos = ""
        if run_mode is None:
            print("Specify run mode with -d or -m ")
            self.usage()
            sys.exit(2)

        if not format_names:
            format_names.append("all")
        self.format_classes = {}
        for fnm in format_names:
            i = list(index.find_formats(fnm))
            if not i:
                print("Format name", fnm, "unrecognized")
                self.usage()
                sys.exit(2)
            for fnm, fcls in i:
                self.format_classes[fnm] = fcls
        run_mode()

    def usage(self, err=None):
        ''' ... '''

        if err:
            print(err)
        print("")
        print("Usage:")
        print("------")
        opt = "[options]"
        print("  python3 -m", __package__, opt, "-m [project_directory]")
        print("  python3 -m", __package__, opt, "-d media_directory [stream_files]…")
        print("")
        print("Options:")
        print("--------")
        print("")
        print("  -a                       - ignore cache (= read everything)")
        print("  -e                       - end when complete")
        print("  -f format[,format]*      - formats to try")
        print("  -n                       - dont write cache (= just try)")
        print("  -t                       - force tty mode (= use escape sequences)")
        print("")
        print("Formats:")
        print("--------")
        for nm, doc in index.documentation.items():
            print("\n  " + nm + "\n\t" + "\n\t".join(doc[0]))
        print("")
        print("Aliases:")
        print("--------")
        for nm, which in index.aliases.items():
            print("\n  " + nm + "\n\t" + ", ".join(sorted(which)))
        print("")

    def sync_media(self):
        ''' Close a media directory '''
        if not self.mdir:
            return
        self.defects[self.mdir.medianame] = self.mdir.summary()
        with open(self.mdir.file_name(".status"), "w", encoding="utf8") as file:
            file.write("Dirname " + self.mdir.medianame + "\n")
            for i in self.mdir.picture():
                file.write(i + '\n')
            for i in sorted(self.mdir.messages):
                file.write(i + '\n')
            file.write(self.mdir.summary() + '\n')
            for i, j in self.mdir.missing():
                file.write("\t" + i + " " + j + "\n")
        self.mdir = None

    def mystatus(self, filename):
        ''' Single line status '''
        l0 = [filename] + list(self.mdir.messages) + [self.mdir.summary()]
        sys.stdout.write("  ".join(l0) + self.esc_eol + '\n')

    def mypicture(self, filename):
        ''' Full Picture '''
        sys.stdout.write(self.esc_home)
        self.mystatus(filename)
        for line in self.mdir.picture():
            print(line + self.esc_eol)
        sys.stdout.write(self.esc_eos)

    def process_file(self, filename):
        ''' Process one file '''
        retval = self.mdir.process_file(filename)
        if retval:
            self.mypicture(filename)
        else:
            self.mystatus(filename)
        sys.stdout.flush()
        return retval

    def process_dir(self, dirname, files):
        ''' Process some files in one directory '''
        if self.mdir:
            self.sync_media()
            self.mdir = None
        for fn in files:
            if not self.mdir:
                for cls in self.format_classes.values():
                    self.mdir = cls(
                        dirname,
                        load_cache = not self.ignore_cache,
                        save_cache = not self.just_try,
                    )

                    self.process_file(fn)
                    if self.mdir.any_good():
                        break
                    self.mdir = None
            else:
                self.process_file(fn)
            self.files_done.add(fn)

    def dir_mode(self):
        ''' Process a specific directory '''

        if not sys.argv:
            print("Specify directory for -d mode")
            self.usage()
            sys.exit(2)
        dirname = sys.argv.pop(0)

        if len(sys.argv) == 0:
            sys.argv = list(
                sorted(
                    glob.glob(os.path.join(dirname, "*", "*.raw"))
                )
            )

        if len(sys.argv) == 0:
            print("Nothing to do ?")
            sys.exit(2)

        sys.stdout.write(self.esc_home + self.esc_eos)
        self.process_dir(dirname, sys.argv)
        self.sync_media()

    def report_incomplate(self):
        ''' Report incomplete media '''
        l = []
        for dirname, defects in sorted(self.defects.items()):
            if 'COMPLETE' not in defects:
                l.append([dirname] + defects.split())
        if not l:
            return
        print()
        w = [0] * max(len(x) for x in l)
        for x in l:
            for n, y in enumerate(x):
                w[n] = max(w[n], len(y))
        for row in l:
            x = []
            for width, datum in zip(w, row):
                x.append(datum.ljust(width))
            print("  ", " ".join(x))

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
            if m == 3:
                self.sync_media()
                self.report_incomplate()
                print()
                print("Waiting for stream files…")
                sys.stdout.flush()
            if m < 10:
                time.sleep(1)
            else:
                time.sleep(5)

    def monitor_process_pending_files(self):
        ''' Process pending files '''

        for dirname in sorted(glob.glob("*")):
            if os.path.isdir(dirname):
                fns = list(sorted(self.monitor_files_todo(dirname)))
                if fns:
                    if dirname not in self.defects:
                        self.defects[dirname] = " - NOTHING"
                    self.process_dir(dirname, fns)

    def monitor_files_todo(self, dirname):
        ''' Yield a list of new ${dirname}/*/*.raw files which have cooled down '''

        for fn in sorted(glob.glob(os.path.join(dirname, "*/*.raw"))):
            if fn[-4:] != ".raw":
                continue
            if fn in self.files_done:
                continue
            st = os.stat(fn)
            if st.st_mtime + COOLDOWN < time.time():
                yield fn
