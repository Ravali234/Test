#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# vita_convert.py: Utilities for making Vita-formatted
#     waveforms.
##

## FEATURES ##

from __future__ import division

## LOGGING ##

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

## IMPORTS ##

import numpy as np
import warnings
import itertools

from cStringIO import StringIO

try:
    import bitstring as bs
except ImportError:
    logger.error("Converting to Vita format requires the bitstring module. " \
          "Please run ``easy_install bitstring`` to install it.")
    bs = None

## CONSTANTS ##

# these packet sizes were inferred from the output of the GUI given to us by II
VITA_PACKET_SIZE = int( '0xF000', 16) * 4
VELO_PACKET_SIZE = int('0x10000', 16) * 4

VELO_HEADER_FORMAT = \
    "uintle:24=velo_packet_size, uintle:8=peripheral_id, pad:32, pad:32, pad:32"
VITA_IF_WORD_FORMAT = \
    """
    uintle:16=vita_packet_size, uint:2=tsi, uint:2=tsf, uint:4=vita_packet_count,
    bin:8=if_word_const
    """
IF_WORD_CONST = '0b00011100'
    
VITA_SID_WORD_FORMAT = \
    "uintle:16=stream_id, uintle:16=dest_mask"
VITA_TRAILER_WORD_FORMAT = \
    "pad:8, uint:4=padding, hex:20=t_word_const"
T_WORD_CONST = "0x0F000"
    
VITA_WAVEFORM_FORMAT = ", ".join([
    VELO_HEADER_FORMAT,
    VITA_IF_WORD_FORMAT
])

## CLASSES ##

