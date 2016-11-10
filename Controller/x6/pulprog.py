#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# pulprog.py: Parser and compiler for the X6 variant of the pulprog pulse
#     programming language.
##
# Authors: Christopher Granade (cgranade@cgranade.com) and Ian Hincks.
##

## FEATURES ####################################################################

from __future__ import division

## IMPORTS #####################################################################

import os, sys
import numpy as np
import pyparsing as pp
import tempfile
import warnings
import shutil

import ConfigParser as cp
import cStringIO
import pkgutil

try:
    import quantities as pq
except ImportError:
    pq = None

from x6 import TX_CHANNELS, CHANNEL_PRI_CODES
from x6 import pulplot
from x6.process_waveform import Waveform, IQWaveform, waveform_to_velo, rewind_write, apply_phase
from x6.utils import PRIPatternParser, validate_active_channels, find_on_path
import x6.utils as u

## UNITS #######################################################################
# We define units such as seconds abstractly so that we can easily change
# scales.

UNIT_VALUES = {
    's':  1e6,
    'ms': 1e3,
    'us': 1e0,
    'ns': 1e-3,
    'ps': 1e-6
}

## HELPER FUNCTIONS ############################################################

def mk_namespace_dict(from_dict):
    """
    Given a dictionary from `str` keys to arbitrary values, attempts to
    convert that dictionary to a namespace dictionary as expected by
    `compile_program`.
    """
    namespace = {}
    if from_dict is not None:
        for key, val in from_dict.iteritems():
            if not isinstance(key, Identifier):
                key = Identifier(str(key))
    
            if pq is not None and isinstance(val, pq.Quantity):
                # Attempt to convert to a time.
                val = Time(val.rescale('us').magnitude * UNIT_VALUES['us'])
    
            elif isinstance(val, np.ndarray):
                # Treat as a waveform.
                # TODO: provide a way of making IQWaveforms.
                val = Waveform(val)
    
            # If val is anything else, leave it alone.
    
            namespace[key] = val

    return namespace

def fn_like_literal(keyword, inner_pattern, return_type):
    """
    Given a keyword and a PyParsing pattern, returns a new pattern that matches
    strings like ``keyword(inner_pattern)`` and encapsulates the caught
    inner string using a given function.
    
    For instance, ``channel(2)`` is turned into an instance of
    `~x6.pulprog.Channel` by
    ``fn_like_literal(pp.Keyword('channel'), integer_literal, Channel)``.
    """
    def returner(s, loc, toks):
        return return_type(toks[0].value)
        
    return pp.Group(
        keyword.suppress() + l_paren.leaveWhitespace() + inner_pattern.setResultsName('value') + r_paren
    ).setParseAction(
        returner
    )

def resolve_sym(sym, namespace):
    if isinstance(sym, Identifier):
        if sym in namespace:
            return namespace[sym]
        else:
            raise KeyError("Variable {} has not been defined.".format(sym.name))
    else:
        return sym    
        

## CLASSES #####################################################################

class Time(object):
    def __init__(self, time):
        self._time = time
        
    def __str__(self):
        return "{} s".format(str(self._time/ UNIT_VALUES['s']))
        
    def __repr__(self):
        return "<Time {} s>".format(self.time)
        
    @property
    def time(self):
        return self._time / UNIT_VALUES['s']
        
class Identifier(object):
    """
    Represents an identifier used as the name of a variable.
    """
    
    def __init__(self, name):
        self._name = name
        
    def __repr__(self):
        return "<Identifier {}>".format(self.name)
        
    @property
    def name(self):
        return self._name
        
    def __hash__(self):
        return hash(self.name)
        
    def __eq__(self, other):
        if isinstance(other, Identifier):
            return self.name == other.name
        else:
            return False

class Resolvable(object):
    """
    Base class for object types that need identifiers resolved for them.
    """
    def _resolve_(self, namespace):
        return NotImplemented
        
class Channel(object):
    """
    Represents either an analog or digital channel associated with a given
    pinout name.
    """

    def __init__(self, pin_name, analog):
        self._pin_name = pin_name
        if isinstance(analog, str):
            self._analog = analog == "analog"
        else:
            self._analog = bool(analog)
            
    @property
    def analog(self):
        return self._analog
        
    @property
    def pri_code(self):
        """
        Returns the bitmask used as a PRI destination code when sending output
        to or recieving input from this channel.
        
        :type: `int`
        """
        return CHANNEL_PRI_CODES[self._pin_name]
        
    @property
    def is_rx(self):
        """
        `True` if and only if the pin for this channel is controlled by the
        RX PRI settings on the X6 board.
        
        .. note::
            This does not necessarily mean that the pin is used to recieve data,
            but only that the pin is configured via the reciever settings.
        """
        return not self.is_tx
        
    @property
    def is_tx(self):
        """
        `True` if and only if the pin for this channel is controlled by the
        TX PRI settings on the X6 board.
        
        .. note::
            This does not necessarily mean that the pin is used to transmit data,
            but only that the pin is configured via the transmitter settings.
        """
        return self._pin_name in TX_CHANNELS
            
    def __str__(self):
        return "{} [{}]".format(self._pin_name, "analog" if self.analog else "digital")
        
    def __repr__(self):
        return "<Channel {}>".format(str(self))

