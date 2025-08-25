#!/usr/bin/env python3

'''
   Summarizing of CHS lists
   ~~~~~~~~~~~~~~~~~~~~~~~~

'''

def ranges(numbers):
    ''' Reduce list of numbers to ranges '''

    diff = None
    for i,j in enumerate(sorted(numbers)):
        if i - j != diff:
            if diff is not None:
                yield first,last
            first = j
            diff = i -j
        last = j
    if diff is not None:
        yield first,last

def summarize_ints(data):
    '''
       Summarize a sequence of integers using intervals

       called with:                     returns:
           [3,]				"3"
           [3,4,]			"{3,4}"
           [3,4,5,]			"{3-5}"
           [1,2,3,4,5,6,8,9,12,13,14]   "{1-6,8,9,12-14}"
           [1,2,3,4,5,6,9,12,13,14]     "{1-6,9,12-14}"
    '''
    l = []
    for low, high in ranges(data):
        if low == high:
            l.append(str(low))
        elif low + 1 == high:
            l.append(str(low))
            l.append(str(high))
        else:
            l.append(str(low) + "-" + str(high))
    return "{" + ",".join(l) + "}"

class Cluster():
    ''' Some group of sectors '''

    def __init__(self, *args):
        self.c = set()
        self.h = set()
        self.s = set()
        self.b = set()
        self.n = 0

        for i in args:
            self.add(i)

    def __repr__(self):
        return "<Cluster " + ", ".join(self.metadata_format()) + ">"

    def metadata_format(self):
        ''' Render in DDHF bitstore metadata format '''
        for cl, ch in ranges(self.c):
            for hl, hh in ranges(self.h):
                for sl, sh in ranges(self.s):
                    for b in self.b:
                        yield "%d…%dc %d…%dh %d…%ds %db" % (cl, ch, hl, hh, sl, sh, b)

    def __iter__(self):
        for c in sorted(self.c):
            for h in sorted(self.h):
                for s in sorted(self.s):
                    for b in sorted(self.b):
                        yield (c, h, s, b)

    def pad(self):
        ''' Pad any holes '''
        for i in range(min(self.c), max(self.c) + 1):
            self.c.add(i)
        for i in range(min(self.h), max(self.h) + 1):
            self.h.add(i)
        for i in range(min(self.s), max(self.s) + 1):
            self.s.add(i)

    def same(self, other, pivot):
        ''' Check of two clusters are the same, except for the pivot element '''
        cc = self.c != other.c
        hh = self.h != other.h
        ss = self.s != other.s
        bb = self.b != other.b
        if pivot == 0 and (hh or ss or bb):
            return False
        if pivot == 1 and (cc or ss or bb):
            return False
        if pivot == 2 and (cc or hh or bb):
            return False
        if pivot == 3 and (cc or hh or ss):
            return False
        return True

    def add(self, chsb):
        ''' Add element to this cluster '''
        c,h,s,b = chsb
        self.c.add(c)
        self.h.add(h)
        self.s.add(s)
        self.b.add(b)
        self.n += 1

    def merge(self, other):
        ''' Merge two clusters '''
        self.c |= other.c
        self.h |= other.h
        self.s |= other.s
        self.b |= other.b
        self.n += other.n

class CHSSet():
    ''' Summarize sets of CHS values '''

    def __init__(self):
        self.chs = []
        self.clusters = None

    def add(self, chs, payload=0):
        ''' add an entry in CHS format '''
        self.chs.append((*chs, payload))
        self.clusters = None

    def __len__(self):
        return len(self.chs)

    def cylinders(self):
        ''' Summarize just the cylinders '''
        cyls = set(chs[0] for chs in self.chs)
        return "c" + summarize_ints(cyls)

    def cluster(self):
        ''' Cluster the geometry into clusters of like tracks '''

        if self.clusters:
            return self.clusters

        wl = list(Cluster(x) for x in sorted(self.chs))
        for pivot in (2, 1, 0):
            i = 0
            while i < len(wl) - 1:
                if wl[i].same(wl[i+1], pivot):
                    wl[i].merge(wl[i+1])
                    wl.pop(i+1)
                else:
                    i += 1
        self.clusters = wl
        return self.clusters

    def cuboids(self):
        ''' Cluster the geometry into likely cuboids '''
        cl = list(self.cluster())
        i = 0
        while i < len(cl) - 1:
            if cl[i].b != cl[i+1].b:
                i += 1
            else:
                cl[i].merge(cl.pop(i+1))
        yield from cl

    def seq(self):
        ''' String representation of clusters '''
        for cl in self.cluster():
            yield str(cl)

    def __iter__(self):

        wl = []
        for c, h, s, _p in sorted(self.chs):
            if wl:
                prev = wl[-1]
                if len(prev[0]) == 1 and c in prev[0] and len(prev[1]) == 1 and h in prev[1]:
                    prev[2].add(s)
                    continue
            wl.append([set((c,)), set((h,)), set((s,))])
        i = 0
        while i < len(wl) -1:
            if wl[i][0] == wl[i+1][0] and wl[i][2] == wl[i+1][2]:
                wl[i][1] |= wl[i+1][1]
                wl.pop(i+1)
            else:
                i += 1
        while wl:
            c, h, s = wl.pop(0)
            i = 0
            while i < len(wl):
                if wl[i][1] == h and wl[i][2] == s:
                    c |= wl[i][0]
                    wl.pop(i)
                else:
                    i += 1
            c = summarize_ints(c)
            h = summarize_ints(h)
            s = summarize_ints(s)
            yield "c" + c + "h" + h + "s" + s

def main():
    ''' Test code '''
    print(summarize_ints([3,]))
    print(summarize_ints([3,4,]))
    print(summarize_ints([3,4,5,]))
    print(summarize_ints([1,2,3,4,5,6,9,12,13,14]))
    print(summarize_ints([1,2,3,4,5,6,8,9,12,13,14]))

    cs = CHSSet()

    for c in range(0, 5):
        for h in range(0, 2):
            for s in range(0, 8):
                if h + s != 4:
                    cs.add((c,h,s))

    print(len(cs))
    for i in cs:
        print("\t", i)

    print(len(cs))
    for i in cs.seq():
        print("\t", i)

if __name__ == "__main__":
    main()
