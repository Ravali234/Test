#!/usr/bin/python
##########################
##########################  Import Utility Python Modules
##########################
import sys
#sys.path.insert(0, r'C:\Users\fortheking\Documents\GitHub\hardware-drivers\python\src')
#sys.path.insert(0, r'C:\Users\mark.liang\My Documents\GitHub\gpibusb-comm_code\python\src\\')

import time
#from src import x6
import x6
import x6.process_waveform as pw
import x6.vita_convert as vc
#from x6.utils import PRIPatternParser

import generate_waveform as gw

#import instruments as ik
#import quantities as pq

import tempfile as tf

import numpy as np

import os
import glob
import warnings

import matplotlib.pyplot as plt
##########################
##########################
##########################

#Define file containing FPGA configurations
PULSE_FILE = 'standard_configurations.pulse'

#Define which configuration to use
PULSE_NAME = 'Single Pulse'

#Connect to Microwave Synthesizer for remote control (optional)
#pm = ik.instruments.other.PhaseMatrixFSW0020.open_serial('COM5', 115200)

##########################
##########################
##########################
def run_expt(pulse_amps,
            pulse_times,
            dead_time=500,
            rep_time_sec=1,
            phase_shift_degree=0,
            num_avgs=1,
            num_repetitions=1,
            do_plot=False
            ):

    # Define Acquisition Time and Receiver Delay for ADC
    acq_time = 2000
    receiver_delay = 0

    # Adjust dead_time by 15 ns to account for timing delays
    dead_time = 15 + dead_time

    # Loop over set of pulse times
    for idx in xrange(pulse_times.shape[0]):

        # Loop over set of pulse amplitudes
        for idy in xrange(pulse_amps.shape[0]):

            # Print out some information to screen
            print 'Pulse Amp = {}'.format(pulse_amps[idy])
            print 'Pulse Length = {}'.format(pulse_times[idx])

            # Generate transmitter and receiver patterns
            a = gen_transmitter_pattern(pulse_times[idx],dead_time)

            #gen_transmitter_pattern_nodigital(pulse_times[idx],dead_time)
            gen_receiver_pattern(receiver_delay,acq_time)

            # Generate pulse waveform
            gw.gen_velo_single_pulse(pulse_times[idx],0,phase_shift_degree,pulse_amps[idy],num_avgs)

            #gw.gen_velo_from_files('rand_data_1.mat', 'rand_data_1.mat', var_name='r')
            #gw.gen_velo_from_files('rand_data_1_10.mat', 'rand_data_1_10.mat', var_name='r')
            #gw.gen_velo_from_files('rand_data_1.mat', 'rand_data_1.mat', var_name='r', volt_units=True)

            # Run acquisition
            data = run_acq(num_repetitions,num_avgs,rep_time_sec)

            # Store and average collected data
            data = data - np.mean(data)

            data_part = np.array_split(data,num_avgs)
            data_averaged = np.sum(data_part,axis=0)/num_avgs


            # Save raw data
            dest_name_format = os.path.join(r'C:\Users\fortheking\Desktop\SinglePulseStandard_Mar31_2015_3', "repetition-{0:05}.npy")
            np.save(dest_name_format.format(pulse_amps.shape[0]*idx + idy), data_averaged)

            # Plot data
            if do_plot:
                plt.plot(np.mean(data_part,axis=0))

    return data_averaged, data_part, data

##########################
##########################
##########################

