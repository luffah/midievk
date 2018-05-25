#!/usr/bin/python3
"""
midievk daemon
Require xdotool

# Copyright (C) 2018  luffah <luffah@runbox.com>
# Author: luffah <luffah@runbox.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import subprocess
import logging
from os.path import isfile
from midiev import MidiKeyboard, MIDITYPE, NOTEON, NOTEOFF, CONTROLLER
from midiev import CONTROLLER_VALUE, VELOCITY, CHANNEL
from options import usage, DEVICE, set_options, get_options
from options import CONFIG_FILE, CONFIG_FORMAT, CONFIG_LOADER
from options import OPTIONS
from options import NOTE_PRESSURE_MIDDLE_IDX, NOTE_PRESSURE_STRONG_IDX
from options import NOTE_PRESSURE_MIDDLE_DELTA, NOTE_PRESSURE_STRONG_DELTA
from options import CTL_DECREASING, CTL_INCREASING, NB_CTL_STEPS_IDX
from options import CTL_VALUE_MIDDLE_MIN_IDX, CTL_VALUE_MIDDLE_MAX_IDX
from interval import setInterval

ABS_DELTA = NOTEOFF

def split_ctl_value(ctlval):
    """split_ctl_value : return

    :param ctlval:
    """
    return int(round(ctlval * (OPTIONS[NB_CTL_STEPS_IDX]-1) / 127)) + 1

class MidiToXdo(object):

    """MidiToXdo"""

    def __init__(self):
        self.midikb = None
        # self._midi_key_chord = {} # table containing active keys
        self._midi_key_values = {} # table containing recents values
        self._midi_ctl_values = {} # table containing recents values for controllers
        self._midi_values = {} # table containing config

    def set_midi_device(self, midikb):
        """set_midi_device

        :param midikb:
        """
        self.midikb = midikb

    def insert(self, key, values):
        """insert

        :param key:
        :param values:
        """
        self._midi_values[key] = values

    def has_key(self, key):
        """has_key

        :param key:
        """
        return key in self._midi_values

    def set_keybind(self, key, keybind):
        """set_keybind

        :param key:
        :param keybind:
        """
        self._midi_values[key]['keybind'] = keybind

    def get_key_type(self, key):
        """get_key_type

        :param key:
        """
        if key in self._midi_values:
            return self._midi_values[key]['type']
        return None

    def set_key_type(self, key, val):
        """set_key_type

        :param key:
        :param val:
        """
        if key in self._midi_values:
            self._midi_values[key]['type'] = val

    def get_key_mode(self, key):
        """get_key_mode

        :param key:
        """
        if key in self._midi_values:
            return self._midi_values[key]['mode']
        return None

    def set_key_mode(self, key, val):
        """set_key_type

        :param key:
        :param val:
        """
        if key in self._midi_values:
            self._midi_values[key]['mode'] = val

    def read_configs(self,
                     file_format=CONFIG_FORMAT,
                     file_name=CONFIG_FILE,
                     config_line_process=None
                    ):
        """read_configs

        :param file_format:
        :param file_name:
        :param config_line_process:
        """
        if isfile(file_name):
            try:
                with open(file_name, "r") as config:
                    options = CONFIG_LOADER[file_format].load(config)
                    set_options(options)
                    if 'keytable' in options:
                        for hexkey in options['keytable']:
                            values = options['keytable'][hexkey]
                            key = int(hexkey, 16)
                            if not 'type' in values or not 'channel' in values:
                                continue
                            if not 'keybind' in values:
                                values['keybind'] = None
                            if not 'mode' in values:
                                values['mode'] = 0
                            self.insert(key, values)
                            if config_line_process:
                                config_line_process(key, self._midi_values[key])
            except BufferError:
                print "error while parsing %s" % file_name
            print "using config %s" % file_name
        else:
            print "%s not found" % file_name
        return len(self._midi_values) > 0

    def save_configs(self, file_format=CONFIG_FORMAT, file_name=CONFIG_FILE):
        """save_configs

        :param file_format:
        :param file_name:
        """
        if file_format in CONFIG_LOADER:
            options = get_options()
            keytable = {}
            for (hexkey, values) in self._midi_values.iteritems():
                keytable[hex(hexkey)] = values
            options['keytable'] = keytable
            with open(file_name, "w") as config:
                CONFIG_LOADER[file_format].dump(
                    options, config, sort_keys=True, indent=4)

    def send_keystroke(self, midikey, hexkey):
        """send_keystroke

        :param midikey: MIDI input
        :param hexkey: key to access to keybind
        :param keyini: key type
        """
        # print (midikey,hexkey,keyini)
        keyevt = None
        key = hexkey
        channel = midikey[CHANNEL]

        keytype = (
            midikey[MIDITYPE] - (ABS_DELTA if self.get_key_mode(key) else 0)
        )

        if keytype in [(NOTEOFF - ABS_DELTA), (NOTEON - ABS_DELTA), CONTROLLER]:
            keyevt = "key"

        elif keytype == NOTEOFF:
            if channel in self._midi_key_values:
                key = self._midi_key_values.pop(channel, None)
                keyevt = "keyup"

        elif keytype == NOTEON:
            if channel not in self._midi_key_values:
                keyevt = "keydown"
                self._midi_key_values[channel] = key

        elif keytype == (CONTROLLER - ABS_DELTA):
            if OPTIONS[NB_CTL_STEPS_IDX] != 0:
                # begin to release existing key if exist
                if channel in self._midi_ctl_values:
                    prevkeybind = self._midi_ctl_values[channel]
                    keyevt = "keyup"
                    if prevkeybind is not None:
                        subprocess.Popen(["xdotool", keyevt, prevkeybind])

                keyevt = "keydown"
                keybind = self._midi_values[key]['keybind']
                self._midi_ctl_values[key] = keybind
            else:
                # The following complicated operations just find
                # the key reference registered for increasing and
                # decreasing.
                # Given it does not need to be recomputed as many as
                # a controler used in relative mode (here the pot
                # only have to be on negative side to simulate
                # keydown for a decreasing key).
                if channel in self._midi_ctl_values:
                    if (
                            midikey[VELOCITY] >= OPTIONS[CTL_VALUE_MIDDLE_MIN_IDX] and
                            midikey[VELOCITY] <= OPTIONS[CTL_VALUE_MIDDLE_MAX_IDX]
                        ):
                        # Neutral - > release a previous key
                        key = self._midi_ctl_values.pop(channel, None)
                        keyevt = "keyup"
                else:
                    keyevt = "keydown"
                    if midikey[VELOCITY] < OPTIONS[CTL_VALUE_MIDDLE_MIN_IDX]:
                        # Negative -> continuously press key for decrease
                        key = (key % (1<< 12))| CTL_DECREASING << 12
                        self._midi_ctl_values[channel] = key
                    elif midikey[VELOCITY] > OPTIONS[CTL_VALUE_MIDDLE_MAX_IDX]:
                        # Positive - > continuously press key for increase
                        key = (key % (1<< 12))| CTL_INCREASING << 12
                        self._midi_ctl_values[channel] = key
                    else:
                        return


        # print(keyevt, key)
        if keyevt:
            if key in self._midi_values:
                keybind = self._midi_values[key]['keybind']
                if keybind is not None:
                    subprocess.Popen(
                        ["xdotool", keyevt, keybind])

    def parse_midi(self):
        """parse_midi"""
        command = self.midikb.read()
        if not command:
            return (None, None)
        # Only pay attention to 0x9X Note on and 0xBX Continuous controller
        miditype = command[MIDITYPE]
        channel = command[CHANNEL]
        hexcode = None

        if miditype == NOTEOFF:
            hexcode = (NOTEOFF << 4 | channel)
        elif miditype == NOTEON:
            vel = command[VELOCITY]
            if vel == 0:
                hexcode = (NOTEOFF << 4 | channel)
                command[MIDITYPE] = NOTEOFF
            else:
                hexcode = (NOTEON << 4 | channel)
                if vel > OPTIONS[NOTE_PRESSURE_MIDDLE_IDX]:
                    if vel > OPTIONS[NOTE_PRESSURE_STRONG_IDX]:
                        hexcode = hexcode | NOTE_PRESSURE_STRONG_DELTA << 12
                    else:
                        hexcode = hexcode | NOTE_PRESSURE_MIDDLE_DELTA << 12
        elif miditype == CONTROLLER:
            hexcode = (CONTROLLER << 4 | channel)
            ctlval = command[CONTROLLER_VALUE]
            if OPTIONS[NB_CTL_STEPS_IDX] != 0:
                val = split_ctl_value(ctlval)
                hexcode = (hexcode | (val << 12))
            else:
                nhexcode = None
                if ctlval == 0:
                    nhexcode = hexcode | CTL_DECREASING << 12
                elif ctlval == 127:
                    nhexcode = hexcode | CTL_INCREASING << 12
                elif hexcode in self._midi_ctl_values:
                    prevctlval = self._midi_ctl_values[hexcode]
                    if ctlval == prevctlval:
                        nhexcode = hexcode
                    elif ctlval < prevctlval:
                        nhexcode = hexcode | CTL_DECREASING << 12
                    else:
                        nhexcode = (hexcode << 1) | CTL_INCREASING
                self._midi_ctl_values[hexcode] = ctlval
                hexcode = nhexcode
        return (command, hexcode)

    @setInterval(.0001)
    def loop_midi_device(self):
        """loop_midi_device"""
        command = None
        if self.midikb:
            if not self.midikb.is_running():
                print DEVICE + " is not running"
                return
        else:
            print "Midi device disappeared"
            exit()
        (command, hexcode) = self.parse_midi()
        if hexcode is not None:
            self.send_keystroke(command, hexcode)
            logging.debug('Key: %s %s', command, hex(hexcode))

    def on_closing(self):
        """on_closing"""
        logging.debug('User want to close the app')
        self.midikb.stop_thread()
        logging.debug('Thanks for using this app :)')



def main():
    """main"""
    midixdo = MidiToXdo()
    if midixdo.read_configs():
        midilistener = MidiKeyboard(DEVICE)
        midixdo.set_midi_device(midilistener)
        midixdo.loop_midi_device()
        while raw_input() is not 'q':
            pass

if __name__ == '__main__':
    if DEVICE and CONFIG_FILE:
        main()
    else:
        usage()