class IQChannel(Channel, Resolvable):
    """
    Subclass of `Channel` representing the pairing of two channels into
    a single logical channel with in-phase and quadrature parts.
    """
    def __init__(self, ch_i, ch_q):
        self._ch_i = ch_i
        self._ch_q = ch_q

    def _resolve_(self, namespace):
        if isinstance(self._ch_i, Identifier):
            self._ch_i = namespace[self._ch_i]
        if isinstance(self._ch_q, Identifier):
            self._ch_q = namespace[self._ch_q]
        if self._ch_i._pin_name == self._ch_q._pin_name:
            raise ValueError('Different TX channels must be used in an IQChannel.')
        if not self._ch_i.analog or not self._ch_q.analog:
            raise ValueError('Both channels in an IQChannel must be analog channels.')

    @property
    def resolved(self):
        return not (isinstance(self._ch_i, Identifier) or isinstance(self._ch_q, Identifier))

    @property
    def analog(self): return True

    @property
    def is_tx(self): return True

    @property
    def pri_code(self):
        if self.resolved:
            return self._ch_i.pri_code | self._ch_q.pri_code
        else:
            return None

    def __repr__(self):
        if self.resolved:
            return "<IQChannel I = {}, Q = {}>".format(
                self._ch_i._pin_name, self._ch_q._pin_name
            )
        else:
            return "<IQChannel I = {}, Q = {} [unresolved]>".format(
                self._ch_i, self._ch_q
            )

    def __str__(self):
        return "(I={}, Q={}) [iq]".format(
            self._ch_i, self._ch_q
        )
       
class PhaseList(object):
    def __init__(self, phases, n_parts):
        self._phases = phases
        self._n_parts = n_parts
        self._idx = 0
        
    def __str__(self):
        return str(self._phases) + " / " + str(self._n_parts)
        
    def __repr__(self):
        return "<PhaseList {}>".format(str(self))
        
    @property
    def cur(self):
        return (self._phases[self._idx], self._n_parts)
        
    def ipp(self):
        self._idx = (self._idx + 1) % len(self._phases)
        

## GRAMMAR #####################################################################

# Disable newlines as a whitespace character.
pp.ParserElement.setDefaultWhitespaceChars(" \t")

## FORWARD DEFINITIONS ##
statement_list = pp.Forward()
channel = pp.Forward()

## SUPPRESSED LITERALS ##
# These literals are syntatically important, but we do not want to actually
# see them in the extracted output.
newline = pp.Suppress("\n")
colon   = pp.Suppress(":")
comma   = pp.Suppress(",")
l_paren = pp.Suppress("(")
r_paren = pp.Suppress(")")
l_bracket = pp.Suppress("[")
r_bracket = pp.Suppress("]")
l_brace = pp.Suppress("{")
r_brace = pp.Suppress("}")
slash = pp.Suppress("/")
comment_start = pp.Suppress(";")
equals  = pp.Suppress("=")
quote = pp.Suppress('"')
dot = pp.Literal(".")

## KEYWORDS ##
# These literals act as keywords, and must have a non-word character following
# them.
boolean_trues = ['True', 'true', 'on', 'high']
boolean_falses = ['False', 'false', 'off', 'low']
boolean = pp.oneOf(boolean_trues + boolean_falses).setParseAction(
    lambda s, loc, toks: toks[0] in boolean_trues
)
define = pp.Keyword("define")
delay  = pp.Keyword("delay")
phase_kw  = pp.Keyword("phase")
include = pp.Keyword("include")
channel_kw = pp.Keyword("channel")
iqchannel_kw = pp.Keyword("iqchannel")
waveform_kw = pp.Keyword("waveform")
iqwaveform_kw = pp.Keyword("iqwaveform")
print_kw = pp.Keyword("print")
analog_kw = pp.Keyword("analog")
digital_kw = pp.Keyword("digital")
ipp_kw = pp.Keyword("ipp")
repeat_kw = pp.Keyword("repeat")
option_kw = pp.Keyword("option")
keyword = (
    define | delay | phase_kw | include | channel_kw |
    iqchannel_kw | waveform_kw | iqwaveform_kw |
    analog_kw | digital_kw | print_kw | boolean | ipp_kw | repeat_kw |
    option_kw
)

## LITERAL VALUES ##
# Here, we define the various kinds of literals that we can have in our grammar,
# including integers, floats, times, strings, phases, waveforms and channels.