def gen_transmitter_pattern(pulse_length,dead_time):

    """
    #pattern = PRIPatternParser()
    #pattern.append_pulse(128, 60, pulse_length + 100)
    # ...
    #pattern.write('transmitter.pattern')
    """
    with open('transmitter.pattern', 'w') as f:

        f.write('[Destination]\n')
        f.write('ArraySize=4\n')
        f.write('P0=1\n')  #Modified 4/14/2016
        #f.write('P0=30\n')  # Oscilloscope Trigger DAC0_DIO1 (NOTE: only works if trigger all DAC digital outs)
        f.write('P1=64\n')  # Pulse Blanking DAC1_DIO0
        #f.write('P1=990\n') #FOR TESTING: Calls all digital lines
        f.write('P2=33\n')   # Pulse DAC0 + DAC1
        f.write('P3=512\n')  # Receiver Blanking for FID DAC1_DIO3
        f.write('\n')
        f.write('[Delay]\n')
        f.write('ArraySize=4\n')
        f.write('P0=0\n')
        ##f.write('P1=60\n') #changed by ML, June 5, 2015
        f.write('P1=0\n')
        ##f.write('P2=0\n') #changed by ML July 10, 2015
        f.write('P2=400\n')  #changed by ML, July 10, 2015
        ##f.write('P2={}\n'.format(314)) ## 400-86
        #f.write('P3={}\n'.format(pulse_length+dead_time+65)) #changed by ML, June 5, 2015
        ##f.write('P3={}\n'.format(112))  ##changed by ML, July 10, 2015
        f.write('P3={}\n'.format(400)) ## modified by ML, July 15, 2015
        ##f.write('P3={}\n'.format(420))
        f.write('\n')
        f.write('[Width]\n')
        f.write('ArraySize=4\n')
        f.write('P0=20000\n')
        f.write('P1={}\n'.format(pulse_length+1000))
        f.write('P2={}\n'.format(pulse_length))
        #f.write('P3={}\n'.format(5*dead_time)) #changed by ML, June 5, 2015
        ##f.write('P3={}\n'.format(pulse_length-30)) #changed by ML, July 10, 2015
        ##f.write('P3={}\n'.format(pulse_length-16))
        f.write('P3={}\n'.format(pulse_length))
        f.close()
        """
        f.write('[Destination]\n')
        f.write('ArraySize=4\n')
        f.write('P0=2\n')  #Modified 4/14/2016
        #f.write('P0=30\n')  # Oscilloscope Trigger DAC0_DIO1 (NOTE: only works if trigger all DAC digital outs)
        f.write('P1=70\n')  # Pulse Blanking DAC1_DIO0
        #f.write('P1=990\n') #FOR TESTING: Calls all digital lines
        f.write('P2=35\n')   # Pulse DAC0 + DAC1
        f.write('P3=550\n')  # Receiver Blanking for FID DAC1_DIO3
        f.write('\n')
        f.write('[Delay]\n')
        f.write('ArraySize=4\n')
        f.write('P0=1\n')
        ##f.write('P1=60\n') #changed by ML, June 5, 2015
        f.write('P1=1\n')
        ##f.write('P2=0\n') #changed by ML July 10, 2015
        f.write('P2=500\n')  #changed by ML, July 10, 2015
        ##f.write('P2={}\n'.format(314)) ## 400-86
        #f.write('P3={}\n'.format(pulse_length+dead_time+65)) #changed by ML, June 5, 2015
        ##f.write('P3={}\n'.format(112))  ##changed by ML, July 10, 2015
        f.write('P3={}\n'.format(400)) ## modified by ML, July 15, 2015
        ##f.write('P3={}\n'.format(420))
        f.write('\n')
        f.write('[Width]\n')
        f.write('ArraySize=5\n')
        f.write('P0=21000\n')
        f.write('P1={}\n'.format(pulse_length+1000))
        f.write('P2={}\n'.format(pulse_length))
        #f.write('P3={}\n'.format(5*dead_time)) #changed by ML, June 5, 2015
        ##f.write('P3={}\n'.format(pulse_length-30)) #changed by ML, July 10, 2015
        ##f.write('P3={}\n'.format(pulse_length-16))
        f.write('P3={}\n'.format(pulse_length))
        f.write('Hello from the inside transmitter\n')
        """
##########################
##########################
##########################
def gen_transmitter_pattern_nodigital(pulse_length,dead_time):

    """
    pattern = PRIPatternParser()
    pattern.append_pulse(128, 60, pulse_length + 100)
    # ...
    pattern.write('transmitter.pattern')
    """
    
    with open('transmitter.pattern', 'w') as f:

        f.write('[Destination]\n')
        f.write('ArraySize=1\n')
        f.write('P1=33\n')   # Pulse DAC0 + DAC1
        f.write('\n')
        f.write('[Delay]\n')
        f.write('ArraySize=1\n')
        f.write('P1=0\n')
        f.write('\n')
        f.write('[Width]\n')
        f.write('ArraySize=1\n')
        f.write('P1={}\n'.format(pulse_length))
        f.close()

##########################
##########################
##########################
def gen_receiver_pattern(delay,width):

    f = open('receiver.pattern', 'w')

    f.write('[Destination]\n')
    f.write('ArraySize=1\n')
    f.write('P0=1\n')     # Receiver Trigger ADC0
    f.write('\n')
    f.write('[Delay]\n')
    f.write('ArraySize=1\n')
    f.write('P0={}\n'.format(delay))
    f.write('\n')
    f.write('[Width]\n')
    f.write('ArraySize=1\n')
    f.write('P0={}\n'.format(width))
    f.write('Hello from the inside receiver\n')
    """
    f.write('[Destination]\n')
    f.write('ArraySize=1\n')
    f.write('P0=2\n')     # Receiver Trigger ADC0
    f.write('\n')
    f.write('[Delay]\n')
    f.write('ArraySize=2\n')
    f.write('P0={}\n'.format(delay))
    f.write('\n')
    f.write('[Width]\n')
    f.write('ArraySize=2\n')
    f.write('P0={}\n'.format(width))
    f.write('Hello from the inside receiver\n')
    """
    f.close()

##########################
##########################
##########################
def run_acq(n_repetitions=1,
        num_avgs=None,
        rep_time_sec=1
    ):
    # Create and configure the driver for the FPGA.
    x = x6.X6()
    x.open()
    x.load_configuration(PULSE_FILE, PULSE_NAME)
    print x.tx_active_channels

    # Set Number of Averages
    if num_avgs is not None:
        num_avgs = int(num_avgs)
        if num_avgs <= 0:
            raise ValueError("num_avgs must be a positive integer.")
        x.tx_count = num_avgs
        x.rx_count = num_avgs

    # Set Repetition Time
    x.tx_period = 1000000000*rep_time_sec
    x.rx_period = 1000000000*rep_time_sec

    # Preconfigure FPGA
    x.preconfigure()

    try:
        # Let it calibrate first.
        time.sleep(2)

        for idx in xrange(n_repetitions):
            print "Repetition idx.",idx
            print "Repetition {}...".format(idx),

            x.start_streaming()
            time.sleep(2 + num_avgs*rep_time_sec)
            x.stop_streaming()
            time.sleep(0.5)

            print "Streaming Stopped"

            data_streams = vc.parse_velo_stream('Data.bin')
            #print "data_streams=",data_streams
            raw_data = data_streams['0x100']


    finally:
        print "Closing..."
        x.close()
    #print  "raw_data=",raw_data
    return raw_data
