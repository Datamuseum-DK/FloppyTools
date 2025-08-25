
import math
import glob

from floppytools.base import kryostream

SCALE = 6
RAD76 = 51.537
TPI = 25.4 / 48
RADI = RAD76 - 5 * TPI
MARGIN = 40

WIDTH = 2 * int(SCALE * (RAD76 + TPI * 76) + MARGIN)

SLOW = 200

class Histogram2():
    def __init__(self):
        self.data = []
        for i in range(SLOW):
            self.data.append([0] * SLOW)

    def add(self, prev, item):
        if 5 < prev < SLOW and 5 < item < SLOW:
            self.data[prev][item] += 1

    def paint(self, pic, peaks):
        peak = 0
        for i in self.data:
            j = max(i)
            peak = max(peak, j)
        peak = math.log(peak)
        print("H2", "peak", peak)

        y0 = SLOW
        x0 = -SLOW
        for x, i in enumerate(self.data):
            for y, j in enumerate(i):
                if 0 and (x-75)**2 + (y-75)**2 > 8000:
                    continue
                    color = (0x00, 0x55, 0x55)
                elif j == 0:
                    color = (0x55, 0x00, 0x55)
                else:
                    j = int(255 * math.log(j) / peak)
                    color = (j, j, j)
                pic.color(    x + x + x0,     y0 - (y + y), color)
                pic.color(1 + x + x + x0,     y0 - (y + y), color)
                pic.color(    x + x + x0, 1 + y0 - (y + y), color)
                pic.color(1 + x + x + x0, 1 + y0 - (y + y), color)