integer_literal = pp.Word(pp.nums).setParseAction(lambda s, loc, toks: int(toks[0]))
float_literal = pp.Group(integer_literal + dot.leaveWhitespace() + integer_literal.leaveWhitespace()).setParseAction(
    lambda s, loc, toks: float(str(toks[0][0]) + "." + str(toks[0][2]))
)
number_literal = (float_literal | integer_literal)

time_suffix = pp.oneOf(['s', 'ms', 'us', 'ns', 'ps'])
time_literal = pp.Group(number_literal + time_suffix.leaveWhitespace()).setParseAction(
    lambda s, loc, toks: Time(toks[0][0] * UNIT_VALUES[toks[0][1]])
).setResultsName('time_literal')

string_literal = pp.dblQuotedString.setParseAction(pp.removeQuotes)

phase_literal = pp.Group(
    l_bracket + 
    pp.delimitedList(
        integer_literal,
        delim=("," + pp.Optional(pp.White(" ")))
    ).setResultsName('phases') +
    r_bracket + pp.Optional(pp.White(" ")) +
    slash + pp.Optional(pp.White(" ")) +
    integer_literal.setResultsName('n_parts')
).setParseAction(
    lambda s, loc, toks: PhaseList(toks[0].phases, toks[0].n_parts)
)

waveform_literal = fn_like_literal(waveform_kw, string_literal, Waveform)
iqwaveform_literal = fn_like_literal(iqwaveform_kw,
    string_literal.setResultsName('waveform_i') + comma +
    string_literal.setResultsName('waveform_q'),
    lambda match: IQWaveform(**match))
channel_literal = fn_like_literal(channel_kw,
    string_literal.setResultsName('pin_name') + comma +
    (analog_kw | digital_kw).setResultsName('analog'),
    lambda match: Channel(**match))
iqchannel_literal = fn_like_literal(iqchannel_kw,
    channel.setResultsName('ch_i') +
    comma + pp.White(' ').suppress() +
    channel.setResultsName('ch_q'),
    lambda match: IQChannel(**match)
    )

literal = number_literal ^ time_literal ^ phase_literal ^ channel_literal ^ iqchannel_literal ^ waveform_literal ^ iqwaveform_literal ^ boolean
literal.setDebug(False)

## COMMENTS ##
# Comments in xpulprog should start with a ";;" and continue until the end of
# a line.
comment = comment_start + pp.restOfLine

## VALUES ##
# In general, a value should be either an identifier (a non-keyword used to
# name variables) or a literal. We define patterns here to enforce that.
identifier = (~keyword + pp.Word(pp.alphas + "_", pp.alphanums + "_")).setParseAction(
    lambda s, loc, toks: Identifier(toks[0])
)
channel << (channel_literal | iqchannel_literal | identifier)
period = time_literal | identifier
phase = phase_literal | identifier
waveform = (waveform_literal | iqwaveform_literal | identifier)

## DEFINE STATEMENT ##
# The "define" statement allows for assigning a literal or identifier to an
# identifier, such that identifiers address variables.
define_statement = (
    define.suppress() +
    identifier.setResultsName('ident') + equals +
    (literal | identifier).setResultsName('value')
).setResultsName('define_statement')

## INCLUDE STATEMENT ##
# The "include" statement executes everything included from another file.
filename = string_literal.setResultsName("incl_file")
incl_statement = (include.suppress() + filename).setResultsName('incl_statement')

## DELAY STATEMENT ##
# The "delay" statement increments the global time counter `t`.
delay_statement = (delay.suppress() + period).setResultsName('delay_statement')

## PULSE EXPRESSIONS ##
# Pulse expressions can be used to form pulse sentences, and consist of either
# a shaped pulse, a delay, or a phase command.
shape = pp.Group(period.setResultsName('period') + colon.leaveWhitespace() + (waveform | boolean).leaveWhitespace().setResultsName('waveform'))
delay_expr = pp.Group(delay.suppress() + period.setResultsName('period'))
phase_expr = pp.Group(phase_kw.suppress() + phase.setResultsName('phase_value'))
pulse_expr = pp.delimitedList(delay_expr.setResultsName('delay_expr') | shape.setResultsName('shaped_pulse') | phase_expr.setResultsName('phase_expr'))

## PULSE STATEMENT ##
# A pulse statement is a list of pulse sentences, each of which is a pulse
# expression and a specification of which channels to pulse on.

channel_list = pp.delimitedList(channel)
channel_spec = pp.Group(channel.setParseAction(
    lambda s, loc, toks: toks[0]
) | (l_paren.suppress() + channel_list + r_paren.suppress()))
pulse_sentence = pp.Group(
    l_paren + pulse_expr.setResultsName('pulse_expr') + r_paren + colon + channel_spec.setResultsName('channel_spec')
)
pulse_statement = pp.delimitedList(pulse_sentence, delim=", ").setResultsName('pulse_statement')

## PRINT STATEMENT ##
print_statement = (print_kw.suppress() + (string_literal ^ literal ^ identifier).setResultsName('value')).setResultsName('print_statement')

