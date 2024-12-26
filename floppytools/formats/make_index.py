#!/usr/bin/env python3

'''
    I wish I could come up with a better design pattern here, but
    until that happens, this will have to do:

    I really dont want to import all the formats, just to ask them
    all which one I should use, so I want a name->format lookup
    facility, and the names should live in the implementation of
    the format, not in some central table.

    This is the program which builds that lookup facility.
'''


import glob
import importlib

#print("#P", __package__)


def main():

    inventory = {}
    mods = {}

    def add_format(name, module, index):
        if name not in inventory:
            inventory[name] = []
        inventory[name].append((module, index))

    for fn in sorted(glob.glob("*.py")):
        if fn in (
            "__init__.py",
            "index.py",
            "make_index.py",
            "_.py",
        ):
            continue
        bn = fn[:-3]
        m = importlib.import_module("." + bn, "floppytools.formats")
        #print("#M", m)
        for idx, fmt in enumerate(m.ALL):
            i = fmt("/tmp", load_cache=False, save_cache=False)
            mods[(bn, idx)] = (i.name, i.aliases, i.__doc__)
            add_format("all", bn, idx)
            add_format(i.name, bn, idx)
            for j in i.aliases:
                add_format(j, bn, idx)

    with open("index.py", "w") as file:
        file.write('#!/usr/bin/env python3\n')
        file.write('\n')
        file.write("''' MACHINE GENERATED FILE, see make_index.py'''\n")
        file.write('\n')

        if True:
            file.write('documentation = {\n')
            for i, j in sorted(inventory.items()):
                mod = mods[j[0]]
                if i != mod[0]:
                    continue
                file.write('    "%s": [\n' % i)
                for x, y in j:
                    mod = mods[(x, y)]
                    file.write('        %s,\n' % str([mod[2].strip()]))
                file.write('    ],\n')
            file.write('}\n')
            file.write('\n')
        if True:
            file.write('aliases = {\n')
            for i, j in sorted(inventory.items()):
                mod = mods[j[0]]
                if i == mod[0] or i == "all":
                    continue
                file.write('    "%s": [\n' % i)
                for x, y in j:
                    mod = mods[(x, y)]
                    file.write('        "%s",\n' % mod[0])
                file.write('    ],\n')
            file.write('}\n')
            file.write('\n')

        file.write('def find_formats(target):\n')
        pfx = ""
        for i, j in sorted(inventory.items()):
            file.write('    %sif target == "%s":\n' % (pfx, i))
            pfx = "el"
            seen = set()
            for modname, idx in j:
                if modname not in seen:
                    file.write('        from . import %s\n' % modname)
                    seen.add(modname)
                clsname = mods[(modname, idx)][0]
                file.write('        yield ("%s", %s.ALL[%d])\n' % (clsname, modname, idx))


if __name__ == "__main__":
    main()
