#!/usr/bin/env python3

'''
   Disk class
   ~~~~~~~~~~
'''

class DiskSector():
    ''' ... '''

    def __init__(self, chs):
        self.chs = chs
        self.readings = []
        self.values = {}
        self.lengths = set()

    def __len__(self):
        return len(self.readings)

    def add_sector(self, read_sector):
        assert read_sector.chs == self.chs
        assert read_sector.good
        self.readings.append(read_sector)
        i = self.values.get(read_sector.octets)
        if i is None:
            i = []
            self.values[read_sector.octets] = i
        i.append(read_sector)
        self.lengths.add(len(read_sector.octets))

    def status(self):
        if len(self.values) == 0:
            return False, '╳'
        if len(self.values) <= 1:
            return True, "╳▁▂▃▄▅▆▇█"[min(len(self.readings), 8)]
        return False, '▒'

    def write_data(self):
        if len(self.values) == 0:
            return None
        assert len(self.values) == 1
        return list(self.values.keys())[0]

class Disk():

    def __init__(self, name):
        self.name = name
        self.disk_sectors = {}
        self.defined_geometry = False
        self.has_cylinders = set()
        self.has_heads = set()
        self.has_sectors = set()
        self.last_addition = (-1, -1, -1)
        self.format = None

    def __str__(self):
        return "{DISK " + self.name + "}"

    def define_geometry(self, first_chs, last_chs):
        assert len(first_chs) == 3
        assert len(last_chs) == 3
        for cyl in range(first_chs[0], last_chs[0]+1):
            self.has_cylinders.add(cyl)
            for head in range(first_chs[1], last_chs[1]+1):
                self.has_heads.add(head)
                for sector in range(first_chs[2], last_chs[2]+1):
                    self.has_sectors.add(sector)
                    chs = (cyl, head, sector)
                    self.disk_sectors[chs] = DiskSector(chs)
        self.defined_geometry = True

    def add_sector(self, sector):
        self.last_addition = sector.chs
        disksector = self.disk_sectors.get(sector.chs)
        assert disksector is not None
        disksector.add_sector(sector)

    def show_geometry(self):
        i = []
        for j in (self.has_cylinders, self.has_heads, self.has_sectors):
            if not j:
                i.append("?")
                continue
            i.append(str(min(j)) + "…" + str(max(j)))
        return "(" + ", ".join(i) + ")"

    def horizontal_status(self):
        l1 = []
        for cylinder in sorted(self.has_cylinders):
            if cylinder == self.last_addition[0]:
                l1.append('↓')
            elif cylinder % 10 == 0:
                l1.append('%d' % (cylinder // 10))
            elif cylinder % 10 == 5:
                l1.append(':')
            else:
                l1.append('.')
        yield ''.join(l1)

        incomplete_cylinders = set()
        for head in sorted(self.has_heads):
            if len(self.has_heads) > 1:
                yield "head=%d" % head
            for sector in sorted(self.has_sectors):
                i = []
                for cylinder in sorted(self.has_cylinders):
                    chs = (cylinder, head, sector)
                    disk_sector = self.disk_sectors.get(chs)
                    if disk_sector is None:
                        i.append('╳')
                        incomplete_cylinders.add(cylinder)
                        continue
                    j, k = disk_sector.status()
                    i.append(k)
                    if not j:
                        incomplete_cylinders.add(cylinder)
                yield ''.join(i)
        missing = []
        for i in sorted(incomplete_cylinders):
            if len(missing) > 0 and i == missing[-1][-1] + 1:
                missing[-1][-1] = i
            else:
                missing.append([i, i])
        i = []
        for j in missing:
            if j[0] == j[1]:
                i.append(str(j[0]))
            else:
                i.append(str(j[0]) + "…" + str(j[1]))
        if i:
            yield "Missing cylinders: " + ', '.join(i)
        else:
            yield "Complete"

    def status(self):
        yield "Status " + self.name + " " + self.show_geometry() + " " + str(self.format)
        if len(self.has_cylinders) <= 85:
            yield from self.horizontal_status()

    def write_bin_file(self, filename):
        lengths = set()
        for disk_sector in self.disk_sectors.values():
            lengths |= disk_sector.lengths
        if len(lengths) == 0:
            return
        assert len(lengths) == 1
        sector_length = list(lengths)[0]
        unread = b'_UNREAD_' * (1 + (sector_length // 8))
        unread = unread[:sector_length]
        with open(filename, "wb") as fo:
            for cylinder in range(min(self.has_cylinders), max(self.has_cylinders) + 1):
                for head in range(min(self.has_heads), max(self.has_heads) + 1):
                    for sector in range(min(self.has_sectors), max(self.has_sectors) + 1):
                        chs = (cylinder, head, sector)
                        disk_sector = self.disk_sectors.get(chs)
                        if disk_sector is None:
                            fo.write(unread)
                            continue
                        data = disk_sector.write_data()
                        if data is None:
                            fo.write(unread)
                            continue
                        fo.write(data)
