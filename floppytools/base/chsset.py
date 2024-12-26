#!/usr/bin/env python3

'''
   Summarizing of CHS lists
   ~~~~~~~~~~~~~~~~~~~~~~~~

'''

def summarize_ints(data):
    '''
       Summarize a sequence of integers using intervals

       called with:                     returns:
           [3,]				"3"
           [3,4,]			"{3,4}"
           [3,4,5,]			"{3…5}"
           [1,2,3,4,5,6,8,9,12,13,14]   "{1…6,8,9,12…14}"
           [1,2,3,4,5,6,9,12,13,14]     "{1…6,9,12…14}"
    '''

    l = []
    prev = None
    for sec in sorted(set(data)):
        if prev is not None and prev + 1 == sec:
            l[-1][1] = sec
        else:
            l.append([sec, sec])
        prev = sec
    if len(l) == 1 and l[0][0] == l[0][1]:
        return str(l[0][0])
    ll = []
    for i in l:
        if i[0] == i[1]:
            ll.append(str(i[0]))
        elif i[0] + 1 == i[1]:
            ll.append(str(i[0]))
            ll.append(str(i[1]))
        else:
            ll.append(str(i[0]) + "…" + str(i[1]))
    return "{" + ",".join(ll) + "}"

class CHSSet():
    ''' Summarize sets of CHS values '''

    def __init__(self):
        self.chs = []
        self.summary = None

    def add(self, chs):
        ''' add an entry in CHS format '''
        self.chs.append(chs)

    def __len__(self):
        return len(self.chs)

    def cylinders(self):
        ''' Summarize just the cyliners '''
        cyls = set(chs[0] for chs in self.chs)
        return "c" + summarize_ints(cyls)

    def __iter__(self):

        wl = []
        for c, h, s in sorted(self.chs):
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

if __name__ == "__main__":
    main()
