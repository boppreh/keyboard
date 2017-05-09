import ctypes
import ctypes.util
import Quartz
import time
from AppKit import NSEvent

try: # Python 2/3 compatibility
    unichr
except NameError:
    unichr = chr

Carbon = ctypes.cdll.LoadLibrary(ctypes.util.find_library('Carbon'))

class KeyMap(object):
    non_layout_keys = {
        0x24: 'return',
        0x30: 'tab',
        0x31: 'space',
        0x33: 'delete',
        0x35: 'escape',
        0x37: 'command',
        0x38: 'shift',
        0x39: 'capslock',
        0x3A: 'option',
        0x3A: 'alternate',
        0x3B: 'control',
        0x3C: 'rightshift',
        0x3D: 'rightoption',
        0x3E: 'rightcontrol',
        0x3F: 'function',
    }
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
        #print(self.non_layout_keys)
        #print(self.layout_specific_keys)
        for vk in self.non_layout_keys:
            if self.non_layout_keys[vk] == character:
                return (vk, [])
        for vk in self.layout_specific_keys:
            if self.layout_specific_keys[vk][0] == character:
                return (vk, [])
            elif self.layout_specific_keys[vk][1] == character:
                return (vk, ['shift'])
        return None

    def vk_to_character(self, vk, modifiers=[]):
        """ Returns a character corresponding to the specified scan code (with given
        modifiers applied) """
        if vk in self.layout_specific_keys:
            if 'shift' in modifiers:
                return self.layout_specific_keys[vk][1]
            return self.layout_specific_keys[vk][0]
        elif vk in self.non_layout_keys:
            # Not a character
            return None
        else:
            # Invalid vk
            return None


class KeyController(object):
    def __init__(self):
        self.key_map = KeyMap()
        self.current_modifiers = {
            "shift": False,
            "caps": False,
            "alt": False,
            "ctrl": False,
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
            #print(dir(ev))
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
            
            # Update modifiers if necessary
            if key_code == 0x38: # shift
                self.current_modifiers["shift"] = True
            elif key_code == 0x39: # caps lock
                self.current_modifiers["caps"] = True
            elif key_code == 0x3A: # alt
                self.current_modifiers["alt"] = True
            elif key_code == 0x3B: # ctrl
                self.current_modifiers["ctrl"] = True
            event = Quartz.CGEventCreateKeyboardEvent(None, key_code, True)
            if event_flags != 0:
                Quartz.CGEventSetFlags(event, event_flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

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
            
            # Update modifiers if necessary
            if key_code == 0x38: # shift
                self.current_modifiers["shift"] = False
            elif key_code == 0x39: # caps lock
                self.current_modifiers["caps"] = False
            elif key_code == 0x3A: # alt
                self.current_modifiers["alt"] = False
            elif key_code == 0x3B: # ctrl
                self.current_modifiers["ctrl"] = False
            event = Quartz.CGEventCreateKeyboardEvent(None, key_code, False)
            if event_flags != 0:
                Quartz.CGEventSetFlags(event, event_flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def map_char(self, character):
        if character in self.media_keys:
            return (128+self.media_keys[character],[])
        else:
            return self.key_map.character_to_vk(character)



""" Exported functions below """

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

def listen(queue):
    pass # TODO

if __name__ == "__main__":
    # Debugging

    # vk lookup
    #letter = "A"
    #print(letter)
    #vk = key_controller.map_char(letter)
    #print(vk)
    #print(key_controller.key_map.vk_to_character(*vk))

    # keystroke emulation
    press(key_controller.map_char('KEYTYPE_PLAY')[0])
    release(key_controller.map_char('KEYTYPE_PLAY')[0])
    press(key_controller.map_char('a')[0])
    release(key_controller.map_char('a')[0])