## INCREMENT PHASE POINTERS (ipp) STATEMENT ##
ipp_statement = ipp_kw.setResultsName('ipp_statement')

## OPTION STATEMENT ##
# An option statement should look like ``option name = value``, where ``value``
# is a literal or identifier that will get converted accordingly.
option_statement = (
    option_kw +
    identifier.setResultsName('name') + equals +
    pp.Optional(pp.White(" ")) +
    (literal | identifier).setResultsName('value')
).setResultsName('option_statement')

## BLOCKS AND STATEMENT LISTS ##
block = l_brace + pp.Optional(pp.White(" \n")).suppress() + pp.Group(statement_list).setResultsName('block_contents') + r_brace

## REPEAT BLOCK STATEMENT ##
repeat_statement = (
    repeat_kw.suppress() + pp.Optional(pp.White(" ")) + integer_literal.setResultsName('how_many') + block
).setResultsName('repeat_statement')

## GENERAL STATEMENTS ##
blank_statement = pp.Group(pp.Optional(pp.White(" \t"))).setResultsName('blank_statement')
statement = \
    pp.Optional(pp.White(" ")).suppress() + \
    pp.Group(
        incl_statement |
        define_statement |
        delay_statement |
        pulse_statement |
        print_statement |
        ipp_statement |
        option_statement |
        repeat_statement | 
        blank_statement) + \
    pp.Optional(comment).suppress() + pp.LineEnd().suppress()


## START ##
statement_list << pp.OneOrMore(statement)#, delim=newline)
pulse_program = statement_list + pp.StringEnd()

## BASE VISITOR CLASS ##########################################################

class CompilationVisitor(object):
    """
    Base class for writing visitors that visit statements parsed by the
    compiler. By default, all visit methods do nothing, so that derived classes
    may override only the visit methods they care to implement.
    """

    def visit_pulseexpr(self, state, channels, t, n_samp, waveform, phase):
        """
        Called for every pulse expression in the XPP
        """
        pass
        
    def visit_option(self, state, opt_name, opt_value):
        """
        Called on every option statement in the XPP
        """
        pass
    
    def declare_final_options(self):
        """
        Called after the main compilation, but before post_compilation. 
        Returns a dictionary of options.
        """
        return {}
    
    def post_compilation(self, sample_rate, active_channels, extra_options, peripheral_id):
        """
        Called right before the compiler exits. Ties any loose ends up, ex.
        writes data to open files.
        """
        pass

## EXAMPLE VISITORS ############################################################

class PrintVisitor(CompilationVisitor):    
    """
    Example visitor that prints out a textual description of each pulse
    instruction, but does nothing further.
    """
    def visit_option(self, state, opt_name, opt_value):
        print "Setting option {} to {}.".format(opt_name, repr(opt_value))
        
    def visit_pulseexpr(self, state, channels, t, n_samp, waveform, phase):
        print "On channels {}):".format(", ".join(map(str, channels)))
        print "\tpulse at t == {} for {} samples with waveform {} and phase {}.".format(
            t, n_samp, waveform, phase
        )

## VISITORS FOR BUILD STEPS ####################################################

class WaveformBuilderVisitor(CompilationVisitor):
    """
    Visitor that builds a set of waveform files into a Velocia packet stream
    for streaming to an X6-1000M board.
    """
    def __init__(self, filename):
        self.filename = filename
        self.waveform_files = [tempfile.TemporaryFile(),
                          tempfile.TemporaryFile(),
                          tempfile.TemporaryFile(),
                          tempfile.TemporaryFile()]
        self.waveforms = {
                            "DA{}".format(idx):Waveform(f) 
                            for idx, f in enumerate(self.waveform_files)
                         }
        self._has_written = False
        
    def visit_pulseexpr(self, state, channels, t, n_samp, waveform, phase):
        for channel in channels:
            if channel.is_rx:
                # We don't build up a waveform for RX channels.
                continue
                
            if isinstance(channel, IQChannel):
                self._build_iq_channel(channel, n_samp, waveform, phase)
            else:
                if channel.analog:
                    self._build_analog_channel(channel, n_samp, waveform)
                else:
                    self._build_digital_channel(channel, n_samp)
    
    def _build_iq_channel(self, iqchannel, n_samp, iqwaveform, phase):
        # in this case append n_samp of data to each of the correct channels
        # in the iqchannel
        pin_name_i = iqchannel._ch_i._pin_name
        pin_name_q = iqchannel._ch_q._pin_name
        
        if not isinstance(iqwaveform, IQWaveform):
            raise ValueError("Expecting an IQWaveform on IQChannel {}, but recieved something else instead, of type {}.".format(str(iqchannel), type(iqwaveform)))
        
        rotated_iqwaveform = apply_phase(iqwaveform, phase)
        
        rewind_write(self.waveforms[pin_name_i], rotated_iqwaveform.waveform_i, n_samp)
        rewind_write(self.waveforms[pin_name_q], rotated_iqwaveform.waveform_q, n_samp)
        
        if n_samp > 0:
            self._has_written = True

    def _build_analog_channel(self, channel, n_samp, waveform):
        # in this case append n_samp of data to the correct DA channel
        pin_name = channel._pin_name
        if isinstance(waveform, IQWaveform):
            rewind_write(self.waveforms[pin_name], waveform.waveform_i, n_samp)
            warnings.warn("Received an IQWaveform instead of a Waveform on channel {}. Proceeding anyway using the I channel of the IQWaveform.".format(str(channel)))
        else:
            rewind_write(self.waveforms[pin_name], waveform, n_samp)
            
        if n_samp > 0:
            self._has_written = True
        
    
    def _build_digital_channel(self, channel, n_samp):
        # nothing to do here
        pass
    
    def declare_final_options(self):
        if self._has_written:
            return {
                'tx_play_from_file_enable': str(True),
                'tx_play_from_file_filename': os.path.basename(self.filename)
            }
        else:
            return {'tx_play_from_file_enable': str(False)}
    
    def post_compilation(self, sample_rate, active_channels, extra_options, peripheral_id):
        if self._has_written:
            # we need to convert the four channels into a single velo file
            waveform_to_velo(
                active_channels, 
                self.filename, 
                waveform0=self.waveforms['DA0'],
                waveform1=self.waveforms['DA1'],
                waveform2=self.waveforms['DA2'],
                waveform3=self.waveforms['DA3'], 
                peripheral_id=peripheral_id, 
                rewind=True
            )
        for f in self.waveform_files:
            f.close()
        
