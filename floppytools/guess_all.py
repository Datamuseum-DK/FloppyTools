#!/usr/bin/env python3

'''
   Try all formats 
   ~~~~~~~~~~~~~~~
'''

import main
import zilog_mcz
import dg_nova
import ibm
import dec_rx02
import wang_wcs
import hp98xx
import q1_microlite

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
