#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# waterlooapp_dll.py: Thin ctypes-based wrapper for
#     WaterlooAppDll.dll.
##
# Author: Christopher Granade (cgranade@cgranade.com).
##
# NOTE:
#     Requires the WaterlooAppDll.dll provided by II to be visible on
#     %PATH%.
##

## IMPORTS ###################################################################

import warnings
import logging
from ctypes import *
import os

## ENVIRONMENT VARIABLES #####################################################

# We need to make sure that KMP_DUPLICATE_LIB_OK is set to "TRUE".
if (
        "KMP_DUPLICATE_LIB_OK" not in os.environ
        or os.environ["KMP_DUPLICATE_LIB_OK"] != "TRUE"
    ):
    warnings.warn("Environment variable KMP_DUPLICATE_LIB_OK not set to 'TRUE'. This may cause problems.")
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

## LOGGING SETUP #############################################################

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())
    
## FUNCTIONS #################################################################

def bool_or_str(val):
    if isinstance(val, str) and val.strip() in ['True', 'False']:
        return eval(val)
    else:
        return bool(val)

def bool_property(attr_name):
    """
    Given an attribute name ``attr_name`` that refers to a non-bool
    attribute, returns a getter and setter to wrap it in a property
    such that the attribute is exposed as a bool.

    Will return something equivalent to:
    
    @property
    def external_trigger(self):
        return bool(self._external_trigger)
    @external_trigger.setter
    def external_trigger(self, newval):
        self._external_trigger = 1 if newval else 0
    """
    def getter(self):
        return bool(getattr(self, attr_name))
    
    def setter(self, newval):
        setattr(self, attr_name, 1 if newval else 0)

    return property(fget=getter, fset=setter)

def str_prop_methods(fname):
    """
    Given a structure field name ``fname``, provides
    getter and setter methods to abstract access to the null-terminated
    C string value of that field name, following the II convention
    of having a matching field indicating the size.
    """
    def getter(self):
        return getattr(self, fname)
    def setter(self, newval):
        newval = str(newval)
        setattr(self, fname, c_char_p(newval))
        setattr(self, fname + "_size", len(newval) + 1) # Leave room for the \0.

    return property(fget=getter, fset=setter)
 
def _errcheck_v0(result, func, args):
    """
    Error check function used with version 0 of the DLL.
    If version 1 has been loaded, please use the `ErrCheckV1` class.
    """
    if result == -1:
        raise RuntimeError("Unspecified error inside {}.".format(func.__name__))
    
## CLASSES ###################################################################

## MOCK DLL ##

class WaterlooDllDummy(object):
    """
    Mocks the functionality and failure modalities of
    WaterlooAppDll.dll for testing of the X6 driver
    class on platforms not supported by that library.
    """
    
    def __init__(self):
        self._common_settings = None
        self._is_open = False
        self._is_streaming = False
    
    def WaterlooApp_Init(self):
        return 0

    def WaterlooApp_Cleanup(self):
        pass

    def WaterlooApp_BoardCount(self):
        return 1

    def WaterlooApp_Open(self, idx, rx_bms, tx_bms):        
        self._is_open = True
        self._is_streaming = False
        return 0

    def WaterlooApp_Close(self):
        if self._is_streaming:
            raise RuntimeError("Simulated crash of WaterlooAppDll.dll.")
        self._is_open = False

    def WaterlooApp_Preconfigure(self):
        pass
    
    def WaterlooApp_GetLogicVersion(self, logic_version_struct):
        pass
    
    def WaterlooApp_Load_Common(self, common_settings):
        self._common_settings = common_settings
    
class WindllDummy(object):
    def __init__(self):
        self.WaterlooAppDll = WaterlooDllDummy()

if 'windll' not in globals():
    # We need to mock up the DLL for testing in this case.
    print '[NOTE] No windll support; mocking up DLL.'
    windll = WindllDummy()

## STRUCTURES ##

