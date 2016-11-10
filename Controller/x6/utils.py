#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# utils.py: Various utility functions and classes needed by
#     different parts of the X6 driver suite.
##
# Authors: Christopher Granade (cgranade@cgranade.com) and
#     Ian Hincks.
##

## IMPORTS #####################################################################

import tempfile as tf
import ConfigParser as cp
import warnings
import StringIO
import numpy as np
import scipy.io as sio
import os, sys
#import x6 as x6

from contextlib import contextmanager

## FUNCTIONS ###################################################################

def strip_spaces_from_ini(filename):

    separator = "="
    lines = file(filename).readlines()

    with open(filename, "w") as fp:
        for line in lines:
            line = line.strip()
            if not line.startswith("#") and separator in line:
                assignment = line.split(separator, 1)
                assignment = map(str.strip, assignment)
                fp.write("%s%s%s\n" % (assignment[0], separator, assignment[1]))
            else:
                fp.write(line + "\n")

def mk_named_temp():
    f = tf.NamedTemporaryFile(delete=False)
    f.close()
    return f.name

@contextmanager
def working_directory(new_wd):
    """
    Sets the working directory during a context block to be equal to ``new_wd``,
    then returns to the previous working directory.
    """
    old_wd = os.getcwd()
    
    # If told to start in a file, go up to the next directory above that.
    if not os.path.isdir(new_wd):
        new_wd = os.path.abspath(os.path.dirname(new_wd))
        
    os.chdir(new_wd)
    yield
    os.chdir(old_wd)
    
def find_on_path(filename):
    """
    Searches sys.path for a given file, using the technique suggested at
    http://dotnot.org/blog/archives/2004/03/06/find-a-file-in-pythons-path/.
    """

    # Loop over folders in sys.path, and append to each one the name of the file
    # we're looking for.    
    for folder in sys.path:
        possible = os.path.join(folder, filename)
        if os.path.isfile(possible):
            return possible
    return None
    
def search_for_file(pathname, starting_point=None):
    """
    Tries to locate the pathname (file or folder) relative to the 
    starting_point. If pathname is already an absolute path, then pathname
    is returned. If pathname is not found relative to starting_point,
    then os.path.abspath(pathname) is returned.
    
    :param str pathname: The path to a file or folder, absolute or relative.
    :param str starting_point: Where to first look for relative pathname. 
        This can be a file or a folder; if a file, the search is relative 
        to the folder the file is in.
    :return: A string containing an absoluted path to pathname.
    """
    
    if starting_point is None or os.path.isabs(pathname):
        return pathname
    else:
        # in this case filename is a relative path
        if not os.path.exists(starting_point):
            raise ValueError('The starting_point "{}" does not exist.'.format(starting_point))
        
        # first get the directory of starting_point, so that we can check
        # if filename exists relative to this...
        if os.path.isdir(starting_point):
            starting_dir = os.path.abspath(starting_point)
        else:
            starting_dir = os.path.abspath(os.path.dirname(starting_point))
        
        # what the filename would be if it exists relative to starting_point
        filename_wouldbe = os.path.normpath(os.path.join(starting_dir, pathname))
        if os.path.exists(filename_wouldbe):
            # and if it exists, return it ...
            return filename_wouldbe
        else:
            # otherwise we are forced to assume it is relative to the 
            # current path, whatever that is
            if not os.path.exists(os.path.abspath(pathname)):
                raise ValueError('The file or folder "{}" was not found, even relative to "{}".'.format(pathname,starting_dir))
            return os.path.abspath(pathname)
        
    
def destcode_query(dest_code, rx=False, tx=False):
    """
    Takes a destination code and returns a dictionary specifying which 
    channels are and are not enabled. Since PRI codes are duplicated
    between RX and TX channels, you can use the rx and tx options to
    supress one or the other, or both or none.
    
    :params int dest_code: The destination code as would appear in the 
        Destination section of a PRI pattern file.
    :params bool rx: Whether or not to consider dest_code as an RX PRI code
    :params bool tx: Whether or not to consider dest_code as an TX PRI code
    :return: A `dict` specifying which channels the dest_code addresses
    """
    
    return {
        name: (dest_code & code) > 0 and 
        (((name in x6.TX_CHANNELS) and tx) or (not (name in x6.TX_CHANNELS) and rx))
        for name, code in x6.CHANNEL_PRI_CODES.iteritems()
    }
    