class Histogram():
    def __init__(self):
        self.data = [0] * SLOW

    def add(self, item):
        if 5 <= item < SLOW:
            self.data[item] += 1

    def peaks(self):
        pks = []
        left = [0] * SLOW
        smear = 5
        minimis = 0
        minimis = 100
        tot = sum(self.data)
        for n, i in enumerate(self.data):
            left[n // smear] += i
        for i in range(4):
            pk = max(left)
            xc = left.index(pk)

            xlo = xc
            while xlo > 0 and left[xlo - 1] < left[xlo] and left[xlo-1] > minimis:
                xlo -= 1

            xhi = xc
            while xhi < len(left) - 1 and left[xhi + 1] < left[xhi] and left[xhi+1] > minimis:
                xhi += 1

            u = xc
            vol = 0
            for x in range(xlo, xhi+1):
                vol += left[x]
                left[x] = 0
            if vol / tot > .01: 
                pks.append((xlo, xc, xhi, vol))
            print("pk", xlo * smear, xc * smear, xhi * smear, vol)

        ll = []
        for xlo,xc,xhi,vol in pks:
            print("PK", pk, xlo * smear, xc * smear, xhi * smear, vol, vol/tot)
            ll.append(xlo * smear)
            ll.append(xhi * smear + smear - 1)
        print("LL", ll)
        while len(ll) < 6:
           ll.append(99999)
        return ll

    def paint(self, pic, peaks):
        peak = max(self.data)

        for i, j in enumerate(self.data):
            x = 2 * (i - SLOW // 2)
            y0 = SLOW 
            yx = y0 + -10 * int(math.log(1 + 1000 * j / peak))
            if peaks[0] <= i <= peaks[1]:
                rgb = (64, 255, 64)
            elif peaks[2] <= i <= peaks[3]:
                rgb = (64, 64, 255)
            elif peaks[4] <= i <= peaks[5]:
                rgb = (255, 0, 0)
            else:
                rgb = (192, 192, 192)
            for y in range(yx, y0 + 1): 
                pic.color(x, y, rgb)
                pic.color(x+1, y, rgb)

    def dump(self, fn):
        peak = max(self.data)
        threshold = peak ** .5
        with open(fn, "w") as file:
            for i, j in enumerate(self.data):
                if j == 0:
                    j = 1
                file.write("%d %d\n" % (i, j))

class Pixel():
    def __init__(self):
        self.data = []

    def rgb(self, peaks):
        r = 0
        g = 0
        b = 0
        if True:
            for k in self.data:
                if peaks[0] <= k <= peaks[1]:
                    g += 1
                elif peaks[2] <= k <= peaks[3]:
                    b += 1
                elif peaks[4] <= k <= peaks[5]:
                    r += 1
        r /= len(self.data)
        g /= len(self.data)
        b /= len(self.data)
        r *= 255
        g *= 255
        b *= 255
        return int(r), int(g), int(b)

class Projection():

    def __init__(self, width):
        self.pic = {}
        self.rgb = {}
        self.width = width

    def add(self, x, y, z):
        p = self.pic.get((x,y))
        if p is None:
            p = Pixel()
            self.pic[(x,y)] = p
        p.data.append(z)

    def color(self, x, y, rgb):
        self.rgb[(x, y)] = rgb

    def dump(self, fn, peaks):
        self.xmin = -self.width // 2
        self.ymin = -self.width // 2
        self.xmax = self.width // 2
        self.ymax = self.width // 2
        with open(fn, "w") as file:
             file.write("P3\n")
             file.write("%d %d 255\n" % (1 + self.xmax - self.xmin, 1 + self.ymax - self.ymin))
             for y in range(self.ymin, self.ymax + 1):
                 for x in range(self.xmin, self.xmax + 1):
                     color = self.rgb.get((x, y))
                     if color:
                         file.write("%d %d %d\n" % color)
                         continue
                     p = self.pic.get((x, y))
                     if True:
                         if not p:
                             p = self.pic.get((x-1, y))
                         if not p:
                             p = self.pic.get((x, y-1))
                         if not p:
                             p = self.pic.get((x, y+1))
                         if not p:
                             p = self.pic.get((x+1, y))
                         if not p:
                             p = self.pic.get((x-1, y-1))
                         if not p:
                             p = self.pic.get((x-1, y+1))
                         if not p:
                             p = self.pic.get((x+1, y-1))
                         if not p:
                             p = self.pic.get((x+1, y+1))
                         if not p:
                             p = self.pic.get((x+2, y+0))
                         if not p:
                             p = self.pic.get((x+0, y+2))
                         if not p:
                             p = self.pic.get((x-2, y+0))
                         if not p:
                             p = self.pic.get((x+0, y-2))
                     if p:
                         file.write("%d %d %d\n" % p.rgb(peaks))
                     else:
                         file.write("%d %d %d\n" % (.5,.5,.5))
        
class KryoFile():

    def __init__(self, fname):
        self.fname = fname
        self.ks = kryostream.KryoStream(fname)
        self.chs = self.ks.chs

    def __repr__(self):
        return "<KF " + self.fname + " " + str(self.chs) + ">"

    def find_first_rotation(self, histo, histo2):
        self.ks.deframe()

        if len(self.ks.index) < 3:
            print("Too few index pulses",len(self.ks.index))
            self.rev0 = -1
            self.rev1 = -1
            return

        self.idx = {}
        for n, i in enumerate(self.ks.index):
            self.idx[i[3]] = i

        dur = 0
        p = 0
        for n, dt in enumerate(self.ks.iter_dt()):
            histo.add(dt)
            histo2.add(p, dt)
            p = dt
            if n in self.idx:
                self.idx[n].append(dur)
            dur += dt

        if len(self.ks.index) < 12:
            idx0 = 0
            idx1 = 1
            iholes = []
        else:
            p = 0
            l = []
            for i, j in self.idx.items():
                d = j[-1] - p
                l.append(d)
                p = j[-1]
            l.sort()
            m = (l[3] + l[-8]) / 2

            p = 0
            pd = 0
            iholes = []
            n = 0
            for i, j in enumerate(self.idx.values()):
                d = j[-1] - p
                if d < m and pd > m:
                    iholes.append(i)
                    n = 0
                pd = d
                p = j[-1]
                n += 1

            idx0 = iholes[0]
            idx1 = iholes[1]

        self.rev0 = self.ks.index[idx0][3]
        self.rev1 = self.ks.index[idx1][3]
        self.rdur = self.ks.index[idx1][-1] - self.ks.index[idx0][-1]
        print(
            "R0",
            idx0,
            self.ks.index[idx0],
        )
        print(
            "R1",
            idx1,
            self.ks.index[idx1],
        )
        print(
            "  ",
            self.rdur,
            iholes,
        )

    def process(self, pict):
        if self.rev0 < 0:
            return

        omega = 0
        dur = 0
        rho = 2 * 3.141592 / self.rdur

        rad = SCALE * (RAD76 + TPI * (76 - self.ks.chs[0]))
        radi = SCALE * RADI - self.ks.chs[0] * .2

        prev = 0
        for n, dt in enumerate(self.ks.iter_dt()):
            if self.rev0 > n:
                continue
            if n > self.rev1:
                break
            omega = dur * rho
            dur += dt
            if n in self.idx:
                x = int(radi*math.sin(omega))
                y = int(-radi*math.cos(omega))
                for dx in (-1, 0, +1):
                    for dy in (-1, 0, +1):
                        pict.color(x+dx, y+dy, (255,255,255))
                
            x = int(rad*math.sin(omega))
            y = int(-rad*math.cos(omega))
            pict.add(x,y,dt)

class DiskImg():


    def __init__(self, dirname):

        self.dirname = dirname

        self.fns = list(sorted(glob.glob(dirname + "/*??.0.raw")))

        if 0 and len(self.fns) < 30:
            print("Too few tracks", len(self.fns))
            return

        kfs = list(KryoFile(fn) for fn in self.fns)

        p = Projection(WIDTH)

        h = Histogram()
        h2 = Histogram2()

        for kf in kfs[:200]:
            print(kf)
            if kf.chs[1] != 0:
                continue
            kf.find_first_rotation(h, h2)

        peaks = h.peaks()
        h2.paint(p, peaks)
        h.paint(p, peaks)
        h.dump("/tmp/_h")

        for kf in kfs[:200]:
            if kf.chs[1] != 0:
                continue
            kf.process(p)

        p.dump("/tmp/pix.ppm", peaks)
        exit(0)

if __name__ == "__main__":

   import sys

   d = DiskImg(sys.argv[1])
   exit(0)

   if False:
       import glob

       for dn in glob.glob("/critter/DDHF/2024/NThun/NThun_0007/*"):
           print("DDD", dn)
           d = DiskImg(dn)
           break

       exit(0)

   #import sys
   #d = DiskImg(sys.argv[1])

   d = DiskImg("/critter/202501_floppy/forth/000")
   #d = DiskImg("/critter/DDHF/2025/20250102/Q1/Bad/50001592/000")
   #d = DiskImg("/critter/DDHF/2025/20250102/Q1/Bad/50001608/000")
   #d = DiskImg("/critter/DDHF/2025/20250102/IntelFD/50001661/000")
   #d = DiskImg("/critter/DDHF/2024/NThun/NThun_0007/11/")
   #d = DiskImg("/critter/FloppyTools_Test/ibm_s34_4/01/")
 
   #d = DiskImg("/critter/FloppyTools_Test/hp9885_zeiss/00/")

   # High density
   #d = DiskImg("/critter/FloppyTools_Test/intel_isis_crfd0031/00/")

   # HS
   #d = DiskImg("/critter/FloppyTools_Test/wang_wcs_cr80fd_0517/00/")
   #d = DiskImg("/critter/FloppyTools_Test/zilog_mcz_nthun_0034/000")

   # a lot of rotational jitter, 26 sectors
   #d = DiskImg("/critter/FloppyTools_Test/ibm_cb110/00/")

   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/S34_8/01")

   # bad track ?
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/S34_7/01")

   # Nearly ideal plain floppy, 8 sectors
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/S34_6/01")

   # Good 26x128 image
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/foo1/00")

   # Good 26x128 image, ditto with waves
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/foo2/00")

   # Good 26x128 image, has index mark
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/foo3/00")

   # also good, unused inner tracks
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/foo4/00")

   # skrevet/formatteret på to forskellige drev
   #d = DiskImg("/critter/DDHF/2024/20240404_s34fd/foo5/00")

   # ikke ret meget tilbage
   #d = DiskImg("/critter/DDHF/2025/20250102/Q1/Eliminated/50001614/003")

   # normal 26s
   #d = DiskImg("/critter/DDHF/2024/crfd_0543/crfd_0543/00")

   #d = DiskImg("/critter/DDHF/2024/20240905/crfd_0531/00")

   # needs work
   #d = DiskImg("/critter/DDHF/2019/20190919_CBM900_STREAM/Vol_1_high_resolution/")
   #d = DiskImg("/critter/DDHF/BitStored/CBM900_Floppy_Vol2/data/Vol_2_low_resolution/", 50, 100)

   # grafisk flot
   #d = DiskImg("/critter/DDHF/2023/20230716_PHK/crfd0034")




   #d = DiskImg("/critter/FloppyTools_Test/dg_nova_nthun_0006/00")

   #d = DiskImg("/critter/FloppyTools_Test/dec_rx02_cb112/00")
   #d = DiskImg("/critter/DDHF/2024/20240208_CB/cb106/00")
   #d = DiskImg("/critter/DDHF/2024/S34fd/S34_3/s34_iii_1", low=60,high=80)

   # 4-record sectors
   #d = DiskImg("/critter/DDHF/2024/S34fd/S34_9/s34_ix_1", low=60,high=80)

   #d = DiskImg("/critter/DDHF/2024/S34fd/S34_4/02", low=60,high=80)

   #d = DiskImg("/critter/DDHF/2025/20250220_DisplayWriter/KP/001")
   #d = DiskImg("/critter/DDHF/2025/20250213_displaywriter_fd/kresten_petersen/000")
   #d = DiskImg("/critter/DDHF/2024/S34fd/NA/cr80fd_0527/00")
   #d = DiskImg("/critter/DDHF/2024/20240815/SuperMaxFD/cr80fd_0545/00", 60, 80)
   #d = DiskImg("/critter/DDHF/2023/20231026_SG002/SG002/sg002g")





     