class WA_PS_Results(Structure):
    """
    ctypes implementation of the structure:

    struct WA_PS_Results
    {
        unsigned int TxBlockCount;
        unsigned int RxBlockCount;
        unsigned int PllLocked;
        double       TxBlockRate;
        double       RxBlockRate;
        double       Temperature;
    };
    """
    _fields_ = [
        ('tx_block_count', c_uint),
        ('rx_block_count', c_uint),
        ('_pll_locked', c_uint),
        ('tx_block_rate', c_double),
        ('rx_block_rate', c_double),
        ('temperature', c_double)
    ]
    
    pll_locked = bool_property('_pll_locked')
    
    def __str__(self):
        return """
            TX block count: {0.tx_block_count}
            TX block rate:  {0.tx_block_rate}
            RX block count: {0.rx_block_count}
            RX block rate:  {0.rx_block_rate}
            
            Temperature:    {0.temperature}
            PLL Locked:     {0.pll_locked}
        """.format(self)
    
class WA_PS_LogicInfo(Structure):
    """
    ctypes implementation of the structure:
    
    struct WA_PS_LogicInfo
    {
        unsigned int FpgaLogicVersion;
        unsigned int FpgaHardwareVariant;
        unsigned int PciLogicRevision;
        unsigned int FpgaLogicSubrevision;
        unsigned int PciLogicFamily;
        unsigned int PciLogicType;
        unsigned int PciLogicPcb;
        unsigned int FpgaChipType;
        unsigned int LaneCount;
    };
    """
    _fields_ = [
        ('fpga_logic_version', c_uint),
        ('fpga_hardware_variant', c_uint),
        ('pci_logic_revision', c_uint),
        ('fpga_logic_subrevision', c_uint),
        ('pci_logic_family', c_uint),
        ('pci_logic_type', c_uint),
        ('fpga_chip_type', c_uint),
        ('lane_count', c_uint)
    ]

    def __str__(self):
        return """
            FPGA logic version:     {0.fpga_logic_version}
            FPGA logic subrevision: {0.fpga_logic_subrevision}
            FPGA hardware variant:  {0.fpga_hardware_variant}
            FPGA chip type:         {0.fpga_chip_type}
            PCI logic revision:     {0.pci_logic_revision}
            PCI logic family:       {0.pci_logic_family}
            PCI logic type:         {0.pci_logic_type}
            Lane count:             {0.lane_count}
        """.format(self)


# NOTE: We should probably deal with this structure
#       separately and not send it unless explicitly
#       required.
class WA_VWBSettings(Structure):
    """
    struct WA_VWBSettings     // Test Graph Settings
    {
        const char *    WaveFile;
        int             WaveFile_size;
        int             WaveType;
        float           WaveformFrequency;
        float           WaveformAmplitude;
        int             TwoToneMode;
        float           TwoToneFrequency;
        int             SingleChannelMode;
        int             SingleChannelChannel;
    };
    """
    _fields_ = [
        ('_WaveFile', c_char_p),
        ('_WaveFile_size', c_int),
        ('WaveType', c_int),
        ('WaveformFrequency', c_float),
        ('WaveformAmplitude', c_float),
        ('TwoToneMode', c_int),
        ('TwoToneFrequency', c_float),
        ('SingleChannelMode', c_int),
        ('SingleChannelChannel', c_int),
    ]

    wave_file = str_prop_methods('_WaveFile')

class WA_CommonSettings(Structure):
    """
    struct WA_CommonSettings     // Clock & Common Settings
    {
        int             ExtClockSrcSelection;
        int             ReferenceClockSource;
        float           ReferenceRate;
        int             SampleClockSource;
        float           SampleRate;
        int             ExtTriggerSrcSelection;
        int             AlertEnable[7];
        int             AutoPreconfig;
        int             DebugVerbosity;
    };
    """
    _fields_ = [
        ('ext_clock_src_selection', c_int),
        ('reference_clock_source', c_int),
        ('reference_rate', c_float),
        ('sample_clock_source', c_int),
        ('sample_rate', c_float),
        ('ext_trigger_src_selection', c_int),
        ('_alert_enable', c_int * 7),
        ('_auto_preconfig', c_int),
        ('debug_verbosity', c_int)
    ]

    auto_preconfig = bool_property('_auto_preconfig')

    # TODO: make an array property function to abstract this.
    @property
    def alert_enable(self):
        return map(bool, self._alert_enable)
    @alert_enable.setter
    def alert_enable(self, newval):
        self._alert_enable[:] = [1 if bool_or_str(chan) else 0 for chan in newval]

