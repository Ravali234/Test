#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# pulplot.py: Functions for visualizing pulses and pulse programs
##
# Author: Ian Hincks (ian.hincks@gmail.com)
##

## IMPORTS #####################################################################

import fnmatch
import os
import matplotlib.pyplot as plt
import numpy as np
import x6.process_waveform as pw
import ConfigParser as cp
from itertools import izip
from x6 import TX_CHANNELS, CHANNELS
from x6.utils import PRIPatternParser, destcode_query, search_for_file

## Classes #####################################################################


## Functions ###################################################################

def plot_lines(sample_rate, line_dict, title="Pulse Sequence"):
    """
    Plots a collection of signals on the same x axis.
    
    :params sample_rate: The sample rate; used to determine the spacing of 
        the x axis.
    :type sample_rate: Any kind of number, units of MHz.
    :params dict line_dict: A dictionary of the form {line_str0: line0, ...}
        where line_str0 is a string that will appear on the y axis, and 
        line0 is a 1D ndarray where each point is the value of the line at
        the given time, discretized by the sample rate.
    :params str title: A title to appear at the top of the plot.
    """
    
    # number of points in the longest line
    max_line_length = max([len(line_dict[line]) for line in line_dict])
    
    # determine the nicest unit to use
    dt = 1 / float(1e6 * sample_rate)
    T = dt * max_line_length
    if T < 1e-9:
        unit = 'ps'
        dt = dt / 1e-12
    elif T < 1e-6:
        unit = 'ns'
        dt = dt / 1e-9
    elif T < 1e-3:
        unit = 'us'
        dt = dt / 1e-6
    elif T < 1:
        unit = 'ms'
        dt = dt / 1e-3
    else:
        unit = 's'
        
    # plot 10% longer than the longest pulse
    plot_line_length = int(max_line_length * 1.1)
        
    # set the vector to put on the x axis
    ts = np.arange(0, dt * plot_line_length, dt)   
    
    # we will put one line in each subplot, with a shared x axis
    fig, axes = plt.subplots(nrows=len(line_dict), ncols=1, sharex=True, squeeze=False)
    plt.subplots_adjust(hspace=0.05)
    
    # since squeeze is False, axes is always a 2D list
    axes = [axis[0] for axis in axes]    

    # loop through and plot
    for axis, (name, function) in izip(axes, line_dict.iteritems()):
        axis.plot(ts, np.concatenate([function, np.zeros(plot_line_length - len(function))]), drawstyle='steps')
        axis.set_ylabel(name)
        total_range = abs(max(function) - min(function))
        if min(function) >= 0:
            axis.set_ylim([min(function) - total_range/10, max(function) + total_range/10])
        else:
            # if part of the function is negative, make the y limits symetric
            axis.set_ylim([-max(abs(function)) - total_range/10, max(abs(function)) + total_range/10])
    
    axes[0].set_title(title)
    axes[-1].set_xlabel('({})'.format(unit))
    
    return fig
    
def digital_to_line(dig_signal):
    """
    Takes a digital signal of the form 
    [[start0,length0],[start1,length1],[start2,length2],...] and returns
    an ndarray of 1s and 0s with 1s where the pulses are.
    """
    
    if len(dig_signal) > 0:
        line = np.zeros(max(map(sum,dig_signal))-1)
    
        for start, length in dig_signal:
            # remember that the digital signals are not zero indexed
            line[start-1:start-1+length] = 1
    else:
        line = np.empty(0)
        
    return line
    
