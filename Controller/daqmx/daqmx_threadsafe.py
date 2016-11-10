#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# daqmx_threadsafe.py: Replacement for PyDAQmx with
#      threadsafe wrappers for DAQmx calls and classes.
##
# Part of the Corylab Hardware Drivers project.
##

## ALL ########################################################################

__all__ = [
    ## ENUMS ##
    'PauseTriggerType',
    'Edge',
    'SampleMode',
    'DigitalLevel',
    'SampleTimingType',
    'CountDirection',
    'Units',
    ## CLASSES ##
    'Task',
    ## UNITS ##
    'samples'
]

## InstrumentKit Imports ##
from instruments.util_fns import assume_units

## Hardware Support Imports ##
try:
    import PyDAQmx as daq
except ImportError:
    daq = None
    # Log the error and propagate it upwards.
    import logging
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())
    logger.error('Could not import PyDAQmx; NI-DAQ functionality will not work.')
    raise

## Other Libraries ##
import quantities as pq
from flufl.enum import IntEnum
import ctypes as C
import numpy as np

## Standard Library Imports ##
import threading
import functools
import logging

## GLOBALS ####################################################################

# We use a reenterant lock so that if we accidently lock twice from within
# the same thread, nothing goes wrong. We only really care that DAQmx is always
# called from one thread at a time.
__daqmx_lock = threading.RLock()

# Make or get a logger instance that we'll use for debugging.
__logger = logging.getLogger(__name__)
__logger.addHandler(logging.NullHandler())

## UNITS ######################################################################

samples = pq.UnitQuantity('sample', 1.0 * pq.dimensionless, 'sample')

## ENUMS ######################################################################

class PauseTriggerType(IntEnum):
    """
    Allowed values for the Pause Trigger Type attribute of a DAQmx Task.
    Documentation on the meaning of each value can be found in the
    `C API Reference`_.
    
    .. _C API Reference: http://zone.ni.com/reference/en-XX/help/370471Y-01/mxcprop/attr1366/
    """
    analog_level = daq.DAQmx_Val_AnlgLvl
    analog_window = daq.DAQmx_Val_AnlgWin
    digital_level = daq.DAQmx_Val_DigLvl
    digital_pattern = daq.DAQmx_Val_DigPattern
    none = daq.DAQmx_Val_None
    
class Edge(IntEnum):
    """
    Allowed values for properties that correspond to kinds of edges.
    """
    rising = daq.DAQmx_Val_Rising
    falling = daq.DAQmx_Val_Falling

class DigitalLevel(IntEnum):
    """
    Allowed values for properties that can take on one of two digital levels,
    high and low.
    """
    low = daq.DAQmx_Val_Low
    high = daq.DAQmx_Val_High
    
class SampleMode(IntEnum):
    """
    Allowed values for types of sample clock timings, as listed in the
    `C API Reference`_.

    .. _C API Reference: http://zone.ni.com/reference/en-XX/help/370471Y-01/daqmxcfunc/daqmxcfgsampclktiming/
    """
    finite_samples = daq.DAQmx_Val_FiniteSamps
    continuous_samples = daq.DAQmx_Val_ContSamps
    hw_timed_single_point = daq.DAQmx_Val_HWTimedSinglePoint

class SampleTimingType(IntEnum):
    """
    Allowed values for the sample timing type attribute of a DAQmx Task.
    Documentation on the meaning of each value can be found in the
    `C API Reference`_.
    
    .. _C API Reference: http://zone.ni.com/reference/en-XX/help/370471Y-01/mxcprop/attr1347/
    """
    sample_clock = daq.DAQmx_Val_SampClk
    burst_handshake = daq.DAQmx_Val_BurstHandshake
    handshake = daq.DAQmx_Val_Handshake
    implicit = daq.DAQmx_Val_Implicit
    on_demand = daq.DAQmx_Val_OnDemand
    change_detection = daq.DAQmx_Val_ChangeDetection
    pipelined_sample_clock = daq.DAQmx_Val_PipelinedSampClk
    
class Units(IntEnum):
    seconds = daq.DAQmx_Val_Seconds
    ticks = daq.DAQmx_Val_Ticks
    custom_scale = daq.DAQmx_Val_FromCustomScale
    volts = daq.DAQmx_Val_Volts

class CountDirection(IntEnum):
    up = daq.DAQmx_Val_CountUp
    down = daq.DAQmx_Val_CountDown
    
