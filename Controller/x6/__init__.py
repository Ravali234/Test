#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# __init__.py: Abstracts access to the X6-1000M board with custom logic.
##
# Author: Christopher Granade (cgranade@cgranade.com).
##
# NOTE:
#     Requires the WaterlooAppDll.dll provided by II to be visible on
#     %PATH%.
##

## FEATURES ###################################################################

from __future__ import division

## IMPORTS ####################################################################

import os
import sys
import warnings
import logging

import x6.utils as utils
from x6._enums import *
from x6.waterlooapp_dll import *

import ConfigParser as cp

from ctypes import *
from functools import wraps

from flufl.enum import Enum, IntEnum

## LOGGING SETUP ##############################################################

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

dll_log = logging.getLogger(__name__ + ".WaterlooAppDll")
dll_log.addHandler(logging.NullHandler())

def log_callback(debug_str):
    # The whole point of this function is to remove the "self" argument
    # that would be there if we just wrapped dll_log.debug.
    dll_log.debug(debug_str)



## CONSTANTS ##################################################################

## DEPRECATED CONSTANTS ##
# The following constants are deprecated, and should be replaced with the
# Enums in _enums.py.

# Clock Sources
#: Selects the clock source to be the X6-1000M's internal oscillator.
CLK_INTERNAL    = 1
#: Selects the clock source to be the external clock indicated
#: by `~x6.X6.ext_clock_src_selection`.
CLK_EXTERNAL    = 0

# Clock Selection
#: Indicates that the external clock is connected via the front panel.
CLK_FRONT_PANEL = 0
#: Indicates that the external clock is connected via the P16 connector
#: on the rear of the X6-1000M's housing.
CLK_P16         = 1

# RX PRI codes
ADC0      = 0x001
ADC0_DIO0 = 0x002
ADC0_DIO1 = 0x004
ADC0_DIO2 = 0x008
ADC0_DIO3 = 0x010
ADC1      = 0x020
ADC1_DIO0 = 0x040
ADC1_DIO1 = 0x080
ADC1_DIO2 = 0x100
ADC1_DIO3 = 0x200

# TX PRI codes
DAC0      = 0x001
DAC0_DIO0 = 0x002
DAC0_DIO1 = 0x004
DAC0_DIO2 = 0x008
DAC0_DIO3 = 0x010
DAC1      = 0x020
DAC1_DIO0 = 0x040
DAC1_DIO1 = 0x080
DAC1_DIO2 = 0x100
DAC1_DIO3 = 0x200

## END DEPRECATED CONSTANTS ##

#: Maximum sample rate for the single channel per DAC
#: mode of operation.
#:
#: :units: samples / :math:`\mu \text{s}`
FULL_SAMPLE_RATE = 1000
#: Maximum sample rate for the two channel per DAC
#: mode of operation.
#:
#: :units: samples / :math:`\mu \text{s}`
HALF_SAMPLE_RATE = 500

RX_CHANNELS = [
    "AD0", "AD1", "AD2", "AD3",
    
    'ADC0_DIO0',
    'ADC0_DIO1',
    'ADC0_DIO2',
    'ADC0_DIO3',
    'ADC1_DIO0',
    'ADC1_DIO1',
    'ADC1_DIO2',
    'ADC1_DIO3'
]

TX_CHANNELS = [
    "DA0", "DA1", "DA2", "DA3",
    
    'DAC0_DIO0',
    'DAC0_DIO1',
    'DAC0_DIO2',
    'DAC0_DIO3',
    'DAC1_DIO0',
    'DAC1_DIO1',
    'DAC1_DIO2',
    'DAC1_DIO3'
]

#: Names of the various analog and digital I/O
#: channels exposed by the UWaterloo custom logic.
#: These names may be used to specify channels in
#: **xpulprog** programs.
CHANNELS = RX_CHANNELS + TX_CHANNELS