def pri_pattern_to_lines(active_channels, rx_pattern=None, tx_pattern=None, tx_velofile=None, normalize=True):
    """
    For each channel in the given PRI patterns that does something, an
    `numpy.ndarray` is given which describes the state of that channel
    at each sample point.
    
    :param list active_channels: A length-four list of bools specifying 
        which of the four DA channels of the x6 will be active.
    :param  rx_pattern: A pattern to be interpretted as the RX line.
    :type rx_pattern: `str` or `~x6.pulprog.PRIPatternParser` or None
    :param  tx_pattern: A pattern to be interpretted as the RX line.
    :type tx_pattern: `str` or `~x6.pulprog.PRIPatternParser` or None
    :param tx_velofile: The filename of a velofile containing the tx analog
        output, e.g., as output by `~x6.process_waveform.waveform_to_velo`
    :type tx_velofile: `str` or None
    :param bool normalize: Whether or not to normalize the tx waveforms by 
        2^15-1
    """
    
    # get the waveform of each tx channel. Note that this might take up a
    # whole lot of memory.
    waveform_dict = pw.velo_to_waveform(active_channels, tx_velofile)
    
    # allow the patterns to be strings pointing to pattern files
    patterns = [rx_pattern, tx_pattern]
    if isinstance(rx_pattern, str) or isinstance(rx_pattern, unicode):
        patterns[0] = PRIPatternParser(rx_pattern)
    if isinstance(tx_pattern, str) or isinstance(tx_pattern, unicode):
        patterns[1] = PRIPatternParser(tx_pattern)
    
    # we will first parse the pattern files and figure out the delays
    # and widths (ie. "pulses") on each tx and rx channel
    line_pulses = {channel: [] for channel in CHANNELS}    
    for pattern, rx  in izip(patterns, [True, False]):
          
        if pattern is not None:
            
            for dest, delay, width in pattern.get_all_pulses():
                
                # get a dictionary that tells us which of the channels the
                # current pulse applies to
                pri_list = destcode_query(dest, rx=rx, tx=not(rx))
                
                for channel in CHANNELS:
                    if pri_list[channel]:
                        line_pulses[channel].append([delay, width])
    
    # next we loop through each channel and turn the pulses (if any) into
    # ndarrays with the data at each sample point
    line_dict = {}
    for channel, line_pulse in line_pulses.iteritems():
        if len(line_pulse) > 0:
            # first just make an array of ones and zeros
            line_dict[channel] = digital_to_line(line_pulse)
            if channel in waveform_dict and waveform_dict[channel] is not None:
                # we have an analog line, so get the value from the waveform
                # TODO: implement this more efficiently using np.nonzero
                for k in range(len(line_dict[channel])):
                    if line_dict[channel][k] == 1:
                        line_dict[channel][k] = waveform_dict[channel].get_chunk(1)
                
                if normalize:
                    line_dict[channel] = line_dict[channel] / (2**15 - 1)
                    
    # finally we take a look at active channels and get rid of any inactive
    # channels we might have
    for channel, active in izip(TX_CHANNELS, active_channels):
        if not active and channel in line_dict:
            del line_dict[channel]
    
    return line_dict
    
def plot_pri_pattern(sample_rate, active_channels, rx_pattern=None, tx_pattern=None, tx_velofile=None, normalize=True, title='Pulse Program'):
    """
    A plot is shown where each subplot plots a channel in the given PRI 
    patterns that does something. This function is simply a trivial 
    composition of the functions `~x6.pulplot.pri_pattern_to_lines` and 
    `~x6.pulplot.plot_lines`.
    
    :param list active_channels: A length-four list of bools specifying 
        which of the four DA channels of the x6 will be active.
    :params sample_rate: The sample rate; used to determine the spacing of 
        the x axis.
    :type sample_rate: Any kind of number, units of MHz.
    :param  rx_pattern: A pattern to be interpretted as the RX line.
    :type rx_pattern: `str` or `~x6.pulprog.PRIPatternParser` or None
    :param  tx_pattern: A pattern to be interpretted as the RX line.
    :type tx_pattern: `str` or `~x6.pulprog.PRIPatternParser` or None
    :param tx_velofile: The filename of a velofile containing the tx analog
        output, e.g., as output by `~x6.process_waveform.waveform_to_velo`
    :type tx_velofile: `str` or None
    :param bool normalize: Whether or not to normalize the tx waveforms by 
        2^15-1
    """
    
    plot_lines(
        sample_rate,
        pri_pattern_to_lines(
            active_channels,
            rx_pattern=rx_pattern, 
            tx_pattern=tx_pattern, 
            tx_velofile=tx_velofile, 
            normalize=normalize
        ),
        title=title
    )

