#!/usr/bin/python3
"""
midievk midi listener

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
# Requiere xdotool, python3-tk
import threading
import logging
import sys
import queue
from interval import setInterval
from options import usage, DEVICE, STATS


# event types
NOTEOFF = 0x80
NOTEON = 0x90
AFTERTOUCH = 0xA0
CONTROLLER = 0xB0
PRESSURE = 0xD0
PATCHCHANGE = 0xC0
PITCHBEND = 0xE0
# (non-musical commands = 0xF0

# event values indexes
MIDITYPE = 0
INSTRUMENT = 1
CHANNEL = 1
VELOCITY = 2
CONTROLLER_VALUE = 2
LSB = 1 #7bits
MSB = 2 #7bits


class MidiKeyboard(object):
    """MidiKeyboard"""
    miditable = {
        # cmd  parameters
        # ----+--------------
        NOTEOFF:2,#TYPE, CHANNEL, VELOCITY,
        NOTEON:2,#TYPE, CHANNEL, VELOCITY,
        AFTERTOUCH:2,#TYPE, CHANNEL, VALUE,
        CONTROLLER:2,#TYPE, CHANNEL, VALUE,
        PATCHCHANGE:1,#TYPE, INSTRUMENT,
        PRESSURE:1,#TYPE, VALUE,
        PITCHBEND:2,#TYPE, LSB, MSB
    }
    event_desc = {
        # cmd  parameters
        # ----+--------------
        NOTEOFF:'Note-off',
        NOTEON:'Note-on',
        AFTERTOUCH:'Aftertouch',
        CONTROLLER:'Controller',
        PATCHCHANGE:'Path change',
        PRESSURE:'Pressure',
        PITCHBEND:'Pitch bend'
    }

    def __init__(self, device=None):
        self._device = None
        self._device_pipe = None
        self._running = threading.Event()
        self._queue = queue.Queue()
        if device is not None:
            print 'listen %s' % device
            self.set_device(device)
            self.start_thread()

    def start_thread(self):
        """start_thread

        :param device:
        """
        if self._device is None:
            raise Exception('No device defined')
        try:
            self._thread = threading.Thread(
                target=self._read_device,
                args=())
            self._thread.setDaemon(True)
            self._thread.start()
        except NameError:
            print("Variable ?", sys.exc_info()[2])
        except BufferError:
            print("Exception on reading", sys.exc_info()[2])

    def stop_thread(self):
        """stop_thread"""
        logging.info('Stop midi-thread request')
        try:
            if self._running.is_set():
                # self._device_pipe.kill()
                # self._device_pipe.stdout.close()
                self._running.clear()
                logging.debug('I set running flag off.')
                self._thread.join(1)
                logging.debug('I close pipe.')
                self._device_pipe.close()
                logging.debug('Midi-thread is closed.')
        except:
                logging.debug('Some thread had been engraved alive.')

    def _read_data_with_values(self, data, message):
        midiinput = self._device_pipe
        if data >= 0x80:
            message.append(data)
            if data in self.miditable:
                expected_len = self.miditable[data]
                message.append(ord(midiinput.read(1)))
                if expected_len == 2:
                    message.append(ord(midiinput.read(1)))
                    if STATS:
                        reg_stat(message)
                self._queue.put(message)
            else:
                expected_len = 0


    def _read_device(self):
        """_read_device """
        # self._device_pipe = open(self._device, 'rb') # a?
        # self._device_pipe = subprocess.Popen(['cat', device],
        # stdout=subprocess.PIPE, bufsize=0)
        self._running.set()
        # with self._device_pipe.stdout as f:
        # with self._device_pipe as f:
        try:
            with open(self._device, 'rb') as midiinput:
                self._device_pipe = midiinput
                try:
                    data = None
                    message = None
                    while self._running.is_set():
                        message = []
                        data = ord(midiinput.read(1))
                        self._read_data_with_values(data, message)

                except BufferError:
                    if data is not None:
                        logging.error(
                            "Midi message not understood: %s - %s",
                            hex(data), message)
                    else:
                        logging.error("Midi message was NONE")
                    exit()
        except IOError:
            logging.error("Device not found: %s ", self._device)


    def read(self):
        """read"""
        try:
            return self._queue.get(False)
        except queue.Empty:
            return False

    def is_running(self):
        """is_running"""
        return self._running.is_set()

    def set_device(self, device=None):
        """set_device

        :param device:
        """
        if device is not None:
            self._device = device

    # def setlight(self, note, status):
        # coord = where['coordinate']
        # x = ascii_lowercase.index(coord[0])
        # message = 'note_on' if status else 'note_off'
        # self._device_pipe.write(message)

    # def send_midi(self, midi):
        # a, b, c = midi.split(" ")
        # subprocess.call("echo -ne '\\x"+a+"\\x"+b+"\\x"+c+"' > /dev/midi", shell=True)
        # with open(device, 'ab') as
        # self._device_pipe = subprocess.Popen(
        # cat    ['cat', device],
            # stdout=device, bufsize=0)
        # print("\033[0;31m: "+midi+"\033[0m")


class MidiView(object):
    """MidiView"""
    midikb = None
    failcnt = 0

    def connect_to_device(self, dev):
        """connect_to_device

        :param dev:
        """
        self.midikb = MidiKeyboard(dev)

    @setInterval(.0001)
    def check_midi_device(self):
        """check_midi_device"""
        if self.midikb:
            if self.midikb.is_running():
                command = self.midikb.read()
                if command:
                    print 'Event:  %s' % command
        else:
            print "Midi device disappeared"
            exit()


STATISTICS = {}
def reg_stat(message):
    """reg_stat

    :param message: [message type, channel, value]
    """
    data = message[0]
    channel = message[1]
    if data in STATISTICS:
        if channel in STATISTICS[data]:
            STATISTICS[data][channel].append(message[2])
        else:
            STATISTICS[data][channel] = [message[2]]
    else:
        STATISTICS[data] = {channel:[message[2]]}


def show_stats():
    """show_stats"""
    template = "{0:<14s} {1:<8s} {2:<8s} {3:<8s} {4:<8s}"
    print template.format("Type", "Channel", "Value", "", "")
    print template.format("", "", "(min)", "(mean)", "(max)")
    print template.format("----", "-------", "-----", "-----", "-----")
    for (keytype, channel_values) in STATISTICS.items():
        for (channel, values) in channel_values.items():
            print template.format(
                MidiKeyboard.event_desc[keytype],
                str(channel),
                str(min(values)),
                str(sum(values)/len(values)),
                str(max(values))
                )

def main():
    """main"""
    midiobserver = MidiView()
    midiobserver.connect_to_device(DEVICE)
    midiobserver.check_midi_device()
    while raw_input() is not 'q':
        pass
    if STATS:
        show_stats()


if __name__ == '__main__':
    if DEVICE:
        main()
    else:
        usage()
