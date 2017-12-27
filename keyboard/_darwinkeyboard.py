import ctypes
import ctypes.util
import Quartz
import time
import os
import threading
from AppKit import NSEvent
from ._keyboard_event import KeyboardEvent, KEY_DOWN, KEY_UP, normalize_name

try: # Python 2/3 compatibility
    unichr
except NameError:
    unichr = chr

Carbon = ctypes.cdll.LoadLibrary(ctypes.util.find_library('Carbon'))

class KeyMap(object):
    non_layout_keys = dict((vk, normalize_name(name)) for vk, name in {
        # Layout specific keys from https://stackoverflow.com/a/16125341/252218
        # Unfortunately no source for layout-independent keys was found.
        0x24: 'return',
        0x30: 'tab',
        0x31: 'space',
        0x33: 'backspace',
        0x35: 'escape',
        0x37: 'command',
        0x38: 'shift',
        0x39: 'capslock',
        0x3a: 'option',
        0x3b: 'control',
        0x3c: 'right shift',
        0x3d: 'right option',
        0x3e: 'right control',
        0x3f: 'function',
        0x40: 'f17',
        0x48: 'volume up',
        0x49: 'volume down',
        0x4a: 'mute',
        0x4f: 'f18',
        0x50: 'f19',
        0x5a: 'f20',
        0x60: 'f5',
        0x61: 'f6',
        0x62: 'f7',
        0x63: 'f3',
        0x64: 'f8',
        0x65: 'f9',
        0x67: 'f11',
        0x69: 'f13',
        0x6a: 'f16',
        0x6b: 'f14',
        0x6d: 'f10',
        0x6f: 'f12',
        0x71: 'f15',
        0x72: 'help',
        0x73: 'home',
        0x74: 'page up',
        0x75: 'delete',
        0x76: 'f4',
        0x77: 'end',
        0x78: 'f2',
        0x79: 'page down',
        0x7a: 'f1',
        0x7b: 'left',
        0x7c: 'right',
        0x7d: 'down',
        0x7e: 'up',
    }.items())
    layout_specific_keys = {}
    def __init__(self):
        # Virtual key codes are usually the same for any given key, unless you have a different
        # keyboard layout. The only way I've found to determine the layout relies on (supposedly
        # deprecated) Carbon APIs. If there's a more modern way to do this, please update this
        # section.

        # Set up data types and exported values:

        CFTypeRef = ctypes.c_void_p
        CFDataRef = ctypes.c_void_p
        CFIndex = ctypes.c_uint64
        OptionBits = ctypes.c_uint32
        UniCharCount = ctypes.c_uint8
        UniChar = ctypes.c_uint16
        UniChar4 = UniChar * 4

        class CFRange(ctypes.Structure):
            _fields_ = [('loc', CFIndex),
                        ('len', CFIndex)]

        kTISPropertyUnicodeKeyLayoutData = ctypes.c_void_p.in_dll(Carbon, 'kTISPropertyUnicodeKeyLayoutData')
        shiftKey = 0x0200
        alphaKey = 0x0400
        optionKey = 0x0800
        controlKey = 0x1000
        kUCKeyActionDisplay = 3
        kUCKeyTranslateNoDeadKeysBit = 0

        # Set up function calls:
        Carbon.CFDataGetBytes.argtypes = [CFDataRef] #, CFRange, UInt8
        Carbon.CFDataGetBytes.restype = None
        Carbon.CFDataGetLength.argtypes = [CFDataRef]
        Carbon.CFDataGetLength.restype = CFIndex
        Carbon.CFRelease.argtypes = [CFTypeRef]
        Carbon.CFRelease.restype = None
        Carbon.LMGetKbdType.argtypes = []
        Carbon.LMGetKbdType.restype = ctypes.c_uint32
        Carbon.TISCopyCurrentKeyboardInputSource.argtypes = []
        Carbon.TISCopyCurrentKeyboardInputSource.restype = ctypes.c_void_p
        Carbon.TISGetInputSourceProperty.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        Carbon.TISGetInputSourceProperty.restype = ctypes.c_void_p
        Carbon.UCKeyTranslate.argtypes = [ctypes.c_void_p,
                                          ctypes.c_uint16,
                                          ctypes.c_uint16,
                                          ctypes.c_uint32,
                                          ctypes.c_uint32,
                                          OptionBits,      # keyTranslateOptions
                                          ctypes.POINTER(ctypes.c_uint32), # deadKeyState
                                          UniCharCount,    # maxStringLength
                                          ctypes.POINTER(UniCharCount), # actualStringLength
                                          UniChar4]
        Carbon.UCKeyTranslate.restype = ctypes.c_uint32

        # Get keyboard layout
        klis = Carbon.TISCopyCurrentKeyboardInputSource()
        k_layout = Carbon.TISGetInputSourceProperty(klis, kTISPropertyUnicodeKeyLayoutData)
        k_layout_size = Carbon.CFDataGetLength(k_layout)
        k_layout_buffer = ctypes.create_string_buffer(k_layout_size) # TODO - Verify this works instead of initializing with empty string
        Carbon.CFDataGetBytes(k_layout, CFRange(0, k_layout_size), ctypes.byref(k_layout_buffer))

        # Generate character representations of key codes
        for key_code in range(0, 128):
            # TODO - Possibly add alt modifier to key map
            non_shifted_char = UniChar4()
            shifted_char = UniChar4()
            keys_down = ctypes.c_uint32()
            char_count = UniCharCount()

            retval = Carbon.UCKeyTranslate(k_layout_buffer,
                                           key_code,
                                           kUCKeyActionDisplay,
                                           0, # No modifier
                                           Carbon.LMGetKbdType(),
                                           kUCKeyTranslateNoDeadKeysBit,
                                           ctypes.byref(keys_down),
                                           4,
                                           ctypes.byref(char_count),
                                           non_shifted_char)

            non_shifted_key = u''.join(unichr(non_shifted_char[i]) for i in range(char_count.value))

            retval = Carbon.UCKeyTranslate(k_layout_buffer,
                                           key_code,
                                           kUCKeyActionDisplay,
                                           shiftKey >> 8, # Shift
                                           Carbon.LMGetKbdType(),
                                           kUCKeyTranslateNoDeadKeysBit,
                                           ctypes.byref(keys_down),
                                           4,
                                           ctypes.byref(char_count),
                                           shifted_char)

            shifted_key = u''.join(unichr(shifted_char[i]) for i in range(char_count.value))

            self.layout_specific_keys[key_code] = (non_shifted_key, shifted_key)
        # Cleanup
        Carbon.CFRelease(klis)

    def character_to_vk(self, character):
        """ Returns a tuple of (scan_code, modifiers) where ``scan_code`` is a numeric scan code
        and ``modifiers`` is an array of string modifier names (like 'shift') """
        # Mapping to preserve cross-platform hotkeys
        if character.lower() == "windows":
            character = "command"

        for vk in self.non_layout_keys:
            if self.non_layout_keys[vk] == character.lower():
                return (vk, [])
        for vk in self.layout_specific_keys:
            if self.layout_specific_keys[vk][0] == character:
                return (vk, [])
            elif self.layout_specific_keys[vk][1] == character:
                return (vk, ['shift'])
        raise ValueError("Unrecognized character: {}".format(character))

    def vk_to_character(self, vk, modifiers=[]):
        """ Returns a character corresponding to the specified scan code (with given
        modifiers applied) """
        if vk in self.non_layout_keys:
            # Not a character
            return self.non_layout_keys[vk]
        elif vk in self.layout_specific_keys:
            if 'shift' in modifiers:
                return self.layout_specific_keys[vk][1]
            return self.layout_specific_keys[vk][0]
        else:
            # Invalid vk
            raise ValueError("Invalid scan code: {}".format(vk))


