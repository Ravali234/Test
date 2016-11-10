#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# _enums.py: Definitions of common enumerations used in configuring the X6
#     board.
##
# Author: Christopher Granade (cgranade@cgranade.com).
##
# NOTE:
#     Requires the WaterlooAppDll.dll provided by II to be visible on
#     %PATH%.
##

## IMPORTS ####################################################################

from flufl.enum import Enum, IntEnum

## ENUMS ######################################################################

class ClockSource(IntEnum):
    #: Selects the clock source to be the X6-1000M's internal oscillator.
    internal = 1
    #: Selects the clock source to be the external clock indicated
    #: by `~x6.X6.ext_clock_src_selection`.
    external = 0
    
class ExtClockSourceSelection(IntEnum):
    # Clock Selection
    #: Indicates that the external clock is connected via the front panel.
    front_panel = 0
    #: Indicates that the external clock is connected via the P16 connector
    #: on the rear of the X6-1000M's housing.
    p16         = 1

class RXPRIDestinations(IntEnum):
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
    
class TXPRIDestinations(IntEnum):
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
    
class TestGenerationMode(IntEnum):
    ramp = 0
    sine = 1
    bit_toggle = 2
    zero = 3
    max_pos = 4
    max_neg = 5
    fast_square = 6
    slow_square = 7
    