CHANNEL_PRI_CODES = {
    
    # Note that some pins share a PRI code; this must be resolved in waveform
    # generation.
    'DA0': DAC0,
    'DA1': DAC0,
    'DA2': DAC1,
    'DA3': DAC1,
    
    'AD0': ADC0,
    'AD1': ADC0,
    'AD2': ADC1,
    'AD3': ADC1,
    
    'ADC0_DIO0': ADC0_DIO0,
    'ADC0_DIO1': ADC0_DIO1,
    'ADC0_DIO2': ADC0_DIO2,
    'ADC0_DIO3': ADC0_DIO3,
    'ADC1_DIO0': ADC1_DIO0,
    'ADC1_DIO1': ADC1_DIO1,
    'ADC1_DIO2': ADC1_DIO2,
    'ADC1_DIO3': ADC1_DIO3,
    
    'DAC0_DIO0': DAC0_DIO0,
    'DAC0_DIO1': DAC0_DIO1,
    'DAC0_DIO2': DAC0_DIO2,
    'DAC0_DIO3': DAC0_DIO3,
    'DAC1_DIO0': DAC1_DIO0,
    'DAC1_DIO1': DAC1_DIO1,
    'DAC1_DIO2': DAC1_DIO2,
    'DAC1_DIO3': DAC1_DIO3
    
}


## FUNCTIONS ##################################################################

def _expose_setting(settings_name, attr_name, attr_type=int, doc=None):
    """
    Should return a property like the following:
    
    @property
    @_require_open_board
    def ext_clock_src_selection(self):
        return int(self.__settings_common.ext_clock_src_selection)
    @ext_clock_src_selection.setter
    @_require_open_board
    def ext_clock_src_selection(self, newval):
        self.__settings_common.ext_clock_src_selection = int(newval)
    """

    extra_args = {} if doc is None else {"doc": doc}
        
    # Add some extra logic for IntEnum types, so that we can take a string
    # containing the int, or the name of the constant, either one.
    # This is needed for use with config files...
    if hasattr(attr_type, '__bases__') and IntEnum in attr_type.__bases__:
        orig_attr_type = attr_type
        def attr_type(newval):
            try:
                newval = int(newval)
            except ValueError:
                pass
            return orig_attr_type(newval)

    @_require_open_board
    def getter(self):
        settings = getattr(self, "_{}__settings_{}".format(type(self).__name__, settings_name))
        return attr_type(getattr(settings, attr_name))

    @_require_open_board
    def setter(self, newval):
        settings = getattr(self, "_{}__settings_{}".format(type(self).__name__, settings_name))
        setattr(settings, attr_name, attr_type(newval))

    return property(fget=getter, fset=setter, **extra_args)

def _require_open_board(fn):
    @wraps(fn)
    def validated_fn(self, *args, **kwargs):
        if not self._is_open:
            raise IOError("Board must be open.")
        return fn(self, *args, **kwargs)
    
    return validated_fn

def _nonnegative(type_fn):
    def validator(value):
        value = type_fn(value)
        if value < 0:
            raise TypeError("Value cannot be negative.")
        else:
            return value
            
    return validator
   
## MAIN CLASS #################################################################

