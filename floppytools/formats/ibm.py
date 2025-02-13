#/usr/bin/env python3

'''
   IBM format
   ~~~~~~~~~~
'''

import crcmod

from ..base import media
from ..base import fluxstream as fs

crc_func = crcmod.predefined.mkCrcFun('crc-ccitt-false')

class IbmTrack():
    ''' ... '''

class IbmFmTrack(IbmTrack):

    GAP1 = 16
    SYNC = '|---' * GAP1

    FM_ADDRESS_MARK = (0xc7, 0xfe)
    AM_PATTERN = SYNC + fs.make_mark_fm(*FM_ADDRESS_MARK)

    DATA_MARK = (0xc7, 0xfb)
    DATA_PATTERN = SYNC + fs.make_mark_fm(*DATA_MARK)

    DELETE_MARK = (0xc7, 0xf8)
    DELETE_PATTERN = SYNC + fs.make_mark_fm(*DELETE_MARK)

    MAX_GAP2 = 100

    def process_stream(self, media, stream, clock=50):
        flux = stream.fm_flux(clock)
        for am_pos in stream.iter_pattern(flux, pattern=self.AM_PATTERN):
            address_mark = stream.flux_data_fm(flux[am_pos-32:am_pos+(6*32)])
            if address_mark is None:
                media.trace("NOAM", am_pos)
                continue
            am_crc = crc_func(address_mark)
            if am_crc != 0:
                media.trace("AMCRC", am_pos, address_mark.hex())
                continue
            chs = (address_mark[1], address_mark[2], address_mark[3])
            sector_size = 128 << address_mark[4]
            extra = [ "FM", "clock=%d" % clock]
            data_pos = flux.find(self.DATA_PATTERN, am_pos, am_pos + self.MAX_GAP2 * 32)
            if data_pos < 0:
                data_pos = flux.find(self.DELETE_PATTERN, am_pos, am_pos + self.MAX_GAP2 * 32)
                if data_pos >= 0:
                    extra.append("deleted")
            if data_pos < 0:
                media.trace("NOFLAG", am_pos)
                continue

            data_pos += len(self.DATA_PATTERN)
            data = stream.flux_data_fm(flux[data_pos-32:data_pos+((2+sector_size)*32)])
            if data is None:
                media.trace("NODATA", am_pos)
                continue

            data_crc = crc_func(data)
            if data_crc:
                media.trace("DATACRC", am_pos, address_mark.hex(), hex(data_crc), len(data), data.hex())
                continue

            yield chs, data[1:1+sector_size], extra

class IbmMfmTrack(IbmTrack):

    GAP1 = 32
    SYNC = '|-' * GAP1

    MFM_ADDRESS_MARK = ((0x0a, 0xa1), (0x0a, 0xa1), (0x0a, 0xa1), (0x00, 0xfe))
    AM_PATTERN = SYNC + ''.join(fs.make_mark(*i) for i in MFM_ADDRESS_MARK)

    DATA_MARK = ((0x0a, 0xa1), (0x0a, 0xa1), (0x0a, 0x0a1), (0x00, 0xfb))
    DATA_PATTERN = SYNC + ''.join(fs.make_mark(*i) for i in DATA_MARK)

    DELETE_MARK = ((0x0a, 0xa1), (0x0a, 0xa1), (0x0a, 0x0a1), (0x00, 0xf8))
    DELETE_PATTERN = SYNC + ''.join(fs.make_mark(*i) for i in DATA_MARK)

    MAX_GAP2 = 60

    def process_stream(self, media, stream, clock=50):
        flux = stream.mfm_flux(clock)
        for am_pos in stream.iter_pattern(flux, pattern=self.AM_PATTERN):
            address_mark = stream.flux_data_mfm(flux[am_pos-64:am_pos+(6*16)])
            if address_mark is None:
                media.trace("NOAM", am_pos)
                continue
            am_crc = crc_func(address_mark)
            if am_crc != 0:
                media.trace("AMCRC", am_pos)
                continue
            chs = (address_mark[4], address_mark[5], address_mark[6])

            extra = [ "MFM", "clock=%d" % clock]
            data_pos = flux.find(self.DATA_PATTERN, am_pos + 20 * 16, am_pos + self.MAX_GAP2 * 16)
            if data_pos < 0:
                data_pos = flux.find(self.DELETE_PATTERN, am_pos, am_pos + self.MAX_GAP2 * 16)
                if data_pos >= 0:
                    extra.append("deleted")
            if data_pos < 0:
                media.trace("NOFLAG", am_pos)
                continue
            data_pos += len(self.DATA_PATTERN)

            sector_size = 128 << address_mark[7]

            off = -4*16
            width = (6 + sector_size) * 16
            data = stream.flux_data_mfm(flux[data_pos+off:data_pos+width+off])
            if data is None:
                media.trace("NODATA", am_pos)
                continue

            data_crc = crc_func(data)

            if data_crc != 0:
                media.trace("DATACRC", am_pos, len(data), hex(data_crc), data[:32].hex())
                continue

            yield chs, data[4:4+sector_size], extra

class Ibm(media.Media):

    ''' IBM format floppy disks '''

    aliases = ["IBM"]

    FM_ADDRESS_MARK = (0xc7, 0xfe)
    MFM_ADDRESS_MARK = ((0x0a, 0xa1), (0x0a, 0xa1), (0x0a, 0xa1), (0x00, 0xfe))
    DATA_MARK = (0xc7, 0xfb)
    DELETE_MARK = (0xc7, 0xf8)
    GAP1 = 16
    MAX_GAP2 = 100

    CLOCKS = [50, 80]

    FMTRACK = IbmFmTrack()
    MFMTRACK = IbmMfmTrack()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.todo = []
        for i in self.CLOCKS:
            self.todo.append((self.FMTRACK, i,))
            self.todo.append((self.MFMTRACK, i,))

    def process_stream(self, stream):
        ''' ...  '''

        retval = False
        for i in range(len(self.todo)):
            track, clock = self.todo[0]
            for chs, data, extra in track.process_stream(self, stream, clock):
                self.did_read_sector(
                    chs,
                    data,
                    stream,
                    flags=extra,
                )
                retval = True
            if retval:
                return retval
            self.todo.append(self.todo.pop(0))
        return False

"""
class IbmFm128Ss(IbmFm):
    ''' ... '''
    #FIRST_CHS = (0, 0, 1)
    #LAST_CHS = (76, 1, 26)
    #SECTOR_SIZE = 128

class IbmFm128Ds(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 26)
    SECTOR_SIZE = 128

class IbmFm256Ss(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 15)
    SECTOR_SIZE = 256

class IbmFm256Ds(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 15)
    SECTOR_SIZE = 256

class IbmFm512Ss(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 0, 8)
    SECTOR_SIZE = 512

class IbmFm512Ds(IbmFm):
    ''' ... '''
    FIRST_CHS = (0, 0, 1)
    LAST_CHS = (76, 1, 8)
    SECTOR_SIZE = 512

class Osborne(IbmFm):
    ''' ... '''
    GEOMETRY = ((0, 0, 1), (39, 0, 10), 256)
    CLOCK_FM = 80

class PC360(IbmFm):
    ''' ... '''
    GEOMETRY = ((0, 0, 1), (39, 0, 9), 512)
    CLOCK_FM = 80
    CLOCK_MFM = 80

"""

ALL = (
    #IbmFm128Ss,
    #IbmFm128Ds,
    #IbmFm256Ss,
    #IbmFm256Ds,
    #IbmFm512Ss,
    #IbmFm512Ds,
    #Osborne,
    #PC360,
    Ibm,
)