class PulseConfigurationVisitor(CompilationVisitor):
    """
    Visitor that builds a pulse configuration to be loaded by an instance of
    the `~x6.X6` driver class.
    """
    def __init__(self, pulse_file, pulse_name="Compiled Pulse"):
        self._pulse_file_name = pulse_file
        self._pulse_name = pulse_name
        self._pulse_config = cp.ConfigParser()
        
        # Initialize the pulse config from a string containing a dump
        # of the "template" configuration.
        pulse_template = pkgutil.get_data('x6', '_template.pulse')
        sio = cStringIO.StringIO(pulse_template)
        self._pulse_config.readfp(sio)
        self._ensure_section()
        
    def _ensure_section(self):
        if not self._pulse_config.has_section(self._pulse_name):
            self._pulse_config.add_section(self._pulse_name)
        
    def visit_option(self, state, opt_name, opt_value):
        self._pulse_config.set(self._pulse_name, opt_name, str(opt_value))
        
    def post_compilation(self, sample_rate, active_channels, extra_options, peripheral_id):
        self._pulse_config.set(self._pulse_name, 'tx_active_channels', ", ".join(map(str, active_channels)))
        self._pulse_config.set(self._pulse_name, 'sample_rate', str(sample_rate))
        for option, value in extra_options.items():
            self._pulse_config.set(self._pulse_name, option, value)
        
        with open(self._pulse_file_name, 'w') as f:
            self._pulse_config.write(f)      
            

class PRIPatternVisitor(CompilationVisitor):
    """
    Visitor that writes to a pair of PRI pattern files.
    """
    
    def __init__(self, rx_pattern_filename, tx_pattern_filename):
        self._rx_pattern = PRIPatternParser(rx_pattern_filename)
        self._tx_pattern = PRIPatternParser(tx_pattern_filename)
        
        self._has_set_rx_enable_pri = False
        self._has_set_tx_enable_pri = False
        
    def write(self):
        self._rx_pattern.write()
        self._tx_pattern.write()

    def visit_pulseexpr(self, state, channels, t, n_samp, waveform, phase):
        
        # this helper function writes a length n_samp pulse at time t
        # to the given pattern, deducing the correct pri code from the 
        # channel list
        def append_to_patterns(pattern, channel_list):
            if len(channel_list) > 0:
                pri_code = reduce(
                    lambda a, b: a | b,
                    [ch.pri_code for ch in channel_list]
                )
                if (pri_code, t, n_samp) not in pattern.get_all_pulses():
                    pattern.append_pulse(pri_code, t, n_samp)
        
        rx_channels = []
        tx_channels = []

        # sort the channels into rx and tx
        for channel in channels:
            if channel.is_rx:
                rx_channels.append(channel)
            else:
                tx_channels.append(channel)
           
        append_to_patterns(self._rx_pattern, rx_channels)
        append_to_patterns(self._tx_pattern, tx_channels)
        
    def visit_option(self, state, opt_name, opt_value):
        # keep track of whether or not the user has explictly enabled/disabled
        # pri in an option statement
        if opt_name == 'rx_enable_pri':
            self._has_set_rx_enable_pri = True
        if opt_name == 'tx_enable_pri':
            self._has_set_tx_enable_pri = True
            
    def declare_final_options(self):
        final_options = {
            'rx_pattern_file': os.path.basename(self._rx_pattern._filename),
            'tx_pattern_file': os.path.basename(self._tx_pattern._filename),
        }
        if not self._has_set_rx_enable_pri:
            final_options['rx_enable_pri'] = str(self._rx_pattern.get_array_size() > 0)
        if not self._has_set_tx_enable_pri:
            final_options['tx_enable_pri'] = str(self._tx_pattern.get_array_size() > 0)
        return final_options
        
    def post_compilation(self, sample_rate, active_channels, extra_options, peripheral_id):
        self.write()
        