def validate_active_channels(active_channels):
    """
    Looks at an instance of active_channels and modifies it to something
    that will work if it's trying to do something the x6 can't handle, e.g.,
    three channel mode.
    
    :param list active_channels: A length four list of bools, specifying 
        which of the four digital-analog channels on the `~x6.X6` are
        to be active
    :return: Usually returns active_channels again, unless you input something
        the x6 won't like, in which case a warning message is issued and 
        the closest thing the x6 will like is returned.
    """
    
    if len(active_channels) != 4:
        raise ValueError('active_channels must be a length four list of bools.')
    
    active_channels = map(bool, active_channels)    
    
    four_active = [True, True, True, True]
   
    msg0 = 'Three channels found active -- switching to four channel mode.'
    msg1 = 'Two active channels found, both on the same DAC -- consider switching to DA0 and DA1 for a higher sample rate.'
    msg2 = 'That\'s an expensive digital delay generator you\'ve got there...'
    
    def print_msg(msg):
        print "Active Channel Message: " + msg
    
    # there is certainly a shorter way to do this, but this
    # way I am less likely to make a mistake with ORs and ANDs
    if   active_channels == [True,  True,  True,  True ]:
        return four_active
    elif active_channels == [True,  True,  True,  False]:
        print_msg(msg0)
        return four_active
    elif active_channels == [True,  True,  False, True ]:
        print_msg(msg0)
        return four_active
    elif active_channels == [True,  True,  False, False]:
        print_msg(msg1)
        return active_channels
    elif active_channels == [True,  False, True,  True ]:
        print_msg(msg0)
        return four_active
    elif active_channels == [True,  False, True,  False]:
        return active_channels
    elif active_channels == [True,  False, False, True ]:
        return active_channels
    elif active_channels == [True,  False, False, False]:
        return active_channels
    elif active_channels == [False, True,  True,  True ]:
        return active_channels
    elif active_channels == [False, True,  True,  False]:
        return active_channels
    elif active_channels == [False, True,  False, True ]:
        return active_channels
    elif active_channels == [False, True,  False, False]:
        return active_channels
    elif active_channels == [False, False, True,  True ]:
        print_msg(msg1)
        return active_channels
    elif active_channels == [False, False, True,  False]:
        return active_channels
    elif active_channels == [False, False, False, True ]:
        return active_channels
    elif active_channels == [False, False, False, False]:
        print_msg(msg2)
        return active_channels
    
def mat_to_rawbin(mat_fname, mat_var, bin_fname, rescale=False):
    """
    Given a MATLAB file and the name of a variable
    in that file, converts the contents of that variable
    to a raw binary file containing 16-bit integers,
    as expected by the various Malibu utilities.
    
    .. deprecated::
        Please use the `~x6.process_waveform.Waveform` class with
        `~x6.process_waveform.waveform_to_velo` instead.
    """
    mfile = sio.loadmat(mat_fname)
    arr = mfile[mat_var]
    
    if rescale:
        arr *= (2**15 - 1) / np.max(np.abs(arr))
        
    with open(bin_fname, 'wb') as f:
        arr.astype('<i2').tofile(f)

## CLASSES #####################################################################

