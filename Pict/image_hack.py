
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
SLOW_OFF = 25

class Histogram2():
    def __init__(self):
        self.data = []
        for i in range(SLOW):
            self.data.append([0] * SLOW)

    def add(self, prev, item):
        prev -= SLOW_OFF 
        item -= SLOW_OFF 
        if 0 <= prev < SLOW and 0 <= item < SLOW:
            self.data[prev][item] += 1

    def paint(self, pic, peaks):
        peak = .1
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
        item -= SLOW_OFF 
        if 0 <= item < SLOW:
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
            if tot > 0 and vol / tot > .01: 
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
        peak = max(.1, max(self.data))

        for i, j in enumerate(self.data):
            x = 2 * (i - SLOW // 2)
            y0 = SLOW 
            yx = y0 + +10 * int(math.log(1 + 1000 * j / peak))
            if peaks[0] <= i <= peaks[1]:
                rgb = (64, 255, 64)
            elif peaks[2] <= i <= peaks[3]:
                rgb = (64, 64, 255)
            elif peaks[4] <= i <= peaks[5]:
                rgb = (255, 0, 0)
            else:
                rgb = (192, 192, 192)
            #for y in range(yx, y0 + 1): 
            for y in range(y0 - 1, yx): 
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
                k -= SLOW_OFF
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

        if len(self.ks.index) < 2:
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


    def __init__(self, dirname, side=0):

        self.dirname = dirname

        self.fns = list(sorted(glob.glob(dirname + "/*??.%d.raw" % side)))

        kfs = list(KryoFile(fn) for fn in self.fns)

        p = Projection(WIDTH)

        h = Histogram()
        h2 = Histogram2()

        for kf in kfs[:200]:
            print("kf", kf)
            kf.find_first_rotation(h, h2)

        peaks = h.peaks()
        h2.paint(p, peaks)
        h.paint(p, peaks)
        h.dump("/tmp/_h")

        for kf in kfs[:200]:
            kf.process(p)

        p.dump("/tmp/pix.ppm", peaks)
        exit(0)

if __name__ == "__main__":

   import sys

   d = DiskImg(sys.argv[1], len(sys.argv) - 2)