class DataLayout(IntEnum):
    group_by_channel = daq.DAQmx_Val_GroupByChannel
    group_by_scan_number = daq.DAQmx_Val_GroupByScanNumber

## DECORATORS ##################################################################

def locks_daq(fn):
    """
    Causes the decorated function or method to lock the DAQmx library when
    called and release that lock upon returning or an exception.
    """
    @functools.wraps(fn)
    def locking_fn(*args, **kwargs):
        global __daqmx_lock
        with __daqmx_lock:
            return fn(*args, **kwargs)
    return locking_fn

def log_calls(fn):
    """
    Causes all calls to the decorated function to be logged.
    """
    name = getattr(fn, '__name__', '<unnamed>')
    @functools.wraps(fn)
    def logging_fn(*args, **kwargs):
        global __logger
        __logger.debug("{name}({args}, {kwargs})".format(
            name=name,
            args=", ".join(map(repr, args)),
            kwargs=", ".join("{}={}".format(key, val) for key, val in kwargs.iteritems())
        ))
        return fn(*args, **kwargs)
    return logging_fn

## FUNCTIONS ###################################################################

def rescale_with_default(quantity, units):
	quantity = assume_units(quantity, units)
	return quantity.rescale(units).magnitude

## CLASSES #####################################################################

class Task(object):
    """
    Used to add some nice logic to `PyDAQmx.Task` for when we are frustrated
    by the limitations of that class. In particular, all calls to PyDAQmx from
    this class lock the DAQmx library such that this class is threadsafe.
    """
    @log_calls
    def __init__(self):
        self._task = daq.Task()
        
    ## TASK METADATA ##

    @property
    @locks_daq
    def name(self):
        if hasattr(self, '_task'):
            buf = C.create_string_buffer(100)
            self._task.GetTaskAttribute(daq.DAQmx_Task_Name, buf)
            return buf.value
        else:
            return None
        
    def __repr__(self):
        return "<Task object at {} with name {}>".format(id(self), self.name)
    
    ## TASK STATE PROPERTIES AND METHODS ##
    @locks_daq
    @log_calls
    def wait_until_done(self,timeout=pq.Quantity(1, "s")):
        # TODO: catch for timeout error.
        self._task.WaitUntilTaskDone(assume_units(timeout, 's').rescale('s').magnitude)
    
    @property
    @locks_daq
    def is_done(self):
        ret_val = C.c_uint32(0)

        self._task.IsTaskDone(C.byref(ret_val))
        return bool(ret_val.value)

    @locks_daq
    @log_calls
    def start(self):
        self._task.StartTask()
    @locks_daq
    @log_calls
    def stop(self):
        self._task.StopTask()
    @locks_daq
    @log_calls
    def clear(self):
        self._task.ClearTask()

    # We implement the context manager protocol by aliasing __enter__
    # and __exit__ to start and stop, respectively.
    __enter__ = start
    __exit__ = stop
    
    ## READ PROPERTIES AND METHODS ##
    # These properties implement reading of scalar and buffer values from the
    # task.
    
    @property
    @locks_daq    
    def counter_value(self):
        """
        Returns the current value of the counter scalar associated with this 
        task.
        
        .. seealso::
            PyDAQmx.Task.ReadCounterScalarU32
        """
        counter_val = C.c_uint32(0)
        self._task.ReadCounterScalarU32(1.0, C.byref(counter_val), None)
        return pq.Quantity(counter_val.value,'counts')
        
    @property
    @locks_daq
    @log_calls
    def n_samples_available_per_chan(self):
        ret_val = C.c_uint32(0)
        self._task.GetReadAvailSampPerChan(C.byref(ret_val))
        return ret_val.value
        
    @locks_daq
    @log_calls
    def read_counter_buffer(self, n_samples):
        # FIXME: assumes single channel reads!
        buf = np.zeros((n_samples), 'uint32')
        buf_len = C.c_int32(n_samples)
        n_read = C.c_int32(0)
        self._task.ReadCounterU32(
            buf_len,
            daq.DAQmx_Val_WaitInfinitely,
            buf,
            C.c_uint32(n_samples),
            C.byref(n_read),
            None
        )
        
        # TODO: check the number of samples read!
        
        return buf
        
    ## WRITE PROPERTIES AND METHODS ##
    
    @locks_daq
    @log_calls
    def write_analog(self,
            samples,
            auto_start=False,
            timeout=None # Here, True means to try once.
    ):
        # TODO: docstring
        # FIXME: implement units for the samples.
        # Note that we assume that samples is
        # either an (n_samples,) array or (n_channels, n_samples) array.
        # In either case, n_samples is the -1th element of the shape.
        n_samples = samples.shape[-1]
        n_channels = 1 if len(samples.shape) == 1 else samples.shape[0]
        # Make a new buffer that is C-ordered and has the exact shape
        # we expect by using reshape.
        samples_buffer = samples.reshape((n_channels, n_samples), order='C')
        samples_buffer = np.require(samples_buffer, 'float64', 'C')
        
        # Make the timeout either WaitInfinitely, or a number of seconds.
        if timeout is None:
            c_timeout = daq.DAQmx_Val_WaitInfinitely
        # This is very unusual, but we want to be sure to catch ONLY the literal
        # singleton True, since 1.0 == True means we could think we want to use
        # the try-once timeout if we wait exactly one second.
        elif timeout is True:
            c_timeout = C.c_double(0.0)
        else:
            c_timeout = C.c_double(rescale_with_default(timeout, pq.second))
        
        # Now that we have the buffer we expect, go on and call the DAQmx
        # method.
        ret_val = C.c_int32(0)
        self._task.WriteAnalogF64(
            n_samples,
            C.c_ulong(auto_start),
            c_timeout,
            DataLayout.group_by_channel,
            samples_buffer,
            C.byref(ret_val),
            None # Reserved for future use in the DAQmx API.
        )
        return ret_val.value
        
    ## SAMPLE TIMING PROPERTIES ##
        
    @property
    @locks_daq
    def sample_timing_type(self):
        ret_val = C.c_int32(0)
        self._task.GetSampTimingType(C.byref(ret_val))
        return SampleTimingType(ret_val.value)
    @sample_timing_type.setter
    @locks_daq
    @log_calls
    def sample_timing_type(self, newval):
        self._task.SetSampTimingType(newval)
        
    ## TRIGGER PROPERTIES ##
    
    @property
    @locks_daq
    def diglvl_pause_trigger_src(self):
        """
        Returns the current source for the digital level pause trigger.
        """
        # TODO: TEST!
        buf = C.create_string_buffer(100)
        self._task.GetTrigAttribute(daq.DAQmx_DigLvl_PauseTrig_Src, buf)
        return buf.value
    @diglvl_pause_trigger_src.setter
    @locks_daq
    @log_calls
    def diglvl_pause_trigger_src(self, newval):
        # TODO: TEST!
        self._task.SetDigLvlPauseTrigSrc(newval)
        
    @property
    @locks_daq
    def pause_trigger_type(self):
        """
        Gets/sets the type of pause trigger for this task, or
        `PauseTriggerType.none` if no pause trigger currently exists.
        """
        ret_val = C.c_int32(0)
        self._task.GetPauseTrigType(C.byref(ret_val))
        return PauseTriggerType(ret_val.value)
    @pause_trigger_type.setter
    @locks_daq
    @log_calls
    def pause_trigger_type(self, newval):
        self._task.SetPauseTrigType(C.c_int32(newval))
        
    @property
    @locks_daq
    def diglvl_pause_trigger_when(self):
        ret_val = C.c_int32(0)
        self._task.GetDigLvlpause_triggerWhen(C.byref(ret_val))
        return DigitalLevel(ret_val.value)
    @diglvl_pause_trigger_when.setter
    @locks_daq
    @log_calls
    def diglvl_pause_trigger_when(self, newval):
        self._task.SetDigLvlPauseTrigWhen(C.c_int32(newval))

    @property
    @locks_daq
    def start_retriggerable(self):
        ret_val = C.c_int32(0)
        self._task.GetStartTrigRetriggerable(C.byref(ret_val))
        return bool(ret_val.value)
    @start_retriggerable.setter
    @locks_daq
    @log_calls
    def start_retriggerable(self, newval):
        self._task.SetStartTrigRetriggerable(C.c_int32(1 if newval else 0))

    ## CHANNEL LIST PROPERTIES ##

    @property
    @locks_daq
    def channels(self):
        n_channels = C.c_uint32(0)
        self._task.GetTaskAttribute(daq.DAQmx_Task_NumChans, C.byref(n_channels))

        chan_names = [C.create_string_buffer(100) for idx in xrange(n_channels.value)]
        for idx, chan_buf in enumerate(chan_names):
            self._task.GetNthTaskChannel(1 + idx, chan_buf, 100)

        return [chan_buf.value for chan_buf in chan_names]

    ## CHANNEL CREATION FUNCTIONS ##

    @locks_daq
    @log_calls
    def create_co_pulse_channel_time(self,
            counter,
            name,
            idle_state,
            initital_delay,
            low_time, high_time
    ):
        initital_delay = rescale_with_default(initital_delay, 's')
        low_time = rescale_with_default(low_time, 's')
        high_time = rescale_with_default(high_time, 's')
        self._task.CreateCOPulseChanTime(
                counter,
                name,
                Units.seconds,
                C.c_int32(idle_state),
                initital_delay,
                low_time, high_time
        )

    @locks_daq
    @log_calls
    def create_ci_count_edges_chan(self,
            counter,
            name,
            edge,
            initial_count,
            count_direction
    ):
        self._task.CreateCICountEdgesChan(
            counter, name,
            C.c_int32(edge),
            rescale_with_default(initial_count, pq.counts),
            C.c_int32(count_direction)
        )

    @locks_daq
    @log_calls
    def create_ci_pulse_width_chan(self,
        counter, name,
        min_counts=0, max_counts=10,
        units=Units.ticks,
        edge=Edge.rising
    ):
        self._task.CreateCIPulseWidthChan(
            counter, name,
            C.c_double(rescale_with_default(min_counts, pq.counts)),
            C.c_double(rescale_with_default(max_counts, pq.counts)),
            C.c_int32(units),
            C.c_int32(edge),
            None
        )
        
    @locks_daq
    @log_calls
    def create_ao_voltage_chan(self,
        physical_name,
        channel_name=None,
        min_val=pq.Quantity(0, 'V'),
        max_val=pq.Quantity(5, 'V')
    ):
        r"""
        Creates a channel to generate voltage and adds it to this task.
        
        :param str physical_name: Name of the physical channel or a range of
            physical channels on which to output an analog voltage.
        :param str channel_name: Name to assign to the channel. Note that if
            this is not `None`, then the given name must be used to refer to
            this channel in the future.
        :param min_val: Minimum voltage that is expected to be generated.
        :type min_val: `pq.Quantity` or `float`
        :units min_val: As specified, or :math:`\text{V}` if not specified.
        :param max_val: Maximum voltage that is expected to be generated.
        :type max_val: `pq.Quantity` or `float`
        :units max_val: As specified, or :math:`\text{V}` if not specified.
        """
        # FIXME: DAQmx_Val_FromCustomScale is not supported!
        self._task.CreateAOVoltageChan(
            physical_name, channel_name,
            C.c_double(rescale_with_default(min_val, pq.volt)),
            C.c_double(rescale_with_default(max_val, pq.volt)),
            Units.volts,
            None
        )
        

    ## TIMING FUNCTIONS ##

    @locks_daq
    @log_calls
    def config_sample_clock_timing(self,
            source, rate, active_edge, sample_mode,
            samples_per_chan
    ):
        self._task.CfgSampClkTiming(
            source,
            assume_units(rate, 1/pq.s).rescale(samples / pq.s).magnitude,
            C.c_int32(active_edge),
            C.c_int32(sample_mode),
            C.c_uint64(samples_per_chan)
        )
        
    @locks_daq
    @log_calls
    def config_implicit_timing(self,
            sample_mode,
            samples_per_chan
    ):
        self._task.CfgImplicitTiming(
            C.c_int32(sample_mode),
            C.c_uint64(samples_per_chan)
        )
        
    ## COUNTER CONFIGURATION ##
    # TODO: make a new Channel object of which these are properties.
    
    @locks_daq
    @log_calls
    def set_ci_pulse_width_terminal(self,
            chan_name,
            terminal_name
    ):
        self._task.SetCIPulseWidthTerm(chan_name, terminal_name)
        
    @locks_daq
    @log_calls
    def set_ci_count_edges_terminal(self,
            chan_name,
            terminal_name
    ):
        self._task.SetCICountEdgesTerm(chan_name, terminal_name)
    
    @locks_daq
    @log_calls
    def set_ci_counter_timebase_src(self,
            chan_name,
            timebase_src
    ):
        self._task.SetCICtrTimebaseSrc(chan_name, timebase_src)
        
    @locks_daq
    @log_calls
    def set_ci_duplicate_count_prevention(self,
            chan_name,
            prevent
    ):
        self._task.SetCIDupCountPrevent(
            chan_name,
            C.c_ulong(prevent)
        )
        
    