class WA_IoTriggerSettings(Structure):
    """
    struct WA_IoTriggerSettings     // Tx/Rx Trigger Settings
    {
        int             ExternalTrigger;
        int             EdgeTrigger;
        int             Framed;
        int             FrameSize;
        int             TriggerDelayPeriod;
        int             ActiveChannels[4];
        bool            DecimationEnable;
        int             DecimationFactor;
    }
    """
    _fields_ = [
        ('_external_trigger', c_int),
        ('_edge_trigger', c_int),
        ('_framed', c_int),
        ('frame_size', c_int),
        ('trigger_delay_period', c_int),
        ('_active_channels', c_int * 4),
        ('_decimation_enable', c_bool),
        ('decimation_factor', c_int),
    ]

    external_trigger  = bool_property('_external_trigger')
    edge_trigger      = bool_property('_edge_trigger')
    framed            = bool_property('_framed')
    decimation_enable = bool_property('_decimation_enable')

    @property
    def active_channels(self):
        return map(bool, self._active_channels)
    @active_channels.setter
    def active_channels(self, newval):
        if len(newval) < 4:
            newval = list(newval) + [False] * (4 - len(newval))
        self._active_channels[:] = [1 if bool_or_str(chan) else 0 for chan in newval]
        
    def __str__(self):
        return (
"""
WA_IoTriggerSettings:
    ExternalTrigger = {0._external_trigger};
    EdgeTrigger = {0._edge_trigger};
    Framed = {0._framed};
    FrameSize = {0.frame_size};
    TriggerDelayPeriod = {0.trigger_delay_period};
    ActiveChannels[4] = {0._active_channels};
    DecimationEnable = {0._decimation_enable};
    DecimationFactor = {0.decimation_factor};
""".format(self))
        

class WA_IoPRISettings(Structure):
    """
    struct WA_IoPRISettings     // Tx/Rx PRI Settings
    {
        int             Enable;
        int             Finite;
        int             Rearm;
        ii64            Period;
        unsigned int    Count;
        const char *    PatternFile;
        int             PatternFile_size;

    };
    """
    _fields_ = [
        ('_enable', c_int),
        ('_finite', c_int),
        ('_rearm', c_int),
        ('period', c_ulonglong),
        ('count', c_uint),
        ('_PatternFile', c_char_p),
        ('_PatternFile_size', c_int),
    ]

    enable       = bool_property('_enable')
    finite       = bool_property('_finite')
    rearm        = bool_property('_rearm')
    pattern_file = str_prop_methods('_PatternFile')

class WA_RxMiscSettings(Structure):
    """
    struct WA_RxMiscSettings     // Rx Other Settings
    {
            //  Streaming
            int             PacketSize;
            int             ForceSize;
            // Testing
            bool            TestCounterEnable;
            int             TestGenMode;
            //  Logging
            int             LoggerEnable;
            int             PlotEnable;
            int             MergeParseEnable;
            unsigned int    SamplesToLog;
            int             OverwriteBdd;
            int             AutoStop;
            unsigned int    MergePacketSize;
    };
    """
    _fields_ = [
        ('packet_size', c_int),
        ('_force_size', c_int),
        
        ('test_counter_enable', c_bool),
        ('test_gen_mode', c_int),

        ('_logger_enable', c_int),
        ('_plot_enable', c_int),
        ('_merge_parse_enable', c_int),
        ('samples_to_log', c_uint),
        ('_overwrite_bdd', c_int),
        ('_auto_stop', c_int),
        ('merge_packet_size', c_uint),
    ]

    force_size = bool_property('_force_size')
    logger_enable = bool_property('_logger_enable')
    plot_enable = bool_property('_plot_enable')
    merge_parse_enable = bool_property('_merge_parse_enable')
    overwrite_bdd = bool_property('_overwrite_bdd')
    auto_stop = bool_property('_auto_stop')