class StateVisitor(CompilationVisitor):
    """
    Visitor that makes necessary changes to the state dictionary during
    compilation.
    """

    def visit_pulseexpr(self, state, channels, t, n_samp, waveform, phase):
        # loop through the channels in this sentence and retrieve
        # all the pin names
        channel_pins = []
        for channel in channels:
            if isinstance(channel, IQChannel):
                channel_pins.append(channel._ch_i._pin_name)
                channel_pins.append(channel._ch_q._pin_name)
            else:
                channel_pins.append(channel._pin_name)           
        
        # Finally, for each of the four DA channels, see if it is
        # being used in the current pulse sentence, and if it is,
        # set the corresponding value in active_channels to true.
        for idx, da_pin in enumerate(TX_CHANNELS[:4]):
            if da_pin in channel_pins:
                state['active_channels'][idx] = True
        
    def visit_option(self, state, opt_name, opt_value):
        # two options are given special treatment
        if opt_name == 'sample_rate':
            state['sample_rate'] = opt_value
        if opt_name == 'active_channels':
            state['override_active_channels'] = map(lambda x: x.strip() == 'True', opt_value.split(','))
        if opt_name == 'rx_enable_pri':
            state['override_rx_enable_pri'] = True
        if opt_name == 'tx_enable_pri':
            state['override_tx_enable_pri'] = True

        
class MultiVisitor(object):
    """
    Visitor that calls each of a sequence of other visitors in turn.
    """
    def __init__(self, *visitors):
        self._visitors = visitors
        
    def visit_option(self, state, opt_name, opt_value):
        for visitor in self._visitors:
            visitor.visit_option(state, opt_name, opt_value)
        
    def visit_pulseexpr(self, state, channels, t, n_samp, waveform, phase):
        for visitor in self._visitors:
            visitor.visit_pulseexpr(state, channels, t, n_samp, waveform, phase)
            
    def declare_final_options(self):
        options = {}
        # join together the options from all sub visitors
        for visitor in self._visitors:
            options = dict(visitor.declare_final_options().items() + options.items())
        return options
    
    def post_compilation(self, sample_rate, active_channels, extra_options, peripheral_id):
        """
        Runs a post compilation function on each visitor.
        """
        for visitor in self._visitors:
            visitor.post_compilation(sample_rate, active_channels, extra_options, peripheral_id)
            
