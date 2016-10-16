# -*- coding: utf-8 -*-
import struct
import os
import atexit
from time import time as now
from threading import Thread
from glob import glob
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

event_bin_format = 'llHHI'

# Taken from include/linux/input.h
# https://www.kernel.org/doc/Documentation/input/event-codes.txt
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03
EV_MSC = 0x04

class EventDevice(object):
    def __init__(self, path):
        self.path = path
        self._input_file = None
        self._output_file = None

    @property
    def input_file(self):
        if self._input_file is None:
            try:
                self._input_file = open(self.path, 'rb')
            except IOError as e:
                if e.strerror == 'Permission denied':
                    print('Permission denied ({}). You must be sudo to access global events.'.format(self.path))
                    exit()

            def try_close():
                try:
                    self._input_file.close
                except:
                    pass
            atexit.register(try_close)
        return self._input_file

    @property
    def output_file(self):
        if self._output_file is None:
            self._output_file = open(self.path, 'wb')
            atexit.register(self._output_file.close)
        return self._output_file

    def read_event(self):
        data = self.input_file.read(struct.calcsize(event_bin_format))
        seconds, microseconds, type, code, value = struct.unpack(event_bin_format, data)
        return (seconds + microseconds / 1e6, type, code, value)

    def write_event(self, type, code, value):
        integer, fraction = divmod(now(), 1)
        seconds = int(integer)
        microseconds = int(fraction * 1e6)
        data_event = struct.pack(event_bin_format, seconds, microseconds, type, code, value)

        # Send a sync event to ensure other programs update.
        sync_event = struct.pack(event_bin_format, seconds, microseconds, EV_SYN, 0, 0)

        self.output_file.write(data_event + sync_event)
        self.output_file.flush()

class AggregatedEventDevice(object):
    def __init__(self, devices):
        self.event_queue = Queue()
        self.devices = devices
        def start_reading(device):
            while True:
                self.event_queue.put(device.read_event())
        for device in self.devices:
            thread = Thread(target=start_reading, args=[device])
            thread.setDaemon(True)
            thread.start()

    def read_event(self):
        return self.event_queue.get(block=True)

    def write_event(self, type, code, value):
        self.devices[0].write_event(type, code, value)

import re
from collections import namedtuple
DeviceDescription = namedtuple('DeviceDescription', 'event_file is_mouse is_keyboard')
device_pattern = r"""N: Name="([^"]+?)".+?H: Handlers=([^\n]+)"""
def list_devices_from_proc(type_name):
    try:
        with open('/proc/bus/input/devices') as f:
            description = f.read()
    except FileNotFoundError:
        return

    devices = {}
    for name, handlers in re.findall(device_pattern, description, re.DOTALL):
        path = '/dev/input/event' + re.search(r'event(\d+)', handlers).group(1)
        if type_name in handlers:
            yield EventDevice(path)

def list_devices_from_by_id(type_name):
    for path in glob('/dev/input/by-id/*-event-' + type_name):
        yield EventDevice(path)

def aggregate_devices(type_name):
    # We don't aggregate devices from different sources to avoid
    # duplicates.

    devices_from_by_id = list(list_devices_from_by_id(type_name))
    if devices_from_by_id:
        return AggregatedEventDevice(devices_from_by_id)

    devices_from_proc = list(list_devices_from_proc(type_name))
    if devices_from_proc:
        return AggregatedEventDevice(devices_from_proc)

    raise ValueError('No {0} device found in /proc/bus/input/devices or /dev/input/by-id/*-event-{0}'.format(type_name))


def ensure_root():
    if os.geteuid() != 0:
        raise ImportError('You must be root to use this library on linux.')
