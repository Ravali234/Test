#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# holzworth_multi.py: Wrapper for HolzworthMulti64.dll used to connect to
#     Holzworth HS9000 series devices via USB. 
##
# Part of the Corylab Hardware Drivers project.
##

## IMPORTS ####################################################################

import ctypes as C
import instruments as ik

## LOGGING CONFIGURATION ######################################################

import logging
logger = logging.getLogger(__name__)

## FUNCTIONS ##################################################################

def prototype_dll(dll):
    """
    Sets ctypes prototypes based on the following C header:
        
        //Use the functions below for HS9000 series or legacy
        HOLZ_INIT int deviceAttached(const char *serialnum);
        HOLZ_INIT int openDevice(const char *serialnum);
        HOLZ_INIT char* getAttachedDevices();
        HOLZ_INIT void close_all (void);
        
        //Use the function below for HS9000 series only
        HOLZ_INIT char* usbCommWrite(const char *serialnum, const char *pBuf);
    """
    
    dll.deviceAttached.argtypes = [C.c_char_p]
    dll.openDevice.argtypes = [C.c_char_p]
    dll.getAttachedDevices.restype = C.c_char_p
    
    dll.usbCommWrite.argtypes = [C.c_char_p, C.c_char_p]
    dll.usbCommWrite.restype = C.c_char_p
    
def attached_devices():
    return _holzworth_dll.getAttachedDevices().split(',')
    
def usb_comm_write(serial_num, cmd):
    logger.debug(" <- {}".format(cmd))
    result = _holzworth_dll.usbCommWrite(serial_num, cmd)
    logger.debug(" -> {}".format(result.strip()))
    return result

## DLL HANDLING ###############################################################

logger.debug("Initializing HolzworthMulti64.dll...")
_holzworth_dll = C.windll.HolzworthMulti64
prototype_dll(_holzworth_dll)
logger.debug("Done initializing.")
logger.info("HolzworthMulti64.dll reports attached devices: {}".format(attached_devices()))


## CLASSES ####################################################################

class HolzworthMultiCommunicator(ik.abstract_instruments.comm.AbstractCommunicator):
    """
    InstrumentKit communicator that relays all I/O through the Holzworth-
    provided DLL.
    
    Note that since you cannot close a single device through the provided DLL,
    but must close all at once, the caller of this class is responsible for
    ensuring that close_all is called when appropriate.
    """
    
    def __init__(self, serial_num):
        super(HolzworthMultiCommunicator, self).__init__()
        self.address = serial_num
        
    ## INSTRUMENTKIT CONTRACT ##
    
    @property
    def address(self):
        return self._ser
    @address.setter
    def address(self, new_ser):
        if new_ser not in attached_devices():
            raise ValueError("Serial number {} not in list of attached devices.".format(new_ser))
        self._ser = new_ser
        _holzworth_dll.openDevice(self._ser)
    
    @property
    def terminator(self):
        return '' # Don't use a terminator; the DLL handles that already.
    @terminator.setter
    def terminator(self, newval):
        raise NotImplementedError("Terminator is read-only for this communicator.")
        
    @property
    def timeout(self):
        return NotImplemented
    @timeout.setter
    def timeout(self, newval):
        raise NotImplementedError("HolzworthMulti64.dll does not support timeouts.")
        
    def _query(self, msg, size=-1):
        return usb_comm_write(self._ser, msg)
        
    def _sendcmd(self, msg):
        self.query(msg) # Discard response?
        
    def flush_input(self):
        pass # Should be a nop, since this is handled internally to the DLL.