def build_all_visitor(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        
    return MultiVisitor(
        PRIPatternVisitor(
            os.path.join(folder_name, 'rx.pattern'),
            os.path.join(folder_name, 'tx.pattern')
        ),
        WaveformBuilderVisitor(
            os.path.join(folder_name, 'waveform.velo')
        ),
        PulseConfigurationVisitor(
            os.path.join(folder_name, 'pulse.pulse')
        ),
        StateVisitor()
    )

## COMPILER ####################################################################

def compile_program(source, pulse_visitor, namespace=None, state=None, peripheral_id=0, is_include=False, debug=False):
    """
    Given an **xpulprog**-language source file, calls a `visitor`_
    for each pulse instruction in the compiled program. Most users will not
    run this function directly, but will use one of the higher-level compiler
    front-ends, such as `compile_to_directory`.
    
    :param str source: Source code for the pulse program to be compiled.
    :param CompilationVisitor pulse_visitor: A `visitor`_ that will observe
        pulse expressions, option statements, etc.
        See `~x6.pulprog.PrintVisitor` for an example.
    :param dict namespace: A mapping from `~x6.pulprog.Identifier` instances
        to values for each variable.
    :param dict state: Initial state of the compiler, containing zero or more
        of the keys ``t``, ``sample_rate``, ``active_channels`` and
        ``override_active_channels``.
    :param bool debug: If `True`, extra debugging information will be printed
        during compilation.
    
        
    .. _visitor: http://en.wikipedia.org/wiki/Visitor_pattern
    
    """

    if namespace is None:
        namespace = {}
    
    if debug == "return":
        stmts = []
    
    # We cannot modify, e.g.,  the local variable `t` from within the closure
    # below, so encapsulating it in a mutable datatype allows
    # for information to be shared across the closure boundary.
    if state is None:
        state = {}
    
    # declare the default state keys    
    if not state.has_key('t'):
        state['t'] = 0
    if not state.has_key('sample_rate'):
        state['sample_rate'] = None
    if not state.has_key('active_channels'):
        state['active_channels'] = [False] * 4
    if not state.has_key('override_active_channels'):
        state['override_active_channels'] = False
    
    # We force the user to declare the sample rate before performing 
    # any commands which require it
    def sample_rate():
        if state['sample_rate'] is None:
            raise ValueError('"sample_rate" was requested, but it has not been set yet. Use the "option" command in your program to set it.')
        else:
            return state['sample_rate']
            
    def active_channels():
        if state['override_active_channels']:
            return validate_active_channels(state['override_active_channels'])
        else:
            return validate_active_channels(state['active_channels'])
        
        
    # Defining our loop body as a function makes recursion easier. 
    def handle_single_statement(stmt):

        # Optionally print our or collect the statement
        # for debugging purposes.
        if debug is True:
            print stmt
        elif debug == "return":
            stmts.append(stmt)

        # Each kind of statement has a results name
        # associated, so that we can find out what statement
        # we got by querying that name.
        stmt_type = stmt.getName()
        
        # A statement without a name shouldn't occur,
        # but if it does, best to handle it with at most a warning.
        if stmt_type == None:
            warnings.warn("Nameless statement type handled; this may be a sign of an internal problem in pulprog.py.")
            pass

        # Handle include statements by recursively calling compile.            
        elif stmt_type == "incl_statement":
            incl_file = find_on_path(stmt.incl_file)
            if incl_file is None:
                raise IOError("Include file {} not found on sys.path.".format(incl_file))
            with open(incl_file, 'r') as f:
                incl_source = f.read()
                
            with u.working_directory(incl_file): # <- Sets the working directory
                                                 # for the next stmt only.
                compile_program(
                    incl_source, 
                    pulse_visitor, 
                    namespace=namespace, 
                    state=state, 
                    peripheral_id=peripheral_id, 
                    is_include=True,
                    debug=debug
                )

        # Defining a new variable or redefining an existing one
        # is quite straightforward; just throw it in the namespace dict.
        elif stmt_type == "define_statement":
            val = resolve_sym(stmt.value, namespace)
            if isinstance(val, Resolvable) and not val.resolved:
                val._resolve_(namespace)
            namespace[stmt.ident] = val

        # A delay is handled by incrementing the global time counter.
        elif stmt_type == "delay_statement":
            val = resolve_sym(stmt[0], namespace)
                
            if not isinstance(val, Time):
                raise TypeError("Delay periods must be times.")
                
            state['t'] += int(val._time * sample_rate())

        # Pulses are somewhat more complicated, and require us
        # to handle each pulse sentence in parallel as well as
        # to resolve the individual expressions within each sentence.
        elif stmt_type == "pulse_statement":

            # We will need to know how long this pulse statement
            # took so that the global time can be incremented accordingly.
            max_t = state['t']

            # Loop over sentences, making sure not to alter globals
            # until the end.
            for pulse_sentence in stmt:
                # Keep track of the time local to this sentence.
                local_t = state['t']
                
                # Unpack and resolve channel references.
                channels = map(
                            lambda sym: resolve_sym(sym, namespace), 
                            pulse_sentence.channel_spec
                              )
                
                # Enforce that channels cannot be mixed digital and analog.
                analog = [channel.analog for channel in channels]
                digital = [not x for x in analog]
                
                if not (all(analog) or all(digital)):
                    raise ValueError("Cannot mix digital and analog channels as outputs of a pulse sentence.")
                
                # Now we can consider each of the three kinds of pulse
                # expressions individually.
                # In practice, this is where most of the compilation logic will go.
                expr = pulse_sentence.pulse_expr
                # in case no phase was specified in the pulse sentence, we
                # set a default value here.
                cur_phase = (0, 1)
                for expr_part in expr:
                    if expr_part.getName() == "delay_expr":
                        n_samp = int(resolve_sym(expr_part.period, namespace)._time * sample_rate())
                        local_t += n_samp
                        
                    elif expr_part.getName() == "shaped_pulse":
                        n_samp = int(resolve_sym(expr_part.period, namespace)._time * sample_rate())
                        pulse_visitor.visit_pulseexpr(
                            state, channels, local_t, n_samp, resolve_sym(expr_part.waveform, namespace), cur_phase
                        )
                        local_t += n_samp
                        
                    elif expr_part.getName() == "phase_expr":
                        cur_phase = resolve_sym(expr_part.phase_value, namespace).cur
                        
                # If this pulse sentence was the longest, set max_t
                # accordingly.
                max_t = max(max_t, local_t)
                
            # Update the global time with the amount of time this
            # pulse statement took.
            state['t'] = max_t

        # Print statements are pretty basic.
        elif stmt_type == "print_statement":
            print resolve_sym(stmt.value, namespace)

        # To increment phases, we search the namespace for
        # phase lists and increment each individually.
        elif stmt_type == "ipp_statement":
            for val in namespace.values():
                if isinstance(val, PhaseList):
                    val.ipp()

        # Repeat statements are simple to handle; it's the grammar
        # that's tricky. We can now just loop over the statements in
        # the block and feed them to handle_single_statement
        # recursively.
        elif stmt_type == "repeat_statement":
            n_repeat = stmt.how_many
            for idx in xrange(n_repeat):
                for substmt in stmt.block_contents:
                    handle_single_statement(substmt)
                
        # Option statements are nearly directly handled by the visitor.
        elif stmt_type == "option_statement":
            opt_name = stmt.name.name # stmt.name is an Identifier.
            opt_value = resolve_sym(stmt.value, namespace)
            print "Debug: {}, {}".format(opt_name, opt_value)
            # If value is a Time, we must convert it.
            if isinstance(opt_value, Time):
                opt_value = int(opt_value._time * sample_rate())
            pulse_visitor.visit_option(state, opt_name, opt_value)
            
            
                
        # A blank statement should actually be ignored.
        # This will also match if the statement has only a
        # comment.
        elif stmt_type == "blank_statement":
            pass
        
        else:
            print "Statement type {} not handled.".format(stmt_type)
    
    
    # Actually parse the source now.
    if not is_include: print "[XPP Compiler] Compiling..."
    try:
        stmts = pulse_program.parseString(source)
    except pp.ParseException as ex:
        print 'Error parsing XPP source on line {}:\n\t"{}"'.format(ex.lineno, ex.line)
        raise ex
        
    for stmt in stmts:
        handle_single_statement(stmt)
    if not is_include: print "[XPP Compiler] Done compiling."
      
    # We now allow the visitor to declare any options it needs in
    # the post-compilation. This essentially allows a MultiVisitor to 
    # communicate between visitors to exchange filenames, etc.
    if not is_include:
        extra_options = pulse_visitor.declare_final_options()

    # Do any required post-compilation steps, but only for the main pulse
    # program, not for any included files
    if not is_include: 
        print "[XPP Compiler] Starting post compilation steps..."
        pulse_visitor.post_compilation(sample_rate(), active_channels(), extra_options, peripheral_id)
        print "[XPP Comiler] Done with post compilation."
        
    if debug == "return":
        return stmts
            
## COMPILER FRONT-ENDS #########################################################

def compile_to_directory(source_file, dirname, namespace=None, overwrite=True):
    """
    Compiles the XPP source in a given file to the directory given.
    
    :param source_file: File containing the xpulprog source to be compiled.
    :type source_file: `str` containing a path or `file`-like
    :param str dirname: Path to the output directory.
    :param dict namespace: A mapping from strings to values, such that
        ``namespace[name]`` specifies the initial value of the **xpulprog**
        variable ``name``.
    :param bool overwrite: If `True`, the output directory will be overwritten
        if it already exists. Otherwise, an exception will be raised if the
        output directory already exists.
    """

    # Make a namespace dictionary in the format we need it.
    namespace = mk_namespace_dict(namespace)
    
    # Check if the output directory already exists and overwrite it or
    # raise an exception if so, depending on the value of ``overwrite``.
    if os.path.exists(dirname):
        if overwrite:
            print "[XPP Compiler] Removing current contents of {}...".format(dirname)
            shutil.rmtree(dirname, ignore_errors=True)
        else:
            raise IOError("Folder already exists. Not overwriting.")
        
    # If we made it here, then the folder doesn't exist, so we can create
    # it with impunity.
    os.mkdir(dirname)
    
    # Load the source.
    if isinstance(source_file, str):
        source_file = open(source_file, 'r')
    try:
        source = "".join(source_file)
    finally:
        source_file.close()
        
    # Make and run the build_all_visitor to generate all of the consituant
    # files.
    ba_visitor = build_all_visitor(dirname)
    
    # Actually run the compiler with the given visitor.
    wd = source_file.name if hasattr(source_file, 'name') else os.getcwd()
    with u.working_directory(wd):
        compile_program(source, ba_visitor, namespace=namespace, debug=False)
    

def plot_pulprog(source_file, namespace=None):
    """
    Compiles the XPP source into a temporary directory, and then calls 
    `x6.pulplot.plot_compiled_folder` on this directory before deleting it.
    
    :param source_file: File containing the xpulprog source to be compiled.
    :type source_file: `str` containing a path or `file`-like
    :param dict namespace: A mapping from `~x6.pulprog.Identifier` instances
        to values for each variable.
    """
    compilation_directory = tempfile.mkdtemp()
    ba_visitor = build_all_visitor(compilation_directory)
    
    # the first bit of the hard work is done here
    compile_program(source_file, ba_visitor, namespace=namespace)
    
    # go out of our way to make sure to get the right pulse_name.
    pulse_name = 'Compiled Pulse'
    for visitor in ba_visitor._visitors:
        if isinstance(visitor, PulseConfigurationVisitor):
            pulse_name = visitor.pulse_name

    # the other half of the hard work is done here
    pulplot.plot_compiled_folder(compilation_directory, pulse_name)
