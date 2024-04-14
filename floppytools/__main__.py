#!/usr/bin/env python3

'''
   Try all formats 
   ~~~~~~~~~~~~~~~
'''

from . import main
from . import zilog_mcz
from . import dg_nova
from . import ibm
from . import dec_rx02
from . import wang_wcs
from . import hp98xx
from . import q1_microlite

if __name__ == "__main__":
    main.Main(
        *ibm.ALL,
        dg_nova.DataGeneralNova,
        zilog_mcz.ZilogMCZ,
        dec_rx02.DecRx02,
        wang_wcs.WangWcs,
        *hp98xx.ALL,
        q1_microlite.Q1MicroLite,
    )