def plot_configuration_file(configuration_file, pulse_name='Compiled Pulse'):
    """
    Given a configuration file (by convention, these files usually end
    in *.pulse) for an X6 experiment, plot the experiment they are setup 
    to do. Any paths specified within the file, if not already absolute,
    will be assumed to be relative to the folder containing the configuration
    file.
    
    :param str configuration file: The path to a configuration file.
    :param pulse_name: The section of the configuration file to look in.
    """    
    
    
    # get ready to parse the config file
    pulse_config = cp.ConfigParser()
    pulse_config.read(configuration_file)
    
    if not pulse_config.has_section(pulse_name):
        raise ValueError('No such pulse name "{}" found in the pulse file "{}".'.format(pulse_name, configuration_file))
    
    def get_absfile(option):
        return search_for_file(pulse_config.get(pulse_name, option), configuration_file)
    
    def get_bool(option):
        return bool(pulse_config.get(pulse_name, option))
    
    # retrieve necessary values from the config file
    rx_pattern, tx_pattern, tx_velofile = None, None, None
    if get_bool('rx_enable_pri'):
        rx_pattern = get_absfile('rx_pattern_file')
    if get_bool('tx_enable_pri'):
        tx_pattern = get_absfile('tx_pattern_file')
    if get_bool('tx_play_from_file_enable'):
        tx_velofile = get_absfile('tx_play_from_file_filename')

    sample_rate = float(pulse_config.get(pulse_name, 'sample_rate'))
    active_channels = pulse_config.get(pulse_name, 'tx_active_channels').split(',')
    active_channels = map(lambda x: x.strip() == 'True', active_channels)
    
    # do the plotting!
    plot_pri_pattern(sample_rate, active_channels, rx_pattern, tx_pattern, tx_velofile, title=pulse_name)  
   
def plot_compiled_folder(path, pulse_name='Compiled Pulse'):
    """
    Given a path to a folder, searches through this folder and calls
    `x6.pulplot.plot_configuration_file` on the first file it finds with
    a *.pulse suffix.
    
    :param str path: The path to a folder.
    :param pulse_name: The section of the configuration file to look in. 
    """   
    
    # first search through the derectory and choose the first file ending 
    # in "pulse"
    pulse_files = []
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, '*.pulse'):
            pulse_files.append(file)

    if len(pulse_files) > 0:
        configuration_file = os.path.abspath(os.path.join(path, pulse_files[0]))
    else:
        raise NameError('The specified folder does not contain a *.pulse file.')
        
    # now we have a function to do exactly what we want
    plot_configuration_file(configuration_file, pulse_name=pulse_name)

def plot_x6_experiment(x6_instance):
    """
    Takes the current configuration of an `~x6.X6` instance and plots the
    action of all channels, analog and digital, that do something.
    
    :param x6.X6 x6_instance: An instance of the `~x6.X6` class.
    """
    
    if x6_instance.rx_enable_pri:
        rx_pattern = x6_instance.rx_pattern_file
    else:
        rx_pattern = None
        
    if x6_instance.tx_enable_pri:
        tx_pattern = x6_instance.tx_pattern_file
    else:
        tx_pattern = None
    
    plot_pri_pattern(
        x6_instance.sample_rate,
        x6_instance.active_channels,
        rx_pattern=rx_pattern,
        tx_pattern=tx_pattern,
        tx_velofile=x6_instance.tx_play_from_file_filename,
        title='Experiment Visualization'
    )