class KeyController(object):
    def __init__(self):
        self.key_map = KeyMap()
        self.current_modifiers = {
            "shift": False,
            "caps": False,
            "alt": False,
            "ctrl": False,
            "cmd": False,
        }
        self.media_keys = {
            'KEYTYPE_SOUND_UP': 0,
            'KEYTYPE_SOUND_DOWN': 1,
            'KEYTYPE_BRIGHTNESS_UP': 2,
            'KEYTYPE_BRIGHTNESS_DOWN': 3,
            'KEYTYPE_CAPS_LOCK': 4,
            'KEYTYPE_HELP': 5,
            'POWER_KEY': 6,
            'KEYTYPE_MUTE': 7,
            'UP_ARROW_KEY': 8,
            'DOWN_ARROW_KEY': 9,
            'KEYTYPE_NUM_LOCK': 10,
            'KEYTYPE_CONTRAST_UP': 11,
            'KEYTYPE_CONTRAST_DOWN': 12,
            'KEYTYPE_LAUNCH_PANEL': 13,
            'KEYTYPE_EJECT': 14,
            'KEYTYPE_VIDMIRROR': 15,
            'KEYTYPE_PLAY': 16,
            'KEYTYPE_NEXT': 17,
            'KEYTYPE_PREVIOUS': 18,
            'KEYTYPE_FAST': 19,
            'KEYTYPE_REWIND': 20,
            'KEYTYPE_ILLUMINATION_UP': 21,
            'KEYTYPE_ILLUMINATION_DOWN': 22,
            'KEYTYPE_ILLUMINATION_TOGGLE': 23
        }
    
    def press(self, key_code):
        """ Sends a 'down' event for the specified scan code """
        if key_code >= 128:
            # Media key
            ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                14, # type
                (0, 0), # location
                0xa00, # flags
                0, # timestamp
                0, # window
                0, # ctx
                8, # subtype
                ((key_code-128) << 16) | (0xa << 8), # data1
                -1 # data2
            )
            Quartz.CGEventPost(0, ev.CGEvent())
        else:
            # Regular key
            # Apply modifiers if necessary
            event_flags = 0
            if self.current_modifiers["shift"]:
                event_flags += Quartz.kCGEventFlagMaskShift
            if self.current_modifiers["caps"]:
                event_flags += Quartz.kCGEventFlagMaskAlphaShift
            if self.current_modifiers["alt"]:
                event_flags += Quartz.kCGEventFlagMaskAlternate
            if self.current_modifiers["ctrl"]:
                event_flags += Quartz.kCGEventFlagMaskControl
            if self.current_modifiers["cmd"]:
                event_flags += Quartz.kCGEventFlagMaskCommand
            
            # Update modifiers if necessary
            if key_code == 0x37: # cmd
                self.current_modifiers["cmd"] = True
            elif key_code == 0x38: # shift
                self.current_modifiers["shift"] = True
            elif key_code == 0x39: # caps lock
                self.current_modifiers["caps"] = True
            elif key_code == 0x3A: # alt
                self.current_modifiers["alt"] = True
            elif key_code == 0x3B: # ctrl
                self.current_modifiers["ctrl"] = True
            event = Quartz.CGEventCreateKeyboardEvent(None, key_code, True)
            Quartz.CGEventSetFlags(event, event_flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            time.sleep(0.01)

    def release(self, key_code):
        """ Sends an 'up' event for the specified scan code """
        if key_code >= 128:
            # Media key
            ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                14, # type
                (0, 0), # location
                0xb00, # flags
                0, # timestamp
                0, # window
                0, # ctx
                8, # subtype
                ((key_code-128) << 16) | (0xb << 8), # data1
                -1 # data2
            )
            Quartz.CGEventPost(0, ev.CGEvent())
        else:
            # Regular key
            # Update modifiers if necessary
            if key_code == 0x37: # cmd
                self.current_modifiers["cmd"] = False
            elif key_code == 0x38: # shift
                self.current_modifiers["shift"] = False
            elif key_code == 0x39: # caps lock
                self.current_modifiers["caps"] = False
            elif key_code == 0x3A: # alt
                self.current_modifiers["alt"] = False
            elif key_code == 0x3B: # ctrl
                self.current_modifiers["ctrl"] = False

            # Apply modifiers if necessary
            event_flags = 0
            if self.current_modifiers["shift"]:
                event_flags += Quartz.kCGEventFlagMaskShift
            if self.current_modifiers["caps"]:
                event_flags += Quartz.kCGEventFlagMaskAlphaShift
            if self.current_modifiers["alt"]:
                event_flags += Quartz.kCGEventFlagMaskAlternate
            if self.current_modifiers["ctrl"]:
                event_flags += Quartz.kCGEventFlagMaskControl
            if self.current_modifiers["cmd"]:
                event_flags += Quartz.kCGEventFlagMaskCommand
            event = Quartz.CGEventCreateKeyboardEvent(None, key_code, False)
            Quartz.CGEventSetFlags(event, event_flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            time.sleep(0.01)

    def map_char(self, character):
        if character in self.media_keys:
            return (128+self.media_keys[character],[])
        else:
            return self.key_map.character_to_vk(character)
    def map_scan_code(self, scan_code):
        if scan_code >= 128:
            character = [k for k, v in enumerate(self.media_keys) if v == scan_code-128]
            if len(character):
                return character[0]
            return None
        else:
            return self.key_map.vk_to_character(scan_code)

class KeyEventListener(object):
    def __init__(self, callback, blocking=False):
        self.blocking = blocking
        self.callback = callback
        self.listening = True
        self.tap = None

    def run(self):
        """ Creates a listener and loops while waiting for an event. Intended to run as
        a background thread. """
        self.tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown) |
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyUp) |
            Quartz.CGEventMaskBit(Quartz.kCGEventFlagsChanged),
            self.handler,
            None)
        loopsource = Quartz.CFMachPortCreateRunLoopSource(None, self.tap, 0)
        loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(loop, loopsource, Quartz.kCFRunLoopDefaultMode)
        Quartz.CGEventTapEnable(self.tap, True)

        while self.listening:
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 5, False)

    def handler(self, proxy, e_type, event, refcon):
        scan_code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        key_name = name_from_scancode(scan_code)
        flags = Quartz.CGEventGetFlags(event)
        event_type = ""
        is_keypad = (flags & Quartz.kCGEventFlagMaskNumericPad)
        if e_type == Quartz.kCGEventKeyDown:
            event_type = "down"
        elif e_type == Quartz.kCGEventKeyUp:
            event_type = "up"
        elif e_type == Quartz.kCGEventFlagsChanged:
            if key_name.endswith("shift") and (flags & Quartz.kCGEventFlagMaskShift):
                event_type = "down"
            elif key_name == "caps lock" and (flags & Quartz.kCGEventFlagMaskAlphaShift):
                event_type = "down"
            elif (key_name.endswith("option") or key_name.endswith("alt")) and (flags & Quartz.kCGEventFlagMaskAlternate):
                event_type = "down"
            elif key_name == "ctrl" and (flags & Quartz.kCGEventFlagMaskControl):
                event_type = "down"
            elif key_name == "command" and (flags & Quartz.kCGEventFlagMaskCommand):
                event_type = "down"
            else:
                event_type = "up"

        if self.blocking:
            return None

        self.callback(KeyboardEvent(event_type, scan_code, name=key_name, is_keypad=is_keypad))
        return event

key_controller = KeyController()

""" Exported functions below """

def init():
    key_controller = KeyController()

def press(scan_code):
    """ Sends a 'down' event for the specified scan code """
    key_controller.press(scan_code)

def release(scan_code):
    """ Sends an 'up' event for the specified scan code """
    key_controller.release(scan_code)

def map_char(character):
    """ Returns a tuple of (scan_code, modifiers) where ``scan_code`` is a numeric scan code 
    and ``modifiers`` is an array of string modifier names (like 'shift') """
    return key_controller.map_char(character)

def name_from_scancode(scan_code):
    """ Returns the name or character associated with the specified key code """
    return key_controller.map_scan_code(scan_code)

def listen(queue, is_allowed=lambda *args: True):
    """ Adds all monitored keyboard events to queue. To use the listener, the script must be run
    as root (administrator). Otherwise, it throws an OSError. """
    if not os.geteuid() == 0:
        raise OSError("Error 13 - Must be run as administrator")
    listener = KeyEventListener(lambda e: queue.put(e) or is_allowed(e.name, e.event_type == KEY_UP))
    t = threading.Thread(target=listener.run, args=())
    t.daemon = True
    t.start()