class WA_TxMiscSettings(Structure):
    """
    struct WA_TxMiscSettings     // Tx Other Settings
    {
        int             TestGenEnable;
        int             TestGenMode;
        double          TestFrequencyMHz;
        //  Streaming
        int             PacketSize;
        int             PlayFromFile_Enable;
        const char *    PlayFromFile_Filename;
        int             PlayFromFile_Filename_size;
    };
    """
    _fields_ = [
        ('_test_gen_enable', c_int),
        ('test_gen_mode', c_int),
        ('test_frequency_mhz', c_double),

        ('packet_size', c_int),
        ('_play_from_file_enable', c_int),
        ('_PlayFromFile_Filename', c_char_p),
        ('_PlayFromFile_Filename_size', c_int),
    ]
    
    test_gen_enable = bool_property('_test_gen_enable')
    play_from_file_enable = bool_property('_play_from_file_enable')
    play_from_file_filename = str_prop_methods('_PlayFromFile_Filename')

## DLL WRAPPER ##
    
class WaterlooAppDll(object):

    def __init__(self):
        # Grab the actuall DLL object.
        dll = windll.WaterlooAppDll
        # Save it away for later use.
        self._dll = dll
        
        # If it's a Dummy, we're done.
        if isinstance(dll, WaterlooDllDummy):
            return
        
        # Otherwise, we need to make prototypes and register callbacks.
        
        # Check whether this version of the DLL supports
        # version checking.
        if hasattr(dll, 'WaterlooApp_DllVersion'):
            dll.WaterlooApp_DllVersion.restype = c_uint
            dll.WaterlooApp_DllVersion.argtypes = []
            self.__version = dll.WaterlooApp_DllVersion()
            log.debug('Building prototypes for DLL version {}...'.format(self.__version))
            ec_int = self.chk_int
            ec_void = self.chk_void
        else:
            self.__version = None
            log.debug('Building prototypes for unknown DLL version ...')
            ec_int = _errcheck_v0
            ec_void = lambda result, func, args: None
            
        # int EXPORT WaterlooApp_Init();
        dll.WaterlooApp_Init.restype = c_int
        dll.WaterlooApp_Init.argtypes = []
        dll.WaterlooApp_Init.errcheck = ec_int
        
        # int EXPORT WaterlooApp_Cleanup();
        dll.WaterlooApp_Cleanup.restype = c_int
        dll.WaterlooApp_Cleanup.argtypes = []
        dll.WaterlooApp_Cleanup.errcheck = ec_int

        # int EXPORT WaterlooApp_Open(int target, int RxBmSize, int TxBmSize);
        dll.WaterlooApp_Open.restype = c_int
        dll.WaterlooApp_Open.argtypes = [
            c_int, c_int, c_int
        ]
        dll.WaterlooApp_Open.errcheck = ec_int

        # int EXPORT WaterlooApp_Close();
        dll.WaterlooApp_Close.restype = c_int
        dll.WaterlooApp_Close.argtypes = []
        dll.WaterlooApp_Close.errcheck = ec_int

        # void EXPORT WaterlooApp_Load_TestGraph(WA_VWBSettings * settings);
        dll.WaterlooApp_Load_TestGraph.restype = None
        dll.WaterlooApp_Load_TestGraph.argtypes = [POINTER(WA_VWBSettings)]
        dll.WaterlooApp_Load_TestGraph.errcheck = ec_void
        
        # void EXPORT WaterlooApp_Load_Common(WA_CommonSettings * settings);
        dll.WaterlooApp_Load_Common.restype = None
        dll.WaterlooApp_Load_Common.argtypes = [POINTER(WA_CommonSettings)]
        dll.WaterlooApp_Load_Common.errcheck = ec_void
        
        # void EXPORT WaterlooApp_Load_TxTrigger(WA_IoTriggerSettings * settings);
        dll.WaterlooApp_Load_TxTrigger.restype = None
        dll.WaterlooApp_Load_TxTrigger.argtypes = [POINTER(WA_IoTriggerSettings)]
        dll.WaterlooApp_Load_TxTrigger.errcheck = ec_void

        # void EXPORT WaterlooApp_Load_RxTrigger(WA_IoTriggerSettings * settings);
        dll.WaterlooApp_Load_RxTrigger.restype = None
        dll.WaterlooApp_Load_RxTrigger.argtypes = [POINTER(WA_IoTriggerSettings)]
        dll.WaterlooApp_Load_RxTrigger.errcheck = ec_void

        # void EXPORT WaterlooApp_Load_TxPRI(WA_IoPRISettings * settings);
        dll.WaterlooApp_Load_TxPRI.restype = None
        dll.WaterlooApp_Load_TxPRI.argtypes = [POINTER(WA_IoPRISettings)]
        dll.WaterlooApp_Load_TxPRI.errcheck = ec_void

        # void EXPORT WaterlooApp_Load_RxPRI(WA_IoPRISettings * settings);
        dll.WaterlooApp_Load_RxPRI.restype = None
        dll.WaterlooApp_Load_RxPRI.argtypes = [POINTER(WA_IoPRISettings)]
        dll.WaterlooApp_Load_RxPRI.errcheck = ec_void

        # void EXPORT WaterlooApp_Load_TxMisc(WA_TxMiscSettings * settings);
        dll.WaterlooApp_Load_TxMisc.restype = None
        dll.WaterlooApp_Load_TxMisc.argtypes = [POINTER(WA_TxMiscSettings)]
        dll.WaterlooApp_Load_TxMisc.errcheck = ec_void

        # void EXPORT WaterlooApp_Load_RxMisc(WA_RxMiscSettings * settings);
        dll.WaterlooApp_Load_RxMisc.restype = None
        dll.WaterlooApp_Load_RxMisc.argtypes = [POINTER(WA_RxMiscSettings)]
        dll.WaterlooApp_Load_RxMisc.errcheck = ec_void

        # void EXPORT WaterlooApp_StreamPreconfigure();
        dll.WaterlooApp_StreamPreconfigure.restype = None
        dll.WaterlooApp_StreamPreconfigure.argtypes = []
        dll.WaterlooApp_StreamPreconfigure.errcheck = ec_void

        # int EXPORT WaterlooApp_StreamStart();
        dll.WaterlooApp_StreamStart.restype = c_int
        dll.WaterlooApp_StreamStart.argtypes = []
        dll.WaterlooApp_StreamStart.errcheck = ec_int

        # void EXPORT WaterlooApp_StreamStop();
        dll.WaterlooApp_StreamStop.restype = None
        dll.WaterlooApp_StreamStop.argtypes = []
        dll.WaterlooApp_StreamStop.errcheck = ec_void

        # unsigned int EXPORT WaterlooApp_BoardCount();
        dll.WaterlooApp_BoardCount.restype = c_uint
        dll.WaterlooApp_BoardCount.argtypes = []

        # void EXPORT WaterlooApp_GetPeriodicStatus(WA_PS_Results * results);
        dll.WaterlooApp_GetPeriodicStatus.restype = None
        dll.WaterlooApp_GetPeriodicStatus.argtypes = [POINTER(WA_PS_Results)]
        dll.WaterlooApp_GetPeriodicStatus.errcheck = ec_void
        
        # void EXPORT WaterlooApp_GetLogicVersion(WA_PS_LogicInfo * results);
        dll.WaterlooApp_GetLogicVersion.restype = None
        dll.WaterlooApp_GetLogicVersion.argtypes = [POINTER(WA_PS_LogicInfo)]
        dll.WaterlooApp_GetLogicVersion.errcheck = ec_void
        
        # New functions with version 1.
        if self.__version >= 1:
            # void EXPORT WaterlooApp_RegisterLogCallback(log_callback_t logger);
            self.log_callback_t = CFUNCTYPE(None, c_char_p)
            dll.WaterlooApp_RegisterLogCallback.restype = None
            dll.WaterlooApp_RegisterLogCallback.argtypes = [self.log_callback_t]
            dll.WaterlooApp_RegisterLogCallback.errcheck = ec_void
            
            # const char* EXPORT WaterlooApp_LastError();
            dll.WaterlooApp_LastError.restype = c_char_p
            dll.WaterlooApp_LastError.argtypes = []
          
    @property
    def version(self):
        return self.__version
          
    def __getattr__(self, name):
        """
        Pass through accesses to DLL functions automatically.
        """
        if name.startswith("WaterlooApp_"):
            return getattr(self._dll, name)
        else:
            raise AttributeError("No attribute {}.".format(name))
            
    def chk_int(self, result, func, args):
        if result == -1:
            what = self._dll.WaterlooApp_LastError()
            raise RuntimeError("Error inside {}: {}".format(func.__name__, what))
            
    def chk_void(self, result, func, args):
        what = self._dll.WaterlooApp_LastError()
        if what:
            raise RuntimeError("Error inside {}: {}".format(func.__name__, what))
    