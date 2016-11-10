#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# vita_convert.py: Utilities for formatting waveforms into binaries suitable 
# for a given X6 instance.
##

## FEATURES ##

from __future__ import division

## IMPORTS ##

import os
import numpy as np
import scipy.io as sio
import tempfile as tf
import x6.vita_convert as vc
from itertools import izip
from x6 import TX_CHANNELS

## CONSTANTS ##

CHANNEL_STREAM_MAP = {'0x100':[0,1], '0x101':[2,3]}

BIN_FILE =0;
MAT_FILE = 1;
NP_ARRAY = 2;


CHUNK_SIZE = 5000000
MINIMUM_DATA_SIZE = 1000000
DATA_TYPE = '<i2'
DATA_ITEM_SIZE = np.dtype(DATA_TYPE).itemsize

## CLASSES ##

class Waveform(object):
    """
    A file-like class to seamlessly deal with waveforms in different formats.
    
    :param waveform: The data for your waveform
    :type waveform: `str` for file locations where non .mat files are assumed to 
        be binary in 16bit little-endian format; `file` for any readable open 
        file-like object assumed to be in 16bit little-endian format; 
        `numpy.ndarray` for a numpy 1D array (this array is automatically astype'd)
        to the correct data type
    :param str var_name: If ``waveform`` is the name of a MATLAB MAT-file or
        a NumPy NPZ file, then ``var_name`` specifies which variable to load
        from that file.
    :param str mode: Allows you to override the mode in any function call to
        open. This option is only relevant if your waveform is being stored
        in a file and not in memory.
    """

    def __init__(self, waveform, var_name=None, mode='rb'):
        # pos is the current position in the waveform measured in DATA_TYPEs
        self._pos = 0
        self._mode = mode
        
        # Decide how to handle the waveform based on its type and contents.
        if isinstance(waveform, str):
            if  waveform[-3:] == 'mat':
                # Load the specified variable from the waveform file
                # and set it as an array.
                self._from = waveform
                self._fromtype = "MAT-file"
                self.__set_to_ndarray(
                    sio.loadmat(waveform, variable_names=[var_name])[var_name]
                )
                
            elif waveform[-3:] == 'npy':
                # Load the NumPy array from the file, then set the buffer
                # to point to the loaded array.
                self._from = waveform
                self._fromtype = "NumPy file"
                self.__set_to_ndarray(np.load(waveform))
                
            elif waveform[-3:] == 'npz':
                # Load the NPZ file, then select the appropriate array from it.
                self._from = waveform
                self._fromtype = "NumPy file"
                self.__set_to_ndarray(np.load(waveform)[var_name])                
                
            else:
                # Everything else is treated as a raw binary file.
                self._from = waveform
                self._fromtype = "Raw binary filename"
                self._waveform_type = BIN_FILE
                self._data_handle = open(waveform, self._mode)
            
        elif isinstance(waveform, file):
            self._from = None
            self._fromtype = "Open raw binary file"
            self._waveform_type = BIN_FILE
            self._data_handle = waveform
            
        elif hasattr(waveform, 'file'):
            # Fix for the TemporaryFile hack on Windows.
            self._from = None
            self._fromtype = "Open raw binary file"
            self._waveform_type = BIN_FILE
            self._data_handle = waveform.file
            
        elif isinstance(waveform, np.ndarray):
            self._from = None
            self._fromtype = "ndarray of shape {}".format(waveform.shape)
            self.__set_to_ndarray(waveform)
            
        else:
            raise TypeError('Data must be provided in a format that it was not.')
            
    def __set_to_ndarray(self, array):
        self._waveform_type = NP_ARRAY
        self._data_handle = array.astype(DATA_TYPE).data
    
    def __repr__(self):
        return "<Waveform from {1}{0}>".format(
            " " + self._from if self._from is not None else "",
            self._fromtype
        )
    
    def get_chunk(self, chunk_size):
        """
        Returns chunk_size samples from the waveform at the current position
        """

        if self._waveform_type == BIN_FILE:
            data = np.fromfile( self._data_handle, 
                                dtype=DATA_TYPE, 
                                count=chunk_size)
            self._pos += chunk_size
            self._pos = min(self._pos, DATA_ITEM_SIZE * self._data_handle.tell())
            return data
        elif self._waveform_type == NP_ARRAY:
            fetch_size = min(chunk_size, len(self._data_handle) // DATA_ITEM_SIZE - self._pos)
            if self._pos < len(self._data_handle) // DATA_ITEM_SIZE:
                data = np.frombuffer(   self._data_handle, 
                                        dtype=DATA_TYPE, 
                                        count=fetch_size,
                                        offset=self._pos * DATA_ITEM_SIZE)
                self._pos += chunk_size
                self._pos = min(self._pos, self.length)
            else:
                data = np.empty(0,dtype=DATA_TYPE)
            return data
        else:
            raise NotImplementedError('Reading of this format not supported yet.')
            
    def set_chunk(self, chunk):
        """
        Writes the 1D ndarray chunk to the current position of the waveform
        """
        if self._waveform_type == BIN_FILE:
            self._data_handle.write(chunk.astype(DATA_TYPE).data)
            self._pos = DATA_ITEM_SIZE * self._data_handle.tell()
        else:
            raise NotImplementedError('Writing of this format not supported yet.')
            
    def seek(self, ndata, mode=0):
        if self._waveform_type == BIN_FILE:
            self._data_handle.seek(ndata * DATA_ITEM_SIZE, mode)
        elif self._waveform_type == NP_ARRAY:
            if mode == 0:
                self._pos = min(ndata, self.length)
            elif mode == 1:
                self._pos = min(self._pos + ndata, self.length)
            elif mode == 2:
                self._pos = min(self.length + ndata, self.length)
            else:
                raise ValueError('Unexpected mode value')
        else:
            raise NotImplementedError('Seeking of this format not supported yet.')
    
    @ property        
    def length(self):
        """
        The current number of samples in the waveform
        """
        if self._waveform_type == BIN_FILE:
            curr_pos = self._data_handle.tell()
            self._data_handle.seek(0, 2)
            num_bytes = self._data_handle.tell()
            self._data_handle.seek(curr_pos)
        elif self._waveform_type == NP_ARRAY:
            num_bytes = len(self._data_handle)
        else:
            raise NotImplementedError('Finding the length of this format not supported yet.')
            
        return num_bytes // DATA_ITEM_SIZE
        
class IQWaveform(Waveform):
    """
    Subclass of `Waveform` representing the pairing of two channels into
    a single logical channel with in-phase and quadrature parts.
    """
    def __init__(self, waveform_i, waveform_q):
        self.waveform_i = Waveform(waveform_i)
        self.waveform_q = Waveform(waveform_q)

    def __repr__(self):
        return "<IQWaveform I = ({}), Q = ({})>".format(
            str(self.waveform_i), str(self.waveform_q)
        )

    def __str__(self):
        return "(I=({}), Q=({}) [iq]".format(
            str(self.waveform_i), str(self.waveform_q)
        )

## FUNCTIONS ##

def rewind_write(waveform_out, waveform_in, n_samp):
    """
    Writes n_samp samples from waveform_in (starting at the beginning)
    to waveform_out (starting at the current position). If n_samp is 
    greater than the length of waveform_in, waveform_in is repeatedly
    added until the exact number of samples has been written to 
    waveform_out.
    
    :param Waveform waveform_out: The `Waveform` to write to
    :param Waveform waveform_in: The `Waveform` to read from
    :param int n_samp: The number of samples in total to write to waveform_out
    """
    samps_written = 0
    while samps_written < n_samp:
        waveform_in.seek(0)
        if n_samp - samps_written > n_samp % waveform_in.length:
            # try to get n_samp samples, but we might get less if
            # waveform_in is shorter than n_samp
            data = waveform_in.get_chunk(n_samp)
        else:
            # there are more points in waveform_in than we have left
            # to add
            data = waveform_in.get_chunk(n_samp % waveform_in.length)
        waveform_out.set_chunk(data)
        samps_written += len(data)
        
def apply_phase(iqwaveform, phase):
    """
    Applies a phase between the two waveforms in iqwaveform.
    
    :param IQWaveform iqwaveform: The `IQWaveform` to apply a phase to.
    :param phase: The phase to apply.
    :type phase: Either a `float` specifying the angle in radians, or a 
        `tuple` of the form (n, p) where
        p is an integer specifying how many times to divid the unit circle,
        and n is how many multiples of this division we want to rotate by.
    :return: A new instance of IQWaveform where the phase has been applied
    """
    
    try:
        angle = phase[0] * (2 * np.pi) / phase[1]
    except TypeError:
        angle = phase
    
    iqwaveform.waveform_i.seek(0)
    iqwaveform.waveform_q.seek(0)
    
    min_length = min(iqwaveform.waveform_i.length, iqwaveform.waveform_q.length)
    
    iq_array = np.vstack((
        iqwaveform.waveform_i.get_chunk(min_length), 
        iqwaveform.waveform_q.get_chunk(min_length)
    ))
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    
    rotated_iq_array = np.dot(rotation, iq_array)
    
    return IQWaveform(rotated_iq_array[0], rotated_iq_array[1])
    
    

def binary_interleave(output_file, waveform1=None, waveform2=None):
    """
    Writes the data in the two input waveforms alternately, value by value, to 
    the output file. If one of the input waveforms is None, then zeros are 
    written in  place of its data. If both input waveforms are set to None, 
    nothing is written to the output file. The number of values written to the 
    output file is equal to twice the number of values contained in the 
    larger input waveform.
    
    :param file output_file: A file-like object to write to
    :param Waveform waveform1: A `~x6.process_waveform.Waveform` to write to 
        the even indeces of the output file
    :param Waveform waveform2: A `~x6.process_waveform.Waveform` to write to 
        the odd indeces of the output file
    :return: The total number of samples written to output_file.
    """
    
    eof1 = waveform1 is None
    eof2 = waveform2 is None
    total_written_count = 0

    # loop until we have read both waveforms completely
    while not eof1 or not eof2:
    
        len1 = 0
        len2 = 0
    
        # get a chunk size from each of the input files
        if not eof1:
            data1 = waveform1.get_chunk(CHUNK_SIZE)
            len1 = len(data1)
            if len1 == 0:
                eof1 = True
        if not eof2:
            data2 = waveform2.get_chunk(CHUNK_SIZE)
            len2 = len(data2)
            if len2 == 0:
                eof2 = True       
        
        # the actual interweaving. zeros go everywhere there is no data to put
        chunk = np.zeros(2*max(len1, len2), dtype=DATA_TYPE)
        if len1 > 0: chunk[:2*len1:2] = data1
        if len2 > 0: chunk[1:2*len2+1:2] = data2      
        
        total_written_count += 2 * max(len1, len2)
        print "Interweaved {0} bytes with {1} bytes.".format(len1 * DATA_ITEM_SIZE, len2 * DATA_ITEM_SIZE)  
        
        # append the chunk to the output file
        output_file.write(chunk.data)
        
    return total_written_count


def binary_copy(output_file, waveform):
    """
    Copies the data in a waveform to a file.
    
    :param output_file: Destination of the copy operation.
    :type output_file: `str` or `file`-like
    :param Waveform waveform: Source of data to be copied.
    :return: The total number of samples copied.
    """

    total_written_count = 0
       
    if isinstance(output_file, str):
        o_f = open(output_file, 'wb')
    else:
        o_f = output_file

    # write in chunks so as not to exhaust RAM
    while True:
        data = waveform.get_chunk(CHUNK_SIZE)
        if len(data) == 0:
            break
        o_f.write(data.data)
        total_written_count += len(data)
        print "Copied {} bytes.".format(len(data) * DATA_ITEM_SIZE)
        
    return total_written_count
    
def write_zeros(file_obj, zero_count):
    """
    Write zero_count zeros to the open file-like object file_obj. The data type of
    the written zeros is given by `x6.process_waveform.DATA_TYPE`.
    
    :params file file_obj: The open file-like object to write to.
    :params int zero_count: The number of zeros to write.
    """
    
    total_written_count = 0
    
    # write in chunks so as not to exhaust RAM
    while total_written_count < zero_count:
        num_to_add = min(CHUNK_SIZE, zero_count-total_written_count)
        file_obj.write(np.zeros(num_to_add, dtype=DATA_TYPE).data)
        total_written_count += num_to_add
        print "Wrote {} zeros to end of file.".format(num_to_add * DATA_ITEM_SIZE)
        
    return total_written_count
        
def waveform_to_velo(active_channels, output_filename, waveform0=None, waveform1=None, waveform2=None, waveform3=None, peripheral_id=0, rewind=True):
    """
    Combines up to four waveforms into a vita/velo file based on which channels
    are active. If more than one channel from the same stream is active, then
    the two corresponding waveforms are interleaved on that stream. If a stream 
    needs to be interleaved but one of the corresponding waveforms is None, then
    the other waveform is interleaved with zeros. 
    See `x6.process_waveform.CHANNEL_STREAM_MAP` to see which streams are 
    associated with which channels.
    
    :param list active_channels: A list of length four where each entry 
        corresponds to a channel, and each should be set to True or False.
    :param str output_filename: A string specifying the output file name of the
        velo file.
    :param waveform0: The waveform to assign to channel 0.
    :type waveform0: `~x6.process_waveform.Waveform` or None
    :param waveform1: The waveform to assign to channel 1.
    :type waveform1: `~x6.process_waveform.Waveform` or None
    :param waveform2: The waveform to assign to channel 2.
    :type waveform2: `~x6.process_waveform.Waveform` or None
    :param waveform3: The waveform to assign to channel 3.
    :type waveform4: `~x6.process_waveform.Waveform` or None
    :param int peripheral_id: The peripheral_id of the x6 board.
    :param bool rewind: Whether or not to call seek(0) on each of the input
        waveforms.
    """
    
    waveforms = [waveform0, waveform1, waveform2, waveform3]
    rawbin_file_dict = {}
    tmp_file_names = []
    
    # go to the beginning of the waveform if rewind is True
    for waveform in waveforms:
        if rewind and waveform is not None:
            waveform.seek(0)
    
    # useful warnings ...
    for channel, waveform in enumerate(waveforms):
        if waveform and not active_channels[channel]:
            print "Warning: Channel {} is not active, and so the corresponding waveform will not be loaded.".format(channel)
  
    for idx, stream in enumerate(CHANNEL_STREAM_MAP):
        
        ch0, ch1 = CHANNEL_STREAM_MAP[stream]   
        
        if any([waveforms[ch] is not None for ch in [ch0, ch1]]) and any([active_channels[ch] for ch in [ch0, ch1]]):
           
            # create a temporary file to store the interleaved (or otherwise) data
            with tf.NamedTemporaryFile(mode='wb',delete=False) as tmp_file:
                tmp_file_names.append(tmp_file.name)
                
                words_written = 0
                
                print "Stream {}: active channels {}, {}.".format(stream, active_channels[ch0], active_channels[ch1])
                if active_channels[ch0] and not active_channels[ch1]:
                    # in this case we should not interleave
                    words_written = binary_copy(tmp_file, waveforms[ch0])
                elif not active_channels[ch0] and active_channels[ch1]:
                    # in this case we should not interleave
                    words_written = binary_copy(tmp_file, waveforms[ch1])
                else:
                    # in this case we should interweave
                    words_written = binary_interleave(tmp_file, waveforms[ch0], waveforms[ch1])
                
                # For a reason we don't understand, and that isn't documented, 
                # it seems that there is some minimum data size we must obey 
                # for the FPGA to work properly on multiple channels.
                # We haven't bothered to find this minimum exactly, but we know
                # it is somewhere between 100 and 1000000 samples
                if words_written < MINIMUM_DATA_SIZE:
                    write_zeros(tmp_file, MINIMUM_DATA_SIZE - words_written)
                
                rawbin_file_dict.update({stream: tmp_file.name})
                

    # finally, write our data to vita/velo format
    if any([waveform is not None for waveform in waveforms]):
        vc.rawbin_to_velo(output_filename, rawbin_file_dict, peripheral_id)
    else:
        print "Warning: Nothing to do...no file written."
    
    # delete all temporary files
    for tmp_file_name in tmp_file_names:
        os.remove(tmp_file_name)

def velo_to_waveform(active_channels, velo_file=None):
    """"
    Interprets a velo_file as data to be sent to the DACs of the x6, and
    returns the waveforms to be executed on the four channels.
    
    :param list active_channels: A length-four list of bools specifying 
        which of the four DA channels of the x6 will be active.
    :param velo_file: The file name of a velo/vita formatted file, for 
        example, as outputted by `~x6.process_waveform.waveform_to_velo`
    :return: A dictionary from channel names to `Waveform`s or None, e.g.,
        {'DA0': Waveform(..), 'DA1': None, 'DA2': Waveform(..), 'DA3': None}
    """
    
    waveforms = [None, None, None, None]    
    
    if velo_file is not None:    
    
        # All of the hard work is done in this function:
        stream_dict = vc.parse_velo_stream(velo_file)
        
        # Now we just need some logic statements to figure out how many waveforms
        # there are, whether to deinterleave, etc.
        for stream, array in stream_dict.iteritems():
            
            ch0, ch1 = CHANNEL_STREAM_MAP[stream]
            
            if active_channels[ch0] and active_channels[ch1]:
                # we need to deinterleave since both channels in the stream are active
                waveforms[ch0] = Waveform(array[::2])
                waveforms[ch1] = Waveform(array[1::2])
            elif active_channels[ch0] and not active_channels[ch1]:
                # no deinterleaving required; just channel 0
                waveforms[ch0] = Waveform(array)
            elif not active_channels[ch0] and active_channels[ch1]:
                # no deinterleaving required; just channel 1
                waveforms[ch1] = Waveform(array)
            
    return {
        channel_name: waveform 
        for channel_name, waveform in izip(TX_CHANNELS[:4], waveforms)
    }
    
    
    
    
    
    