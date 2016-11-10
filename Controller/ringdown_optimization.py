#!/usr/bin/python

import sys
#sys.path.insert(0, r'C:\Users\fortheking\Documents\GitHub\hardware-drivers\python\src\\')
#sys.path.insert(0, r'C:\Users\fortheking\Documents\GitHub\gpibusb-comm_code\python\src\instruments\\')
#$sys.path.insert(0, r'C:\Users\fortheking\Documents\GitHub\InstrumentKit\python\src\\')

import time
import x6
import x6.process_waveform as pw
import x6.vita_convert as vc
#from x6.utils import PRIPatternParser

import generate_waveform as gw

import instruments as ik
import quantities as pq

import tempfile as tf

import numpy as np

import os
import glob
import warnings

import matplotlib.pyplot as plt

PULSE_FILE = 'ringdown_optimization.pulse'
PULSE_NAME = 'Single Pulse'

pm = ik.instruments.other.PhaseMatrixFSW0020.open_serial('COM5', 115200)
#gm = ik.instruments.lakeshore.Lakeshore475.open_gpibusb('COM8',12)


def run_ringdown_optimization(pulse_time,
                            pulse_time_append,
                            comp_times,
                            comp_amps,
                            freqs,
                            num_avgs,
            ):

    with_amp = True
    seq_length = comp_times.size*comp_amps.size
    sleep_time = 10+seq_length*num_avgs*0.1
    num_repetitions = 1
    dead_time = 15 + 20
    minima_labels = np.zeros((freqs.shape[0],5))

    pm = ik.instruments.other.PhaseMatrixFSW0020.open_serial('COM5', 115200)
    pm.rf_output = True

    for idx in xrange(freqs.size):
        print 'Running Frequency {} MHz'.format(freqs[idx])

        pm.freq = freqs[idx] * pq.MHz

        gen_transmitter_pattern(pulse_time+pulse_time_append, dead_time)
        gen_receiver_pattern(0,10000)
        gw.gen_velo_ringdown_optimization(pulse_time,pulse_time_append,0,comp_times,comp_amps,num_avgs)
        data = run_experiment(num_repetitions,sleep_time,seq_length*num_avgs)

        # Process data
        #data_part = np.array_split(data[:num_avgs * 10000],num_avgs)
        data_part = np.array_split(data,num_avgs)
        data_averaged = np.mean(data_part,axis=0)
        data_averaged_split = np.array_split(data_averaged,seq_length)

        # Save raw data
        dest_name_format = os.path.join(r'C:\Users\fpga\Desktop\spin_echo\rabi_experiment', "repetition-{0:05}.npy")
        np.save(dest_name_format.format(idx), data_averaged_split)

        ringdown = np.zeros((seq_length,))
        ringdown_labels = np.zeros((seq_length,2))
        varct = 0

        for idy in xrange(comp_times.shape[0]):
            for idz in xrange(comp_amps.shape[0]):
                #delay_prepulse = 200     # With JEOL or Varian Cavity DirCoupler
                #delay_unknown = 18
                #delay_postpulse = 30
                #integration_time = 500
                delay_prepulse = 208     # With SC Resonator Port 2
                delay_unknown = 0
                delay_postpulse = 0
                integration_time = 200
                start_index = delay_prepulse + delay_unknown + pulse_time + comp_times[idy] + delay_postpulse
                end_index = start_index + integration_time

                if with_amp:
                    start_index = 450
                    end_index = 700

                new_data_averaged = np.abs(data_averaged_split[varct]-np.mean(data_averaged_split[varct][start_index:end_index]))

                ringdown[varct] = np.sum(new_data_averaged[start_index:end_index])

                ringdown_labels[varct,0] = comp_times[idy]
                ringdown_labels[varct,1] = comp_amps[idz]

                varct = varct + 1

        min_pt = np.argmin(ringdown)

        minima_labels[idx,0] = freqs[idx]
        minima_labels[idx,1] = min_pt
        minima_labels[idx,2] = ringdown_labels[min_pt,0]
        minima_labels[idx,3] = ringdown_labels[min_pt,1]
        minima_labels[idx,4] = ringdown[min_pt]

        #ringdown = ringdown_temp.reshape(comp_times.shape[0], comp_amps.shape[0])

    pm.rf_output = False

    return data_averaged_split, ringdown, minima_labels

def gen_transmitter_pattern(pulse_length,dead_time):

    """
    pattern = PRIPatternParser()
    pattern.append_pulse(128, 60, pulse_length + 100)
    # ...
    pattern.write('transmitter.pattern')
    """

    with open('transmitter.pattern', 'w') as f:

        f.write('[Destination]\n')
        f.write('ArraySize=4\n')
        f.write('P0=30\n')  # Oscilloscope Trigger DAC0_DIO1 (NOTE: only works if trigger all DAC digital outs)
        f.write('P1=128\n')  # Pulse 1 Blanking DAC1_DIO1
        f.write('P2=33\n')   # Pulse 1 DAC0 + DAC1
        f.write('P3=512\n')  # Receiver Blanking DAC1_DIO3
        f.write('\n')
        f.write('[Delay]\n')
        f.write('ArraySize=4\n')
        f.write('P0=0\n')
        f.write('P1=60\n')
        f.write('P2=0\n')
        #f.write('P3=60\n')
        f.write('P3={}\n'.format(pulse_length+60+65+dead_time))
        f.write('\n')
        f.write('[Width]\n')
        f.write('ArraySize=4\n')
        f.write('P0=20\n')
        f.write('P1={}\n'.format(pulse_length+65))
        f.write('P2={}\n'.format(pulse_length))
        f.write('P3=2000\n')

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

    f.close()

def run_experiment(n_repetitions=1,
                  how_long_to_sleep=2.5,
                  num_avgs=None
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

    # Preconfigure FPGA
    x.preconfigure()

    try:
        # Let it calibrate first.
        time.sleep(2)

        for idx in xrange(n_repetitions):

            print "Repetition {}...".format(idx),

            x.start_streaming()
            time.sleep(how_long_to_sleep)
            x.stop_streaming()
            time.sleep(0.5)

            print "Streaming Stopped"

            data_streams = vc.parse_velo_stream('Data.bin')
            raw_data = data_streams['0x100']

        print "Closing..."
        x.close()

    finally:
        pass

    return raw_data
