
def corr(a, b):
    n = 0
    for i, j in zip(a, b):
        if i == j:
            n += 1
    return n

class Segment():
    def __init__(self, flux, common=False):
        assert len(flux) > 0
        self.flux = flux
        self.common = common

    def __repr__(self):
        if self.common:
            return "[%d]" % len(self.flux)
        return self.flux

    def __len__(self):
        return len(self.flux)

    def __getitem__(self, idx):
        return self.flux.__getitem__(idx)

    def delete(self, idx):
        assert not self.common
        i = len(self)
        if idx == 0:
            self.flux = self.flux[1:]
        elif idx == len(self.flux) - 1:
            self.flux = self.flux[:-1]
        else:
            self.flux = self.flux[:idx] + self.flux[idx+1:]
        assert len(self) == i - 1

    def insert(self, idx, what):
        i = len(self)
        if idx == 0:
            self.flux = what + self.flux
        elif idx == len(self.flux):
            self.flux = self.flux + what
        else:
            self.flux = self.flux[:idx] + what + self.flux[idx:]
        assert len(self) == i + 1

    def best(self, other, distance):
        hbstart = 0
        hblen = 0
        hlen = 0
        hstart = None
        if distance == 0:
            a = self.flux
            b = other.flux
        elif distance > 0:
            a = self.flux[distance:]
            b = other.flux
        else:
            a = self.flux
            b = other.flux[-distance:]
        for n, i in enumerate(zip(a, b)):
            if i[0] == i[1]:
                if hstart is None:
                    hstart = n
                    hlen = 1
                else:
                    hlen += 1
            else:
                if hstart is not None:
                    if hlen > hblen:
                        hblen = hlen
                        hbstart = hstart
                hstart = None
        if hstart is not None:
            if hlen > hblen:
                hblen = hlen
                hbstart = hstart
        return a[hbstart:hbstart+hblen]

    def fuzz(self, other):
        l = ""
        for i in range(-32,32):
            j = self.best(other, i)
            #print("%4d" % i, len(j), len(self.flux), len(other.flux))
            if len(j) > len(l):
                l = j
        return l

    def fit(self, flux):
        if len(flux) < 16:
            return ''
        i = self.flux.find(flux)
        if i > 0:
            return flux

        length = len(flux) // 8
        best = 0
        offset = 0
        for i in range(8):
            fl2 = flux[length * i: length * (i + 1)]
            mine = self.flux.find(fl2)
            if mine == -1:
                continue
            their = flux.find(fl2)
            sofar = len(fl2)
            while mine > 0 and their > 0 and self.flux[mine-1] == flux[their-1]:
                mine -= 1
                their -= 1
                sofar += 1
            ii = mine+sofar
            jj = their+sofar
            while ii < len(self.flux) and jj < len(flux) and self.flux[ii] == flux[jj]:
                ii += 1
                jj += 1
                sofar += 1
            if sofar > best:
                best = sofar
                offset = mine
        if best < 16:
            return ''
        return self.flux[offset:offset + best]

class Reading():
    def __init__(self, flux, weight=1):
        self.weight = weight
        self.original_segment = Segment(flux)
        self.segments = [ self.original_segment ]

    def __lt__(self, other):
        if self.weight != other.weight:
            return self.weight > other.weight
        return self.segments[0].flux < other.segments[0].flux

    def __getitem__(self, idx):
        return self.segments.__getitem__(idx)

    def subst(self, common):
        assert len(common) > 0
        for n, seg in enumerate(self.segments):
            assert len(seg) > 0
            if seg.common:
                 continue
            i = seg.flux.find(common.flux)
            if i < 0:
                 continue
            if i == 0 and len(seg) == len(common):
                 self.segments[n] = common
                 return
            if i == 0:
                j = Segment(seg.flux[len(common):])
                self.segments[n] = j
                self.segments.insert(n, common)
                return
            if i + len(common) == len(seg):
                j = Segment(seg.flux[:i])
                self.segments[n] = common
                self.segments.insert(n, j)
                return
            j = Segment(seg.flux[:i])
            k = Segment(seg.flux[i+len(common):])
            self.segments[n] = k
            self.segments.insert(n, common)
            self.segments.insert(n, j)
            return
        print("SUBST failed")
        exit(2)

    def iter_private(self):
        for seg in self.segments:
            if not seg.common:
                yield seg

class Comparator():
    def __init__(self):
        self.readings = {}

    def add_reading(self, flux):
        rdg = self.readings.get(flux, None)
        if rdg:
            rdg.weight += 1
        else:
            self.readings[flux] = Reading(flux)

    def analyze(self):
        if isinstance(self.readings, dict):
            self.readings = list(sorted(self.readings.values()))
        for rdg in self.readings:
            rdg.segments = [ rdg.original_segment ]
        while self.one_pass():
            continue
        for n, rdg in enumerate(self.readings):
            print("R %2d" % n, "%4d" % rdg.weight, " ".join(str(x) for x in rdg.segments))
    
    def find_candidate(self):
        l = ""
        for seg0 in self.readings[0].iter_private():
            for seg1 in self.readings[1].iter_private():
                i = seg0.fuzz(seg1)
                if len(i) > len(l):
                    l = i
        return l

    def find_hit(self, flux):
        if len(flux) < 16:
            return None
        for rdg in self.readings:
            hit = ""
            for seg in rdg.iter_private():
                i = seg.fit(flux)
                # print("F", seg, len(i), len(hit))
                if len(i) > len(hit):
                    hit = i
            if len(hit) < 16:
                return None
            if len(hit) < len(flux):
                flux = hit
        return flux

    def one_pass(self):
        l = self.find_candidate() 
        if l is None:
            return False
        #print("CAND", len(l), l)
        hit = self.find_hit(l)
        if hit is None:
            return False
        #print("HIT", len(hit), hit)
        if len(hit) < 16:
            return False
        probe = Segment(hit)
        probe.common=True
        #print("PP", probe, probe.flux)
        for rdg in self.readings:
            rdg.subst(probe)
        return True