class VeloPacket(object):
    def __init__(self,data, peripheral_id):
        self._data = data
        self._peripheral_id = peripheral_id
        
    def write(self, f):
        """
        Writes the Velocia packet datagram to a file for loading by the FPGA.
        
        :param f: Target to which the Velocia packet will be written.
        :type f: file-like or `str`
        """
        
        if isinstance(f, str):
            with open(f, 'wb') as opened_f:
                self.write(opened_f)
            return
                
        f.write(self.datagram.tobytes())
              
    @property
    def header(self):
        if not len(self._data) % (4 * 32) == 0:
            warnings.warn("Not aligned to four 32-bit words.")
        return velo_header(4 + len(self._data) // (32), self._peripheral_id)
        
    @property
    def datagram(self):
        return self.header + self._data
        
class VitaPacket(object):
    """
    :param data: Data to be encapsulated in a Vita packet.
    :type data: `bitstring.BitArray` or `numpy.ndarray`
    :param stream_id: ID of the stream with which this Vita packet should be
        associated. Normally this will be `"0x100"` for the first stream.
    :type stream_id: `int` or `str` containing a hexadecimal value
    """
    
    def __init__(self, data, stream_id, dest_mask=1, timestamp=(0, 0), tsi=3, tsf=3, pad=True):
        if isinstance(data, bs.BitArray):
            self._data = data
        elif isinstance(data, np.ndarray):
            self._data = bs.BitString(bytes=data.astype('<i2').data)
        else:
            raise TypeError('Data must be provided as a bitstring BitArray or as a NumPy array.')
        self.packet_count = None
        if isinstance(stream_id, str):
            self._stream_id = int(stream_id, 16)
        else:
            self._stream_id = stream_id
        self._dest_mask = dest_mask
        self._timestamp = timestamp
        self._tsi = tsi
        self._tsf = tsf
        self._pad = pad
        
    @property
    def header(self):
        return vita_header(
            packet_size=8 + len(self._data) // (32),
            packet_count=self.packet_count,
            tsf=self._tsf, tsi=self._tsi,
            stream_id=self._stream_id,
            dest_mask=self._dest_mask,
            timestamp=self._timestamp
        )
        
    @property
    def datagram(self):
        return self.header + self._data + self.padding + self.trailer
        
    @property
    def n_bytes(self):
        return len(self._data) // 8
        
    @property
    def padding(self):
        if self._pad:
            return bs.BitArray('pad:8') * (16 - self.n_bytes % 16)
        else:
            return bs.BitArray('')
        
    @property
    def trailer(self):
        return vita_trailer((16 - self.n_bytes) % 16 if self._pad else 0)

class VitaReader(object):
    """
    A utility class that reads from a file-like object into one
    or more NumPy arrays containing samples.
    """

    def __init__(self):
        self._streams = {}

    def fromstream(self, stream_file):
        """
        :param stream_file: Encapsulation of one or more Vita
            packet streams, probably as obtained by decoding
            a Velocia stream using `~x6.vita_convert.VeloReader`.
        :type stream_file: `file`-like
        """

        for stream_id, vita_packet_data in _packetize_vita_stream(stream_file):
            if stream_id not in self._streams:
                self._streams[stream_id] = StringIO()
                
            self._streams[stream_id].write(vita_packet_data)
                

    def asarrays(self):
        return {
            hex(stream_id): np.fromstring(sio.getvalue(), dtype="<i2")
            for stream_id, sio in self._streams.iteritems()
        }

class VeloReader(object): # <- maybe make this inherit from IOBase?
    """
    A utility class that imitates a file, but reads and discards Velocia headers
    streamed from an underlying true file.
    """
    
    def __init__(self, true_file):
        self._true_file = true_file
        self._buffer = bytearray()
        
    def read(self, n_bytes=None):
        n_bytes_left = n_bytes 
        eof = False
        ret_buffer = bytearray()
        
        while (n_bytes_left is None or n_bytes_left > 0) and not eof:
            # If the buffer is empty, fill it with the next packet.
            if not self._buffer:
                eof = self._read_packet()
                if eof:
                    break
                
            # Figure out how many bytes to read from the buffer.
            size = min(n_bytes_left, len(self._buffer))
            ret_buffer += self._buffer[0:size]
            del self._buffer[0:size]
            n_bytes_left -= size
            
        return str(ret_buffer)
                
    def _read_packet(self):
        # TODO: if there are no more packets, return True.
        #       Otherwise, add the packet's *contents* to self._buffer,
        #       discarding the header.
        
        # Look at the header to figure out how many words long the packet is.
        header = bs.BitArray(bytes=self._true_file.read(4 * 4)) # 4 4-byte words.
        if len(header) == 0:
            return True
        
        n_packet_words, dummy = header.unpack(VELO_HEADER_FORMAT)

        # Find the number of bytes to read by converting the
        # word count to bytes and subtracting off the length of the
        # header we just read.
        n_bytes = 4 * (n_packet_words - 4)
        
        # Log that we saw a new Velo packet.
        logger.debug("Reading new Velo packet containing {} bytes.".format(n_bytes))
            
        # Now add those bytes to the buffer.
        new_bytes = self._true_file.read(n_bytes)
        self._buffer += new_bytes

        # Return True if we EOF'd.
        return len(new_bytes) == 0

class VeloVitaPacker(object):
    """
    A utility class for packing vita packets into a file in velo chunks
    
    :param filename: The filename to pack the data into
    :type filename: `str`
    :param peripheral_id: The X6 PID
    :type peripheral_id: `int`
    """
    def __init__(self, filename, peripheral_id=0):
        self._file = open(filename, 'wb')
        self._buffer = bs.BitArray('')
        self._peripheral_id = peripheral_id
        
    def pack(self, packet):
        self._buffer += packet.datagram
        while len(self._buffer.bytes) >= VELO_PACKET_SIZE:
            self._write_packet(VELO_PACKET_SIZE)
            
    def _write_packet(self, size):
        data = self._buffer[:8 * size]
        velo_packet = VeloPacket(data, self._peripheral_id)
        self._file.write(velo_packet.datagram.bytes)
        self._buffer = self._buffer[8 * size:]
            
    def flush(self):
        while len(self._buffer.bytes) > 0:
            self._write_packet(min(VELO_PACKET_SIZE, len(self._buffer.bytes)))
        
        self._file.flush()
        
## PRIVATE FUNCTIONS ##

def _packetize_vita_stream(stream_file):
    """
    Given a `file`-like containing one or more Vita streams,
    yields each Vita packet in turn along with the stream
    ID for each packet.

    :yields: ``(stream_id, packet_data)``
    """
    # Remember where we are in the counter increment.
    next_count = 0
    
    while True:
        # Read the first seven words from the stream.
        vita_header = bs.BitArray(bytes=stream_file.read(7 * 4))

        # Check for EOF.
        if len(vita_header) == 0:
            break

        # Figure out the Vita packet length.
        [
            packet_size, tsi, tsf, packet_count, ifw_const, stream_id, dest_mask
        ] = vita_header.unpack(VITA_IF_WORD_FORMAT + ", " + VITA_SID_WORD_FORMAT)
        
        # Record that we saw a packet in a given stream.
        logger.debug("Reading new Vita packet on stream 0x{0:X} with size {1} and count {2}".format(
            stream_id, packet_size, packet_count
        ))
        
        # Handle packet counts.
        if packet_count != next_count:
            warnings.warn(
                "Packet count {1} in stream 0x{0:X} didn't match expected {2}. Is this really a Vita stream?".format(
                    stream_id, packet_count, next_count
            ))

        next_count = (next_count + 1) % 16

        # Read the data and padding.
        packet_data = stream_file.read((packet_size - 7) * 4)

        # Break off the trailer word.
        trailer = bs.BitArray(bytes=packet_data[-4:])
        packet_data = packet_data[:-4]

        # Find out how much padding there is.
        [padding, dummy] = trailer.unpack(VITA_TRAILER_WORD_FORMAT)

        # Subtract that many bytes from the packet data.
        if padding > 0:
            packet_data = packet_data[:-padding]

        yield stream_id, packet_data

## FUNCTIONS ##

def parse_velo_stream(stream_filename='Data.bin'):
    """
    Given a file containing an encapsulated Velocia stream,
    unpacks the encoded Vita streams and returns them as
    NumPy arrays.

    Stream IDs in the returned `dict` are stored as strings
    as produced by the `hex` function. For instance, stream
    `256` will be encoded as `"0x100"`, as is consistent with
    II documentation.

    :param str stream_filename: Path to the stream file to load.
    :return: A dictionary from Vita stream IDs to NumPy arrays.        
    """

    vita_r = VitaReader()

    with open(stream_filename, 'rb') as f:
        velo_r = VeloReader(f)
        vita_r.fromstream(velo_r)
        
    return vita_r.asarrays()
        
        
def parse_vita_waveform(waveform_file):
    # FIXME: this is probably deprecated.
    with open(waveform_file, 'rb') as f:
        bytes = bs.BitArray(bytes=f.read())
    return bytes.unpack(VITA_WAVEFORM_FORMAT)

def velo_header(packet_size, peripheral_id):
    return bs.pack(
        VELO_HEADER_FORMAT,
        velo_packet_size=packet_size, peripheral_id=peripheral_id
    )
    
def vita_header(packet_size, packet_count, stream_id, timestamp=(0, 0), dest_mask=0, tsf=3, tsi=3):
    return bs.pack(
            VITA_IF_WORD_FORMAT,
            vita_packet_size=packet_size, vita_packet_count=packet_count,
            tsf=tsf, tsi=tsi, if_word_const=IF_WORD_CONST
        ) + bs.pack(
            VITA_SID_WORD_FORMAT,
            dest_mask=dest_mask, stream_id=stream_id
        ) + bs.pack(
            'pad:32, 0x00000300' # Reserved words.
        ) + bs.pack(
            'uintle:32, uintle:64',
            *timestamp
        )
        
def vita_trailer(padding=0):
    return bs.pack(
        VITA_TRAILER_WORD_FORMAT,
        padding=padding,
        t_word_const=T_WORD_CONST
    )
      
def repeat_iter(i):
    return itertools.chain.from_iterable(itertools.repeat(i))
       
def rawbin_to_velo(velo_filename, rawbin_file_dict, peripheral_id):
    """
    Converts raw binary waveforms into vita packets spliced into velo packets 
    and saves this new binary to disk.
    
    :param str velo_filename: File name of the output velo packets binary.
    :param rawbin_file_dict: A dictionary associating stream IDs to raw binary 
        file names.
    :type rawbin_file_dict: A `dict` of the form, e.g., 
        ``{'0x100': 'file1.bin', '0x101': 'file2.bin'}``
    :param int peripheral_id: The PID of the X6
    """
    
    packer = VeloVitaPacker(velo_filename, peripheral_id)
    
    files = [
        (stream_id, open(filename, 'rb'))
        for stream_id, filename in rawbin_file_dict.items()
    ]
    
    eof = {stream_id: False for stream_id in rawbin_file_dict}
    
    for packet_count, (stream_id, file_obj) in itertools.izip(repeat_iter(range(16)), repeat_iter(files)):
        
        if not eof[stream_id]:
            data = file_obj.read(VITA_PACKET_SIZE)
            
            if not data:
                eof[stream_id] = True
                if all(eof.values()):
                    break
            else:
                # Make a Vita packet with data.
                packet = VitaPacket(
                        data=bs.BitArray(bytes=data),
                        stream_id=stream_id,
                        pad=False
                    )
                # Note that contrary to the documentation, we don't use 
                # separate counters for the separate streams
                packet.packet_count = packet_count
                packer.pack(packet)
                
            
    packer.flush()
    