class X6(object):
    """
    Abstracts access to an X6-1000M board loaded with the WaterlooApp
    logic and accessed via the WaterlooApp.dll shared library provided
    by II. For more information on the functionality exposed by this
    class, please see ``UofWaterlooPRI_SW_Notes.pdf``, as provided in
    the ``Waterloo_Dll.zip`` deliverable from II.

    All Windows structured exceptions and DLL integer return codes are
    checked for errors, and are converted into `RuntimeError` exceptions.
    Additionally, an `IOError` is raised if a method is called when the
    board is in the wrong state for that method.

    Note that if raw access to the underlying DLL is ever required,
    this can be obtained as the ``_dll`` attribute of an instance of
    this class.
    """

    ## SPECIAL METHODS ##
    
    def __init__(self):
        # Allow exceptions here to propagate
        # out.
        self._dll = WaterlooAppDll()

        # Call the init function in the DLL and catch exceptions.
        try:
            res = self._dll.WaterlooApp_Init()
        except WindowsError as ex:
            raise RuntimeError("Windows exception raised during Init: " + str(ex))
            
        # If logging is supported, register a callback to forward logs
        # to Python's logging engine.
        if self._dll.version >= 1:
            try:
                self._log_callback_ptr = self._dll.log_callback_t(log_callback)
                self._dll.WaterlooApp_RegisterLogCallback(self._log_callback_ptr)
            except WindowsError as ex:
                # Log the error and continue.
                log.error("Error occured setting up logger for DLL: " + str(ex))

        self._is_open = False
        self._is_streaming = False

    def __del__(self):
        try:
            self.close()
        finally:
            try:
                # Silently fail during deletion only.
                self._dll.WaterlooApp_Cleanup()
            except:
                sys.stderr.write('WARNING: FPGA driver did not clean up properly. This is a bad sign.')
                pass # Silently fail during deletion.

    ## PRIVATE METHODS ##
            
    def __init_settings(self):
        self.__settings_common     = WA_CommonSettings()
        self.__settings_rx_trigger = WA_IoTriggerSettings()
        self.__settings_tx_trigger = WA_IoTriggerSettings()
        self.__settings_rx_pri     = WA_IoPRISettings()
        self.__settings_tx_pri     = WA_IoPRISettings()
        self.__settings_rx_misc    = WA_RxMiscSettings()
        self.__settings_tx_misc    = WA_TxMiscSettings()

    def __apply_settings(self):
        log.debug('Loading common settings...')
        self._dll.WaterlooApp_Load_Common(self.__settings_common)
        log.debug('Loading trigger settings...')
        self._dll.WaterlooApp_Load_RxTrigger(self.__settings_rx_trigger)
        self._dll.WaterlooApp_Load_TxTrigger(self.__settings_tx_trigger)
        log.debug('Loading PRI settings...')
        self._dll.WaterlooApp_Load_RxPRI(self.__settings_rx_pri)
        self._dll.WaterlooApp_Load_TxPRI(self.__settings_tx_pri)
        log.debug('Loading misc settings...')
        self._dll.WaterlooApp_Load_RxMisc(self.__settings_rx_misc)
        self._dll.WaterlooApp_Load_TxMisc(self.__settings_tx_misc)

    def __validate_file(self, attr, quiet):
        with open(getattr(self, attr), 'r'):
            if not quiet:
                print "[DEBUG] {} valid.".format(attr)

    ## SETTINGS PROPERTIES ##

    # FIXME: these need "python-ified". That is, make ints that act like
    #        bools into actual bools, decode obscured ints, etc.

    ext_clock_src_selection    = _expose_setting('common', 'ext_clock_src_selection', ExtClockSourceSelection, """
        Sets the source for the external clock signal to either be the front panel
        or the P16 connector on the rear of the X6 housing.
        
        .. seealso::
            X6-1000M user's manual (page 83)
        
        :type: `ExtClockSourceSelection`
    """)
    reference_clock_source     = _expose_setting('common', 'reference_clock_source', ClockSource, doc="""
        Sets the source for the reference clock to either be the internal oscillator
        or the external source selected by `X6.ext_clock_src_selection`.
        
        .. seealso::
            X6-1000M user's manual (page 83)
            
        :type: `ClockSource`
    """)
    reference_rate             = _expose_setting('common', 'reference_rate', float, doc="""
        :type: `float`
        :units: MHz
    """)
    sample_clock_source        = _expose_setting('common', 'sample_clock_source', ClockSource, doc="""
        Sets the source for the sample clock to either be the internal PLLs
        or the external source selected by `X6.ext_clock_src_selection`.
        
        .. seealso::
            X6-1000M user's manual (page 83)
            
        :type: `ClockSource`
    """)
    sample_rate                = _expose_setting('common', 'sample_rate', _nonnegative(float), doc="""
        Specifies the rate at which samples are to be played and aquired.
        The maximum sample rate for the X6-1000M board is 1 GHz
        (``sample_rate = 1000.0``).
        
        If more than one TX channel is active on the same hardware DAC, the
        samples will be broadcast to both channels if the sample rate is
        higher than 500 MHz, and will be deinterlaced if the sample rate is
        lower.
        
        Setting ``sample_rate < 0`` will cause a `ValueError`.

        :type: `float`
        :units: MHz
    """)
    ext_trigger_src_selection  = _expose_setting('common', 'ext_trigger_src_selection', int)
    auto_preconfig             = _expose_setting('common', 'auto_preconfig', bool_or_str, doc="""
        If this option is `True`, the board will be preconfigured before each
        call to :meth:`~x6.X6.start_streaming`.
        
        :type: `bool`
    """)
    debug_verbosity            = _expose_setting('common', 'debug_verbosity', int)
    alert_enable               = _expose_setting('common', 'alert_enable', list)

    rx_external_trigger        = _expose_setting('rx_trigger', 'external_trigger', bool_or_str, doc="""
        If `True`, will enable external triggering of the ADCs. Otherwise,
        the ADCs will be software triggered after a delay set by
        :attr:`~x6.X6.rx_trigger_delay_period`.

        :type: `bool`
    """)
    rx_edge_trigger            = _expose_setting('rx_trigger', 'edge_trigger', bool_or_str, doc="""
        If `True`, will set the external trigger to edge mode. Otherwise,
        the external trigger will act in level mode. Only effective if
        :attr:`~x6.X6.rx_external_trigger` is `True`.

        :type: `bool`
    """)
    rx_framed                  = _expose_setting('rx_trigger', 'framed', bool)
    rx_frame_size              = _expose_setting('rx_trigger', 'frame_size', int, doc="""
        If :attr:`~x6.X6.tx_framed` is `True`,
        specifies the number of points to take before setting the trigger to false.
        
        :units: samples
        
        .. seealso::
            X6-1000M user's manual (page 132)
            
        .. note::
            Must be divisible by 8 samples.
    """)
    rx_trigger_delay_period    = _expose_setting('rx_trigger', 'trigger_delay_period', int, """
        If :attr:`~x6.X6.rx_external_trigger` is `False`, specifies how long
        to wait after a call to `~x6.X6.start_streaming` before issuing
        a software trigger.

        :type: `int`
        :units: seconds
    """)
    rx_decimation_enable       = _expose_setting('rx_trigger', 'decimation_enable', bool_or_str)
    rx_decimation_factor       = _expose_setting('rx_trigger', 'decimation_factor', int)
    rx_active_channels         = _expose_setting('rx_trigger', 'active_channels', list, doc="""
        Specifies which ADC channels should be active for aquisition.
        For an instance `x`, if
        ``x.rx_active_channels[i]`` is `True`, then channel ``i``
        will be active.

        :type: `list` of length 2 containing `bool` values.
    """)

    tx_external_trigger        = _expose_setting('tx_trigger', 'external_trigger', bool_or_str)
    tx_edge_trigger            = _expose_setting('tx_trigger', 'edge_trigger', bool_or_str)
    tx_framed                  = _expose_setting('tx_trigger', 'framed', bool_or_str)
    tx_frame_size              = _expose_setting('tx_trigger', 'frame_size', int, doc="""
        If :attr:`~x6.X6.tx_framed` is `True`,
        specifies the number of points to take before setting the trigger to false.
        
        :units: samples
        
        .. seealso::
            X6-1000M user's manual (page 132)    
            
        .. note::
            Must be divisible by 8 samples.
    """)
    tx_trigger_delay_period    = _expose_setting('tx_trigger', 'trigger_delay_period', int, doc="""
        If :attr:`~x6.X6.tx_external_trigger` is `False`, specifies how long
        to wait after a call to `~x6.X6.start_streaming` before issuing
        a software trigger.

        :type: `int`
        :units: seconds
    """)
    tx_decimation_enable       = _expose_setting('tx_trigger', 'decimation_enable', bool_or_str)
    tx_decimation_factor       = _expose_setting('tx_trigger', 'decimation_factor', int)
    tx_active_channels         = _expose_setting('tx_trigger', 'active_channels', list)

    rx_enable_pri              = _expose_setting('rx_pri', 'enable', bool_or_str)
    rx_finite                  = _expose_setting('rx_pri', 'finite', bool_or_str)
    rx_rearm                   = _expose_setting('rx_pri', 'rearm', bool_or_str)
    rx_period                  = _expose_setting('rx_pri', 'period', long, """
        If :attr:`~x6.X6.rx_enable_pri` is `True`, sets the period of the
        entire PRI pattern specified by :attr:`~x6.X6.rx_pattern_file`.

        :type: `long`
        :units: samples
    """)
    rx_count                   = _expose_setting('rx_pri', 'count', int, doc="""
        If :attr:`~x6.X6.rx_enable_pri` and :attr:`~x6.X6.rx_finite` are `True`,
        specifies how many times the PRI patterns is to be repeated when
        triggered.
        
        :type: `int`
    """)
    rx_pattern_file            = _expose_setting('rx_pri', 'pattern_file', str)

    tx_enable_pri              = _expose_setting('tx_pri', 'enable', bool_or_str)
    tx_finite                  = _expose_setting('tx_pri', 'finite', bool_or_str)
    tx_rearm                   = _expose_setting('tx_pri', 'rearm', bool_or_str, """
        If :attr:`~x6.X6.tx_enable_pri` and :attr:`~x6.X6.tx_finite` are `True`,
        this property will allow the X6 to accept another trigger to repeat the
        pattern. For each trigger the X6 will output the pattern the number of times
        as specified by :attr:`~x6.X6.tx_count`.

        Note that this does not restart the DAC waveform. Your entire waveform must
        be preloaded into memory ahead of time, even if it is an identical copy.

        For example, with :attr:`~x6.X6.tx_count`=2, each trigger event will cause
        the X6 to output 2 copies of your pulse program separated in time by
        :attr:`~x6.X6.tx_period`. This can continue to occur until the X6 has
        completely played out the waveform that you have loaded.
    """)
    tx_period                  = _expose_setting('tx_pri', 'period', long)
    tx_count                   = _expose_setting('tx_pri', 'count', int)
    tx_pattern_file            = _expose_setting('tx_pri', 'pattern_file', str)

    rx_packet_size             = _expose_setting('rx_misc', 'packet_size', int)
    rx_force_size              = _expose_setting('rx_misc', 'force_size', bool_or_str)
    rx_test_counter_enable     = _expose_setting('rx_misc', 'test_counter_enable', bool_or_str)
    rx_test_gen_mode           = _expose_setting('rx_misc', 'test_gen_mode', int)
    rx_logger_enable           = _expose_setting('rx_misc', 'logger_enable', bool_or_str, doc="""
        Causes samples received by the ADCs to be written to ``Data.bin`` in
        the current working directory. The samples are logged as a stream of
        Velocia packets encapsulating one or more Vita packet streams, each
        corresponding to an active RX channel. The
        `x6.vita_convert.parse_velo_stream` function can be used to convert this
        file to ordinary NumPy arrays for further manipulation.
        
        :type: `bool`
        
        .. warning::
            If this option is set to `True`, any file named ``Data.bin`` in the
            current directory **will** be erased.
    """)
    rx_plot_enable             = _expose_setting('rx_misc', 'plot_enable', bool_or_str)
    rx_merge_parse_enable      = _expose_setting('rx_misc', 'merge_parse_enable', bool_or_str, doc="""
        This option replicates the behavior of the "Vita Merge Parse" option
        in the "Stream" example provided with the X6-1000M development kit,
        but is otherwise undocumented. It is recommended that this option be
        set to `False`, and that `x6.vita_convert` be used to interpret
        aquired data instead.
        
        :type: `bool`
    """)
    rx_samples_to_log          = _expose_setting('rx_misc', 'samples_to_log', int)
    rx_overwrite_bdd           = _expose_setting('rx_misc', 'overwrite_bdd', bool_or_str)
    rx_auto_stop               = _expose_setting('rx_misc', 'auto_stop', bool_or_str)
    rx_merge_packet_size       = _expose_setting('rx_misc', 'merge_packet_size', int)

    tx_test_gen_enable         = _expose_setting('tx_misc', 'test_gen_enable', bool_or_str)
    tx_test_gen_mode           = _expose_setting('tx_misc', 'test_gen_mode', int, doc="""
        Selects one of several functions to be generated on board the FPGA, rather than
        sent as per :attr:`~x6.X6.tx_play_from_file_filename`.
        
        :type: `TestGenerationMode`
    """)
    tx_test_frequency_mhz      = _expose_setting('tx_misc', 'test_frequency_mhz', float)
    tx_packet_size             = _expose_setting('tx_misc', 'packet_size', int)
    tx_play_from_file_enable   = _expose_setting('tx_misc', 'play_from_file_enable', bool_or_str, doc="""
        If `True`, the active DACs will play from waveform specified by
        :attr:`~x6.X6.tx_play_from_file_filename` when triggered.
        If :attr:`~x6.X6.tx_enable_pri` is also `True`, then the
        waveform will only be played during periods specified by
        :attr:`~x6.X6.tx_pattern_file`.
        
        :type: `bool`
    """)
    tx_play_from_file_filename = _expose_setting('tx_misc', 'play_from_file_filename', str, doc="""
        If :attr:`~x6.X6.tx_play_from_file_enable` is `True`, this
        property specifies the name of a waveform file to be played by
        the DACs. This file must be formatted as a stream of Velocia
        packets encapsulating a Vita packet stream. To convert an arbitrary
        waveform to this format, please see `x6.vita_convert.rawbin_to_velo`.
        
        :type: `str`
    """)
        
    ## OTHER PROPERTIES ##

    @property
    def n_boards(self):
        """
        Returns the number of boards detected by the X6-1000M driver.
        
        :type: `int`
        """
        return self._dll.WaterlooApp_BoardCount()

    @property
    def is_open(self):
        """
        Returns `True` if a board is currently open.
        """
        return self._is_open

    @property
    def is_streaming(self):
        """
        Returns `True` if a board is currently open and is in streaming mode.
        """
        return self._is_open and self._is_streaming

    @property
    def dll_version(self):
        """
        Returns the version of the ``WaterlooAppDll.dll`` library used by
        this driver, or `None` if the version information is missing from
        the DLL (this is normally due to using the II-provided version).
        """
        return self._dll.version

    ## BOARD STATE METHODS ##
        
    def open(self, idx_board=0, rx_busmaster_size=4, tx_busmaster_size=4):
        """
        Opens an X6 board with the given index. Note that only one
        board may be opened at a time.

        :param int idx_board: Index of the board to be opened, in the
            range ``[0, n_boards)``.
        :param int rx_busmaster_size: Size of the recieving busmaster in MiB.
        :param int tx_busmaster_size: Size of the transmitting busmaster in MiB.
        """
        if self._is_open:
            raise IOError("A board has already been opened; close the X6 first.")

        if idx_board not in xrange(self.n_boards):
            raise ValueError("Board index {} is invalid.".format(idx_board))
        
        try:
            res = self._dll.WaterlooApp_Open(
                idx_board,
                rx_busmaster_size,
                tx_busmaster_size)
            self._is_open = True
            self._is_streaming = False
            self.__init_settings()
        except WindowsError as ex:
            raise RuntimeError("Windows exception raised during Open: " + str(ex))
        
    def close(self):
        """
        Closes the currently connected board. If the board is currently streaming,
        then the stream is stopped. If no board is opened, this method does nothing.
        """
        # If we aren't open, do nothing.
        # This way, the method is idemptotent.
        if not self._is_open:
            return

        if self._is_streaming:
            try:
                self.stop_streaming()
            except Exception as ex:
                print "[WARN] Exception encountered while stopping stream; trying to close anyway.\n" + str(ex)

        try:
            res = self._dll.WaterlooApp_Close()
            self._is_open = False
            self._is_streaming = False
        except WindowsError as ex:
            raise RuntimeError("Windows exception raised during Close: " + str(ex))

    @_require_open_board
    def logic_version(self):
        """
        logic_version()
        
        Reads information from the board on the currently loaded
        logic.
        """
        logic_info = WA_PS_LogicInfo()
        self._dll.WaterlooApp_GetLogicVersion(byref(logic_info))
        return logic_info
        
    @_require_open_board
    def periodic_status(self):
        """
        periodic_status()
        
        Returns periodic status about the currently opened
        board, including temeprature and transfer rates.
        """
        periodic_status = _WS_PS_Results()
        self._dll.WaterlooApp_GetPeriodicStatus(byref(periodic_status))
        return periodic_status
        
    @_require_open_board
    def preconfigure(self, validate=True):
        """
        preconfigure(validate=True)
        
        Applies all configuration changes, calibrates the board and prepares
        the board for streaming.

        :param bool validate: If `True`, the current configuration will
            be validated before it is sent to the board.
        """
        if validate:
            self.validate_configuration()
        self.__apply_settings()
        self._dll.WaterlooApp_StreamPreconfigure()

    @_require_open_board
    def start_streaming(self):
        """
        start_streaming()
        
        Starts streaming to the connected board using the last configuration
        sent.
        """
        if self._is_streaming:
            raise IOError("The board is already streaming.")
        self._dll.WaterlooApp_StreamStart()
        self._is_streaming = True

    @_require_open_board
    def stop_streaming(self):
        """
        stop_streaming()
        
        Stops streaming to the connected board.
        """
        self._dll.WaterlooApp_StreamStop()
        self._is_streaming = False


    ## CONIFGURATION LOADING ##

    __SCALAR_CONF_ATTRS = [
        'ext_clock_src_selection',
        'reference_clock_source',
        'reference_rate',
        'sample_clock_source',
        'sample_rate',
        'ext_trigger_src_selection',
        'auto_preconfig',
        'debug_verbosity',
        
        'rx_external_trigger',
        'rx_edge_trigger',
        'rx_framed',
        'rx_frame_size',
        'rx_trigger_delay_period',
        'rx_decimation_enable',
        'rx_decimation_factor',

        'tx_external_trigger',
        'tx_edge_trigger',
        'tx_framed',
        'tx_frame_size',
        'tx_trigger_delay_period',
        'tx_decimation_enable',
        'tx_decimation_factor',

        'rx_enable_pri',
        'rx_finite',
        'rx_rearm',
        'rx_period',
        'rx_count',

        'tx_enable_pri',
        'tx_finite',
        'tx_rearm',
        'tx_period',
        'tx_count',

        'rx_packet_size',
        'rx_force_size',
        'rx_test_counter_enable',
        'rx_test_gen_mode',
        'rx_logger_enable',
        'rx_plot_enable',
        'rx_merge_parse_enable',
        'rx_samples_to_log',
        'rx_overwrite_bdd',
        'rx_auto_stop',
        'rx_merge_packet_size',

        'tx_test_gen_enable',
        'tx_test_gen_mode',
        'tx_test_frequency_mhz',
        'tx_packet_size',
        'tx_play_from_file_enable',
    ]

    __FILE_CONF_ATTRS = [
        'rx_pattern_file',
        'tx_pattern_file',
        'tx_play_from_file_filename',
    ]

    __ARRAY_CONF_ATTRS = [
        'alert_enable',
        'rx_active_channels',
        'tx_active_channels',
    ]
    
    @_require_open_board
    def load_configuration(self, conf_file, section='Default Pulse'):
        """
        load_configuration(conf_file, section='Default Pulse')
        
        Given the filename for a configuration file and a section within that
        file, loads a pulse configuration for application to the currently
        opened board. The configuration is not sent to the board until
        :meth:`preconfigure` is called.
        """
        conf = cp.SafeConfigParser()
        conf.read(conf_file)

        if not conf.has_section(section):
            warnings.warn("No section [{}] in {}. Using defaults from [DEFAULT] section.".format(
                section, conf_file
            ))
            conf.add_section(section)

        for conf_attr in self.__SCALAR_CONF_ATTRS:
            if conf.has_option(section, conf_attr):
                setattr(self, conf_attr, conf.get(section, conf_attr))
                
        for conf_attr in self.__FILE_CONF_ATTRS:
            if conf.has_option(section, conf_attr):
                # search for any file listed in conf_file relative to 
                # conf_file, and use the absolute path
                setattr(self, conf_attr, utils.search_for_file(conf.get(section, conf_attr), conf_file))

        for conf_attr in self.__ARRAY_CONF_ATTRS:
            if conf.has_option(section, conf_attr):
                setattr(self, conf_attr, conf.get(section, conf_attr).split(","))
            
    def save_configuration(self, conf_file, section='Default Pulse'):
        conf = cp.SafeConfigParser()
        conf.read(conf_file)

        if not conf.has_section(section):
            conf.add_section(section)

        for conf_attr in self.__SCALAR_CONF_ATTRS + self.__FILE_CONF_ATTRS:
            conf.set(section, conf_attr, str(getattr(self, conf_attr)))

        for conf_attr in self.__ARRAY_CONF_ATTRS:
            conf.set(section, conf_attr, ", ".join(map(str, getattr(self, conf_attr))))

        with open(conf_file, 'w') as f:
            conf.write(f)

    def validate_configuration(self, quiet=True):
        """
        Checks the current configuration for problems that may prevent the
        valid operation of the attached board. If any configuration problems
        are detected, an exception is raised.
        """
                
        # Check that filenames can be resolved.
        if self.tx_play_from_file_enable:
            self.__validate_file('tx_play_from_file_filename', quiet)
                    
        if self.tx_enable_pri:
            self.__validate_file('tx_pattern_file', quiet)
            
        if self.rx_enable_pri:
            self.__validate_file('rx_pattern_file', quiet)
            
        if any(self.rx_active_channels):
            # Try and load "Data.bin" for writing, see if we're allowed to.
            # If not, allow the IOError to propagate outward.
            f = open('Data.bin', 'wb')
            f.close()
            
        # Check that sample rates are correct for single- and multi-channel
        # outputs.
        multi_ch = all(self.tx_active_channels[0:2]) or all(self.tx_active_channels[2:4])
        if not multi_ch:
            if self.sample_rate > 1000:
                warnings.warn("X6-1000M cannot exceed 1GS/s. Consider reducing sample_rate.")
        else:
            if self.sample_rate > 500:
                warnings.warn("X6-1000M cannot exceed 500MS/s when in interlaced mode. Consider disabling a tx_active_channel or reducing sample_rate.")