class PRIPatternParser(cp.SafeConfigParser):
    """
    A class for parsing pattern files for the X6 PRI.
    """
    
    DESTINATION = 'Destination'
    DELAY = 'Delay'
    WIDTH = 'Width'
    ARRAY_SIZE = 'ArraySize'
    
    SECTIONS = [DESTINATION, DELAY, WIDTH]
    
    def __init__(self, filename=None):
        
        cp.SafeConfigParser.__init__(self)
        
        self._filename = filename
        
        if self._filename is not None:
            self.read(self._filename)
        else:            
            self._add_missing_sections()
            
    def _add_missing_sections(self):
        included_sections = [self.has_section(section) for section in self.SECTIONS]
        if not all(included_sections) and any(included_sections):
            warnings.warn('Only some of the required sections were found in the pattern file. This will likely result in indexing errors.')
        
        for section in self.SECTIONS:
            if not self.has_section(section):
                self.add_section(section)
                self.set(section, self.ARRAY_SIZE, '0')
           
    def set_destination(self, pulse_num, destination):
        if pulse_num >= self.get_array_size():
            raise ValueError('Your pulse_num is out of bounds; it cannot be greater than ArraySize-1={}'.format(self.get_array_size()-1))
            
        self.set(self.DESTINATION, 'P{}'.format(pulse_num), hex(destination))
        
    def set_delay(self, pulse_num, delay):
        if pulse_num >= self.get_array_size():
            raise ValueError('Your pulse_num is out of bounds; it cannot be greater than ArraySize-1={}'.format(self.get_array_size()-1))
            
        self.set(self.DELAY, 'P{}'.format(pulse_num), str(delay))
        
    def set_width(self, pulse_num, width):
        if pulse_num >= self.get_array_size():
            raise ValueError('Your pulse_num is out of bounds; it cannot be greater than ArraySize-1={}'.format(self.get_array_size()-1))
            
        self.set(self.WIDTH, 'P{}'.format(pulse_num), str(width))
        
    def set_pulse(self, pulse_num, destination, delay, width):
        self.set_destination(pulse_num, destination)
        self.set_delay(pulse_num, delay)
        self.set_width(pulse_num, width)
        
    def append_pulse(self, destination, delay, width):
        self.set_array_size(self.get_array_size() + 1)
        self.set_pulse(self.get_array_size()-1, destination, delay, width)
    
    def get_pulse(self, pulse_num):
        destination = self.get(self.DESTINATION, 'P{}'.format(pulse_num))
        delay = self.get(self.DELAY, 'P{}'.format(pulse_num))
        width = self.get(self.WIDTH, 'P{}'.format(pulse_num))
        
        return int(destination, 0), int(delay, 0), int(width, 0)
        
    def get_all_pulses(self):
        return [self.get_pulse(k) for k in range(self.get_array_size())]
            
    
    def get_array_size(self):
        array_sizes = [int(self.get(section, self.ARRAY_SIZE)) for section in self.SECTIONS]
        
        if len(set(array_sizes)) > 1:
            warnings.warn('The ArraySize in the Destination, Delay, and Width sections are not equal.')
            
        return array_sizes[0]
        
    def set_array_size(self, newval):
        for section in self.SECTIONS:
            self.set(section, self.ARRAY_SIZE, str(newval))
        
    def read(self, filename=None):
        if filename is None:
            if self._filename is None:
                raise ValueError('There is no file to read from.')
            else:
                cp.SafeConfigParser.read(self, self._filename)
        else:
            cp.SafeConfigParser.read(self, filename)
        self._add_missing_sections()
            
    def write(self, file=None):
        if file is None:
            if self._filename is None:
                raise ValueError('There is no file to write to.')
            else:
                filename = self._filename
                with open(self._filename, 'w') as f:
                    cp.SafeConfigParser.write(self, f)
        else:
            filename = file
            with open(file, 'w') as f:
                cp.SafeConfigParser.write(self, f)
        
        # if you don't get ride of the spaces, the x6 will silently fail
        strip_spaces_from_ini(filename)
                
    def cat(self):
        # use the write method just to be extra sure that we are seeing
        # exactly what will be in the file.
        output = StringIO.StringIO()
        self.write(output)
        output.seek(0)
        print output.read()
    
    def optionxform(self, option):
        return str(option)

class X6Settings(object):
    """
    A class for dealing with the settings file. We choose not to just 
    inherit from SafeConfigParser because it is an old-style class.
    """

    _FILENAME = find_on_path('x6/x6settings.ini') 
    
    _CTRL_CONSOLE = 'Control Console'
    _CTRL_CONSOLE_EDITOR = 'TextEditor'    
    
    _REQUIRED_SECTIONS = (_CTRL_CONSOLE,)
    
    def __init__(self):
        
        self._config = cp.SafeConfigParser()
        self.read()
            
    def _add_missing_sections(self):
        for section in self._REQUIRED_SECTIONS:
            if not self._config.has_section(section):
                self._config.add_section(section)
    
    # BEGIN CUSTOM SETTERS/GETTERS
       
    def control_console_get(self, variable):
        try:
            return self._config.get(self._CTRL_CONSOLE, variable)
        except cp.NoOptionError:
            None
            
    def control_console_set(self, variable, value=None):
        self._config.set(self._CTRL_CONSOLE, variable, value)
        
    @property 
    def control_console_file_editor(self): return self.control_console_get(self._CTRL_CONSOLE_EDITOR)

    # END CUSTOM SETTERS/GETTERS

    def read(self, filename=None):
        if filename is None:
            if not self._FILENAME is None:
                self._config.read(self._FILENAME)
        else:
            self._config.read(filename)
        self._add_missing_sections()
            
    def write(self, file=None):
        # *always* write to _FILENAME
        with open(self._FILENAME, 'w') as f:
            self._config.write(f)
            
    def cat(self):
        # use the write method just to be extra sure that we are seeing
        # exactly what will be in the file.
        output = StringIO.StringIO()
        self._config.write(output)
        output.seek(0)
        print output.read()
