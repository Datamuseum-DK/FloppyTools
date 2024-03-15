#/usr/bin/env python3

'''
   FM modulation byte decoding
   ~~~~~~~~~~~~~~~~~~~~~~~~~~~
'''

FM_TO_BIN = {}
REV_FM_TO_BIN = {}

def init_tables():
    for i in range(256):
        bits = bin(256|i)[3:]
        j = bits.replace('0', '--').replace('1', '##')
        FM_TO_BIN[j] = i
        j = "".join(x for x in reversed(bits)).replace('0', '--').replace('1', '##')
        REV_FM_TO_BIN[j] = i

init_tables()

def tobytes(fmstring):
    i = []
    for j in range(0, len(fmstring), 16):
        x = FM_TO_BIN.get(fmstring[j:j+16])
        if x is None:
            return None
        i.append(x)
    return bytes(i)
