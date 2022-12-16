# SPDX-License-Identifier: GPL-2.0-or-later

"""
A small library to customize ICL01.
More a proof of concept and an APDU reference than a serious software.
"""

import collections
import struct
import time

import hid

import hut

class InvalidActionError(Exception):
    pass

class ICL01QueryError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__("Status 0 expected got {}".format(status))

ICL01Capabilities = collections.namedtuple('ICL01Capabilities', ('map_size', 'macros_buffer_size'))

class ICL01Capabilities:
    __slots__ = ('map_size', 'macros_buffer_size')
    STRUCT = struct.Struct('<H3xBB5xBHH47x')
    size = 0x40

    def __init__(self, map_size, macros_buffer_size, dpi_steps, dpi_max, dpi_min):
        self.map_size = map_size
        self.macros_buffer_size = macros_buffer_size * 0x80
        # These are not used with a keyboard
        #self.dpi_steps = dpi_steps
        #self.dpi_max = dpi_max
        #self.dpi_min = dpi_min

    @classmethod
    def unpack_from(cls, buffer, offset = 0):
        args = cls.STRUCT.unpack_from(buffer, offset)
        assert(args[0] == 0x55aa)
        return cls(*args[1:])

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)
    
    def __str__(self):
        return "Board size: {} keys, Max macro buffer size: {}".format(self.map_size, self.macros_buffer_size)

class ICL01GlobalConfig:
    __slots__ = ('current_profile', 'profiles')
    PROFILES_COUNT = 3
    size = 3 * 0x40

    def __init__(self, current_profile, profiles):
        self.current_profile = current_profile
        self.profiles = profiles

    @classmethod
    def unpack_from(cls, buffer, offset = 0):
        assert(len(buffer) == cls.size)

        current_profile = buffer[0]
        profiles = list(ICL01Config.iter_unpack(buffer))
        return cls(current_profile, profiles)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        assert(self.current_profile >= 0 and self.current_profile <= 2)
        assert(len(self.profiles) <= 3)
        data = memoryview(buffer)[offset:offset+self.size]

        for i, p in enumerate(self.profiles):
            p.pack_into(data, i*0x40)
        data[0] = self.current_profile

    def pack(self):
        data = bytearray(self.size)
        self.pack_into(data, 0)
        return data

class ICL01LightInfo:
    __slots__ = ('selectItem', 'light', 'speed', 'fx', 'multicolor', 'r', 'g', 'b')
    STRUCT = struct.Struct('<BBBBBBBB')
    size = 8

    def __init__(self, light, speed, fx, multicolor, r, g, b):
        self.light = light
        self.speed = speed
        self.fx = fx
        self.multicolor = multicolor
        self.r = r
        self.g = g
        self.b = b

    @classmethod
    def unpack_from(cls, buffer, offset = 0):
        return cls(*cls.STRUCT.unpack_unpack_from(buffer, offset))

    @classmethod
    def unpack(cls, data):
        return cls(*cls.STRUCT.unpack(data))

    @classmethod
    def iter_unpack(cls, data):
        return (cls(*d) for d in cls.STRUCT.iter_unpack(data))

    def pack(self):
        return cls.struct.pack(*self)
    
    def pack_into(self, buffer, offset):
        cls.struct.pack_into(buffer, offset, *self)


class ICL01Config:
    __slots__ = ('board', 'coloroffset', 'zzccledmode', 'wflag', 'key6flag', 'winflag', 'pollingRate', 'scandelay', 'customcolors_group', 'logo', 'logo_on', 'st')
    STRUCTS = (struct.Struct('<B8xBBBBB2xBB'), )
    size = 64

    def __init__(self, board, coloroffset, zzccledmode, wflag, key6flag,
            winflag, pollingRate, scandelay, customcolors_group, logo, logo_on, st):
        self.board = board
        self.coloroffset = coloroffset
        self.zzccledmode = zzccledmode
        self.wflag = wflag
        self.key6flag = key6flag
        self.winflag = winflag
        self.pollingRate = pollingRate
        self.scandelay = scandelay
        self.customcolors_group = customcolors_group
        self.logo = logo
        self.logo_on = logo_on
        self.st = st

    @classmethod
    def unpack_from(cls, buffer, offset = 0):
        data = memoryview(buffer)[offset:offset+cls.size]
        args = (ICL01LightInfo.unpack_from(data, 1),) + cls.STRUCTS[0].unpack_from(data, 9) + (
                ICL01LightInfo.unpack_from(data, 27), int.from_bytes(data[36:37], 'little'),
                ICL01LightInfo.unpack_from(data, 37))
        return cls(*args)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(buffer)

    @classmethod
    def iter_unpack(cls, data):
        sz = len(data)
        offset = 0
        while sz >= cls.size:
            yield cls.unpack_from(data, offset)
            offset += cls.size
            sz -= cls.size
        assert(sz == 0)

    def pack_into(self, buffer, offset):
        data = memoryview(buffer)[offset:offset+self.size]
        self.board.pack_into(data, 1)
        cls.STRUCTS[0].pack_into(data, 9, self.coloroffset, self.zzccledmode, self.wflag,
                self.key6flag, self.winflag, self.pollingRate, self.scandelay,
                self.customcolors_group)
        self.logo.pack_into(data, 27)
        data[36:37] = self.logo_on.to_bytes(1, 'little')
        self.st.pack_into(data, 37)

    def pack(self):
        data = bytearray(0x40)
        self.pack_into(data, 0)
        return data

class Color:
    __slots__ = ('r', 'g', 'b')
    STRUCT = struct.Struct('<BBB')
    size = 3

    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    @classmethod
    def unpack_from(cls, buffer, offset = 0):
        return cls(*cls.STRUCT.unpack_unpack_from(buffer, offset))

    @classmethod
    def unpack(cls, data):
        return cls(*cls.STRUCT.unpack(data))

    @classmethod
    def iter_unpack(cls, data):
        return (cls(*d) for d in cls.STRUCT.iter_unpack(data))

    def pack(self):
        return self.STRUCT.pack(self.r, self.g, self.b)
    
    def pack_into(self, buffer, offset):
        cls.struct.pack_into(buffer, offset, *self)

class Action:
    __slots__ = ('type', )
    size = 3

    @classmethod
    def unpack_from(cls, buffer, offset = 0):
        blk = buffer[offset:offset+cls.size]
        type_ = blk[0]
        if type_ == 0x10:
            return ActionMouseClick.unpack(blk)
        elif type_ == 0x11:
            return ActionMousePan.unpack(blk)
        elif type_ == 0x12:
            return ActionMouseWheel.unpack(blk)
        elif type_ == 0x14:
            return ActionMouseClickRepeat.unpack(blk)
        elif type_ == 0x20:
            return ActionKey.unpack(blk)
        elif type_ == 0x21:
            return ActionKeyRepeat.unpack(blk)
        elif type_ == 0x30:
            return ActionConsumer.unpack(blk)
        elif type_ == 0x40:
            return ActionSystem.unpack(blk)
        elif type_ == 0x50:
            return ActionConsumer.unpack(blk)
        elif type_ == 0x60:
            return ActionConsumer(0x223, 0x60) 
        elif type_ == 0x70:
            return ActionMacro.unpack(blk)
        elif type_ == 0x71:
            return ActionMacroRepeat.unpack(blk)
        elif type_ == 0xa0:
            return ActionFn.unpack(blk)
        elif type_ == 0xb0:
            return ActionKey.unpack(blk)
        else:
            raise InvalidActionError("Invalid action type")

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    @classmethod
    def iter_unpack(cls, data):
        sz = len(data)
        offset = 0
        while sz >= cls.size:
            yield cls.unpack_from(data, offset)
            offset += cls.size
            sz -= cls.size
        assert(sz == 0)

    @classmethod
    def unpack_macro(cls, type_, param):
        action = type_ & 0x7f
        if action == 0x1:
            return ActionMouseClick.unpack_macro(type_, param)
        elif action == 0x2:
            return ActionMousePan.unpack_macro(type_, param)
        elif action == 0x3:
            return ActionMouseWheel.unpack_macro(type_, param)
        elif action == 0x4:
            return ActionMouseMove.unpack_macro(type_, param)
        elif action == 0x5:
            return ActionMouseMove.unpack_macro(type_, param)
        elif action == 0x9:
            return ActionKey.unpack_macro(type_, param)
        elif action == 0xa:
            return ActionKey.unpack_macro(type_, param)
        else:
            raise InvalidActionError("Invalid action type")

    def __eq__(self, other):
        ret = ((self.__class__ == other.__class__) and
                (self.type == other.type))
        if not ret:
            return False
        
        for v in self.__slots__:
            if getattr(self, v) != getattr(other, v):
                return False
        
        return True
        
class ActionMouseClick(Action):
    __slots__ = ('buttons', )
    STRUCT = struct.Struct('<BBB')

    def __init__(self, buttons):
        assert(buttons >= 0 and buttons <= 0xff)
        self.type = 0x10
        self.buttons = buttons

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, buttons, unused = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ & 0x7f == 0x10)
        return cls(buttons)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.buttons, 0)

    def pack(self):
        return self.STRUCT.pack(self.type, self.buttons, 0)

    @classmethod
    def unpack_macro(cls, type_, param):
        assert(type_ == 0x1)
        return cls(param)
    
    def pack_macro(self):
        return (0x1, self.buttons)

    def __str__(self):
        buttons = []
        b = self.buttons
        for i in range(8):
            m = 1 << i
            if b & m:
                buttons.append(hut.BUTTONS[m])

        if not buttons:
            buttons.append("<None>")

        return "+".join(buttons)

    def __repr__(self):
        return "{}(0x{:02x})".format(self.__class__.__name__, self.buttons)

class ActionMousePan(Action):
    __slots__ = ('pan', 'delay')
    STRUCT = struct.Struct('<BBb')

    def __init__(self, pan, delay):
        assert(pan >= -128 and pan <= 127)
        assert(delay >= 0 and delay <= 0xf)
        self.type = 0x11
        self.pan = pan
        self.delay = delay

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, delay, pan = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x11)
        return cls(pan, delay)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.delay, self.pan)

    def pack(self):
        return self.STRUCT.pack(self.type, self.delay, self.pan)

    @classmethod
    def unpack_macro(cls, type_, param):
        assert(type_ & 0x7f == 0x2)
        return cls(param, 0x55)
    
    def pack_macro(self):
        return (0x2, self.pan)

    def __str__(self):
        return "Pan {} (repeated every {} times)".format(
                self.pan,
                self.delay)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.pan, self.delay)

class ActionMouseWheel(Action):
    __slots__ = ('wheel', )
    STRUCT = struct.Struct('<BBb')

    def __init__(self, wheel):
        assert(wheel >= -128 and wheel <= 127)
        self.type = 0x12
        self.wheel = wheel

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, unused, wheel = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x12)
        return cls(wheel)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, 0, self.wheel)

    def pack(self):
        return self.STRUCT.pack(self.type, 0, self.wheel)

    @classmethod
    def unpack_macro(cls, type_, param):
        assert(type_ & 0x7f == 0x3)
        # There is a bug in the firmware on this: this can't work
        return cls(0)
    
    def pack_macro(self):
        return (0x3, 0)

    def __str__(self):
        return "Wheel {}".format(self.wheel)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.wheel)

class ActionMouseClickRepeat(Action):
    __slots__ = ('delay', 'count')
    STRUCT = struct.Struct('<BBB')

    def __init__(self, delay, count):
        assert(delay >= 0 and count <= 0xff)
        self.type = 0x14
        self.delay = delay
        self.count = count

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, delay, count = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x14)
        return cls(delay, count)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.delay, self.count)

    def pack(self):
        return self.STRUCT.pack(self.type, self.delay, self.count)

    def __str__(self):
        return "{} left clicks every {} cycles".format(self.count, self.delay)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.delay, self.count)

class ActionMouseMove(Action):
    __slots__ = ('deltaX', 'deltaY')

    def __init__(self, deltaX=0, deltaY=0):
        assert(deltaX == 0 or deltaY == 0)
        assert(deltaX >= -128 and deltaX <= 127)
        assert(deltaY >= -128 and deltaY <= 127)
        self.deltaX = deltaX
        self.deltaY = deltaY

    @classmethod
    def unpack_macro(cls, type_, param):
        pos = (type_ & 0x80) == 0
        type_ &= 0x7f
        assert(type_ == 0x4 or type_ == 0x5)
        
        if pos:
            delta = param
        else:
            delta = 256 - param

        # Convert to signed integer
        delta &= 0xff
        if delta & 0x80:
            delta = delta - 256
        
        deltaX = deltaY = 0
        if type_ == 0x4:
            deltaX = delta
        elif type_ == 0x5:
            deltaY = delta

        return cls(deltaX, deltaY)
    
    def pack_macro(self):
        if self.deltaY == 0:
            return (0x4, self.deltaY.to_bytes(1, 'little')[0])
        elif self.deltaX == 0:
            return (0x5, self.deltaX.to_bytes(1, 'little')[0])
        else:
            raise InvalidActionError("Can't encode ActionMouseMove in macro")

    def __str__(self):
        return "Mouse move dx: {} dy: {}".format(self.deltaX, self.deltaY)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.deltaX, self.deltaY)

class ActionKey(Action):
    __slots__ = ('modifiers', 'keycode')
    STRUCT = struct.Struct('<BBB')

    def __init__(self, modifiers, keycode, type_=0x20):
        assert(type_ == 0x20 or type_ == 0xb0)
        assert(modifiers >= 0 and modifiers <= 0xff)
        assert(keycode >= 0 and keycode <= 0xff)
        self.type = type_
        self.modifiers = modifiers
        self.keycode = keycode

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, modifiers, keycode = cls.STRUCT.unpack_from(buffer, offset)
        return cls(modifiers, keycode, type_)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.modifiers, self.keycode)

    def pack(self):
        return self.STRUCT.pack(self.type, self.modifiers, self.keycode)


    @classmethod
    def unpack_macro(cls, type_, param):
        type_ &= 0x7f
        assert(type_ == 0x9 or type_ == 0xa)
        if type_ == 0x9:
            return cls(param, 0)
        elif type_ == 0xa:
            return cls(0, param)
    
    def pack_macro(self):
        if self.keycode == 0:
            return (0x9, self.modifiers)
        elif self.modifiers == 0:
            return (0xa, self.keycode)
        else:
            raise InvalidActionError("Can't encode ActionKey in macro")

    def __str__(self):
        keys = []
        mod = self.modifiers
        for i in range(8):
            m = 1 << i
            if mod & m:
                keys.append(hut.MODIFIERS[m])
        if self.keycode != 0:
            keys.append(hut.KEYS.get(self.keycode, "Unknown"))

        if not keys:
            keys.append("<None>")

        return "+".join(keys)

    def __repr__(self):
        return "{}(0x{:02x}, {})".format(self.__class__.__name__, self.modifiers, self.keycode)

class ActionKeyRepeat(Action):
    __slots__ = ('keycode', 'delay')
    STRUCT = struct.Struct('<BBB')

    def __init__(self, keycode, delay):
        assert(keycode >= 0 and keycode <= 0xff)
        assert(delay >= 0 and delay <= 0xf)
        self.type = 0x21
        self.keycode = keycode
        self.delay = delay

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, delay, keycode = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x21)
        return cls(keycode, delay)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.delay, self.keycode)

    def pack(self):
        return self.STRUCT.pack(self.type, self.delay, self.keycode)

    def __str__(self):
        return "{} (repeated every {} times)".format(
                hut.KEYS.get(self.keycode, "Unknown"),
                self.delay)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.keycode, self.delay)

class ActionConsumer(Action):
    __slots__ = ('keycode', )
    STRUCT = struct.Struct('<BH')

    def __init__(self, keycode, type_=0x30):
        assert(type_ == 0x30 or type_ == 0x50 or type_ == 0x60)
        assert(keycode >= 0 and keycode <= 0xffff)
        if type_ == 0x60:
            assert(keycode == 0x223)
        self.type = type_
        self.keycode = keycode

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, keycode = cls.STRUCT.unpack_from(buffer, offset)
        return cls(keycode, type_)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.keycode)

    def pack(self):
        return self.STRUCT.pack(self.type, self.keycode)

    def __str__(self):
        return hut.CONSUMER.get(self.keycode, "Unknown")

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.keycode)

class ActionSystem(Action):
    __slots__ = ('keys', )
    STRUCT = struct.Struct('<BH')

    def __init__(self, keys):
        # According to HID descriptor: only the 3 first bits are used
        assert(keys >= 0 and keys <= 0x7)
        self.type = 0x40
        self.keys = keys

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, keys = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x40)
        return cls(keys)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.keys)

    def pack(self):
        return self.STRUCT.pack(self.type, self.keys)

    def __str__(self):
        keys = []
        k = self.keys
        for i in range(3):
            m = 1 << i
            if k & m:
                keys.append(hut.SYSTEM[m])

        if not keys:
            keys.append("<None>")
        return "+".join(keys)

    def __repr__(self):
        return "{}({:02x})".format(self.__class__.__name__, self.keys)

class ActionMacro(Action):
    __slots__ = ('macro', 'mode')
    STRUCT = struct.Struct('<BBB')
    MACRO_MODES = {
        0x00: "One-shot",
        0x01: "Loop until release",
        0x02: "Loop until new press",
        0x03: "Stop at release",
    }

    def __init__(self, macro, mode):
        assert(macro >= 0 and macro <= 0xff)
        assert(mode in self.MACRO_MODES)
        self.type = 0x70
        self.macro = macro
        self.mode = mode

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, macro, mode = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x70)
        return cls(macro, mode)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.macro, self.mode)

    def pack(self):
        return self.STRUCT.pack(self.type, self.macro, self.mode)

    def __str__(self):
        return "Macro {0}, {1}".format(self.macro, self.MACRO_MODES[self.mode])

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.macro, self.mode)

class ActionMacroRepeat(Action):
    __slots__ = ('macro', 'repeat')
    STRUCT = struct.Struct('<BBB')

    def __init__(self, macro, repeat):
        assert(macro >= 0 and macro <= 0xff)
        assert(repeat >= 0 and repeat <= 0xff)
        self.type = 0x71
        self.macro = macro
        self.repeat = repeat

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, macro, repeat = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0x71)
        return cls(macro, repeat)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.macro, self.repeat)

    def pack(self):
        return self.STRUCT.pack(self.type, self.macro, self.repeat)

    def __str__(self):
        return "Macro {0}, Repeat {1} times".format(self.macro, self.repeat)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.macro, self.repeat)

class ActionFn(Action):
    __slots__ = ('mode', 'param')
    STRUCT = struct.Struct('<BBB')
    FN_MODES = {
        0x01: "Fn",
        0x02: "Run macro {}",
        0x03: "Clear reports",
        0x04: "Game mode",
        0x08: "Reset",
        0x09: "Increase luminosity",
        0x0a: "Decrease luminosity",
        0x0b: "Decrease speed",
        0x0c: "Increase speed",
        0x0d: "Next color",
        0x0e: "Enable FX (TO CHECK)",
        0x0f: "Custom color profile {}",
        0x11: "Switch color mode 4/5/6",
        0x12: "Switch color mode 1/2/3",
        0x13: "Switch color mode 7/8/9",
        0x14: "Switch color mode 10/11/12",
        0x15: "Switch color mode 13/14/15",
        0x16: "Switch color mode 16/17/18",
        0x17: "Change color submode"
    }

    def __init__(self, mode, param):
        assert(mode in self.FN_MODES)
        self.type = 0xA0
        self.mode = mode
        self.param = param

    @classmethod
    def unpack_from(cls, buffer, offset=0):
        type_, mode, param = cls.STRUCT.unpack_from(buffer, offset)
        assert(type_ == 0xA0)
        return cls(mode, param)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)

    def pack_into(self, buffer, offset):
        return self.STRUCT.pack_into(buffer, offset, self.type, self.mode, self.param)

    def pack(self):
        return self.STRUCT.pack(self.type, self.mode, self.param)

    def __str__(self):
        return self.FN_MODES[self.mode].format(self.param)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.mode)

class MacrosBlock(list):
    HDR = struct.Struct('<HHH10x')
    WORD = struct.Struct('<H')
        
    @classmethod
    def unpack_from(cls, buffer, offset=0):
        magic, size, count = cls.HDR.unpack_from(buffer, offset)
        assert(magic == 0x55aa or magic == 0x0000)
        
        if magic == 0x0000:
            return cls([])
        
        assert(len(buffer) >= size)
        
        buffer = memoryview(buffer)[:size]
        
        offsets = (cls.WORD.unpack_from(buffer, offset+16+2*i)[0] for i in range(count))
        macros = (Macro.unpack_from(buffer, offset + off) for off in offsets)
        
        return cls(macros)

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)
    
    def size(self):
        sz = self.HDR.size + self.WORD.size*len(self)
        for macro in self.macros:
            sz += macro.size()
        return sz
    
    def pack_into(self, buffer, offset):
        wsz = self.WORD.size
        offsets = []
        offsetsoff = offset + self.HDR.size
        macrosoff = offsetsoff + wsz*len(self)
        for macro in self:
            offsets.append(macrosoff)
            macrosoff += macro.pack_into(buffer, macrosoff)
        
        for off in offsets:
            self.WORD.pack_into(buffer, offsetsoff, off)
            offsetsoff += wsz
        
        self.HDR.pack_into(buffer, offset, 0x55aa, macrosoff, len(self))

    def pack(self):
        buffer = bytearray(self.size())
        self.pack_into(buffer, 0)
        return bytes(buffer)

    def __str__(self):
        s = ""
        for i, macro in enumerate(self):
            s += "Macro {}\n{!s}".format(i, macro)
        return s

class Macro(list):
    STRUCT = struct.Struct('<HBB')
    
    @classmethod
    def unpack_from(cls, buffer, offset=0):
        count, unused1, unused2 = cls.STRUCT.unpack_from(buffer, offset)
        
        sz = cls.STRUCT.size
        def actions():
            offset_ = offset + sz
            for i in range(count):
                delay, action, param = cls.STRUCT.unpack_from(buffer, offset_)
                pressed = (action & 0x80) != 0
                act = Action.unpack_macro(action, param)
                yield MacroEntry(delay, pressed, act)
                offset_ += sz

        return cls(actions())

    @classmethod
    def unpack(cls, data):
        return cls.unpack_from(data)
    
    def size(self):
        return self.STRUCT.size * (len(self) + 1)
    
    def pack_into(self, buffer, offset):
        sz = self.STRUCT.size
        self.STRUCT.pack_into(buffer, offset, len(self), 0, 0)
        off = sz
        for delay, act in self:
            action, param = act.pack_macro()
            self.STRUCT.pack_into(buffer, offset + off, delay, action | 0x80, param)
            off += sz
        return off

    def pack(self):
        buffer = bytearray(self.size())
        self.pack_into(buffer, 0)
        return bytes(buffer)
    
    def __str__(self):
        s = "{} actions:\n".format(len(self))
        for entry in self:
            if type(entry.action) is ActionMouseMove:
                s += "    {!s}, wait {} ms\n".format(entry.action, entry.delay)
            else:
                s += "    {!s}, {}, wait {} ms\n".format(entry.action, "pressed" if entry.pressed else "released", entry.delay)
        return s

MacroEntry = collections.namedtuple('MacroEntry', ('delay', 'pressed', 'action'))

class ICL01Device:
    # 64 - 8 for header
    DATA_MAX = 56
    MSG_HDR = struct.Struct('<BHBBHB56s')

    def __init__(self, paths):
        assert(len(paths) == 2)
        self.paths = paths
        self.devices = [None]*2
        self.inconfig = False
        self.capabilities = None

    def __repr__(self):
        return "<{0}: {1!r}>".format(self.__class__.__name__, self.paths)

    def _get(self, intf):
        if self.devices[intf] is not None:
            return self.devices[intf]

        d = hid.device()
        d.open_path(self.paths[intf])
        self.devices[intf] = d
        return d

    def reboot(self):
        dev = self._get(0)

        # Go to bootloader
        report = b'\xAA\x55\xA5\x5A\xFF\x00\x33\xCC'
        report += b'\x00' * (64 - len(report))
        dev.send_feature_report(b'\x00' + report)

        # Our device now have vanished
        #self.paths = None
        #self.devices = None
        
        # Come back to firmware
        report = b'\x07\xAA\x55'
        report += b'\x00' * (64 - len(report))
        dev.send_feature_report(b'\x00' + report)

    def checksum(self, cmd, size, offset, status, data):
        if size is None:
            size = len(data)
        checksum = 0
        checksum = (checksum + cmd) & 0xffff
        checksum = (checksum + size) & 0xffff
        checksum = (checksum + (offset & 0xff)) & 0xffff
        checksum = (checksum + (offset >> 8)) & 0xffff
        checksum = (checksum + size) & 0xffff
        for b in data:
            checksum = (checksum + b) & 0xffff
        return checksum

    def query(self, cmd, offset = 0, size = None, data = None):
        dev = self._get(1)

        if data is None:
            data = b''
        if size is None:
            size = len(data)

        assert(size >= 0 and size <= self.DATA_MAX)
        assert(offset >= 0 and offset <= 0xffff)

        checksum = self.checksum(cmd, size, offset, 0, data)
        request = self.MSG_HDR.pack(4, checksum, cmd, size, offset, 0, data)
        dev.write(request)

        start = current = time.monotonic()
        while True:
            delta = int((current - start) * 1000.)
            remaining = 1000 - delta
            if remaining <= 0:
                raise IOError("Timeout while reading data")
            reply = dev.read(64, remaining)
            if reply and reply[0] == 4:
                break
            current = time.monotonic()

        report_id, rchecksum, rcmd, rsize, roffset, rstatus, rdata = self.MSG_HDR.unpack(bytes(reply))

        if report_id != 4:
            raise IOError("Report ID 4 expected got {}".format(report_id))

        # Keyboard doesn't recompute its checksum
        if checksum != rchecksum:
            raise IOError("Checksum 0x{:04x} expected got 0x{:04x}".format(checksum, rchecksum))

        if cmd != rcmd:
            raise IOError("Command 0x{:02x} expected got 0x{:02x}".format(cmd, rcmd))

        if offset != roffset:
            raise IOError("Offset 0x{:04x} expected got 0x{:04x}".format(offset, roffset))

        if rstatus != 0:
            raise ICL01QueryError(rstatus)

        return rdata[:rsize]

    def begin_configure(self):
        if self.inconfig:
            raise RuntimeError("Already in configure mode")
        self.query(0x01)
        self.inconfig = True

    def end_configure(self, *args):
        if not self.inconfig:
            raise RuntimeError("Not in configure mode")
        self.query(0x02)
        self.inconfig = False

    __enter__ = begin_configure
    __exit__ = end_configure

    def read(self, cmd, size, offset = 0):
        ret = b''
        while size > 0:
            sz = min(size, self.DATA_MAX)
            reply = self.query(cmd, offset, sz, None)
            size -= len(reply)
            offset += len(reply)
            ret += reply
        return ret

    def write(self, cmd, data, offset = 0):
        while len(data) > 0:
            sz = min(len(data), self.DATA_MAX)
            self.query(cmd, offset, None, data[:sz])
            data = data[sz:]
            offset += sz

    def read_capabilities(self, force=False):
        if self.capabilities and not force:
            return self.capabilities
        data = self.read(0x03, size=0x40)
        self.capabilities = ICL01Capabilities.unpack(data)
        return self.capabilities

    def write_capabilities(self, data):
        """Never used in real life"""
        # We don't build the structure ourselves as we don't know enough about it
        self.write(0x04, data)
        self.capabilities = None

    def read_global_config(self, profile=None):
        assert(profile is None or profile < 3)
        if profile is None:
            offset = 0
            sz = 3 * 0x40
        else:
            offset = 0x40 * profile
            sz = 0x40

        config = self.read(0x05, sz, offset=offset)

        if profile is None:
            return ICL01GlobalConfig.unpack(config)
        else:
            return ICL01Config.unpack(config)

    def write_global_config(self, config=None, profile=None):
        if not self.inconfig:
            raise RuntimeError("Device must be set in configure state first")

        if config is None:
            if profile is None:
                raise ValueError("When writing no configuration, profile id must be set")
            assert(profile >= 0 and profile <= 2)
            self.write(0x06, profile.to_bytes(1, byteorder='little'), 0)
            return

        if isinstance(config, ICL01Config):
            if profile is None:
                raise ValueError("When writing only one configuration, profile id must be set")
            assert(profile >= 0 and profile <= 2)
            offset = profile * 0x40 + 0x01
            data = config.pack()
            self.write(0x06, data[1:], offset)
            return

        if isinstance(config, ICL01GlobalConfig):
            if profile is not None:
                raise ValueError("When writing all configurations, profile id must not be set")
            data = config.pack()
            self.write(0x06, data, 0)
            return

        raise ValueError("Invalid configuration")

    def read_original_mapping_table(self):
        sz = self.read_capabilities().map_size * 3
        data = self.read(0x07, size=sz)
        return [Action.unpack_from(data, offset) for offset in range(0, sz, 3)]

    def read_current_mapping_table(self):
        sz = self.read_capabilities().map_size * 3
        data = self.read(0x08, size=sz)
        return [Action.unpack_from(data, offset) for offset in range(0, sz, 3)]

    def write_current_mapping_table(self, actions, start=0):
        if not self.inconfig:
            raise RuntimeError("Device must be set in configure state first")

        assert(start + len(actions) < self.read_capabilities().map_size)

        data = bytearray(len(actions) * Action.size)
        offset = 0
        for action in actions:
            action.pack_into(data, offset)
            offset += Action.size

        self.write(0x09, data, offset=start*Action.size)

    def read_custom_colors(self, profile=None):
        if profile is None:
            sz = 10 * 512
        else:
            assert(len(data) <= 512)
            assert(profile < 10)
            sz = 512
            offset = profile * 512
        data = self.read(0x0a, size=sz)
        profile_size = self.read_capabilities().map_size * Color.size
        assert(profile_size < 512)
        if profile is None:
            ret = []
            for i in range(10):
                d = data[i*512:i*512+profile_size]
                ret.append(list(Color.iter_unpack(d)))
        else:
            d = data[:profile_size]
            ret = list(Color.iter_unpack(d))

        return ret

    def write_custom_colors(self, colors, profile=None, start=0):
        if not self.inconfig:
            raise RuntimeError("Device must be set in configure state first")

        if profile is None:
            # start is the profile number to begin to change
            # colors is an array of array of 170 colors
            assert(start + len(colors) < 10)
            data = bytearray(len(colors)*512)
            for i, col in enumerate(colors):
                assert(len(col) == 170) # 512/3
                offset = i * 512
                for c in col:
                    c.pack_into(data, offset)
                    offset += c.size
            offset = start * 512
        else:
            # start is the color index in the profile to begin to change
            # colors is an array of colors
            assert(profile < 10)
            assert((start+len(colors))*Color.size <= 512)
            data = bytearray(len(colors)*Color.size)
            offset = 0
            for c in colors:
                c.pack_into(data, offset)
                offset += c.size
            offset = profile * 512 + start * Color.size

        self.write(0x0b, data, offset=offset)

    def reset(self):
        self.query(0x0d)

    def write_computer_colors(self, colors, start=0):
        sz = self.read_capabilities().map_size
        assert(len(colors) <= sz - start)

        data = b''
        for col in colors:
            data += col.pack()

        self.write(0x12, data, offset=start*Color.size)

    def cancel_computer_colors(self):
        self.query(0x13)
        
    def read_macros(self):
        sz = self.read_capabilities().macros_buffer_size
        data = self.read(0x14, size=sz)
        return MacrosBlock.unpack_from(data)

    def write_macros(self, macros):
        if not self.inconfig:
            raise RuntimeError("Device must be set in configure state first")

        maxsz = self.read_capabilities().macros_buffer_size
        sz = macros.size()
        assert(sz <= maxsz)
        
        data = bytearray(sz)
        macros.pack_into(data, 0)
        
        data = self.write(0x15, data, offset=0)

    def read_physical_map(self):
        sz = self.read_capabilities().map_size
        data = self.read(0x1b, size=sz)
        return data

    def request_1d_do_not_run(self):
        # Read unknown memory area not documented : 0x1fff0c00 - 0x1fff0cc0
        return
        data = self.read(0x1d, size=0xc0)
        return data
    def request_1e_do_not_run(self, data):
        # Write unknown memory area not documented : 0x1fff0c00 - 0x1fff0cc0
        return
        assert(len(data) < 0xc0)
        self.write(0x1e, data)

    def write_computer_color(self, color):
        data = color.pack()
        self.query(0x1f, offset=0, size=0, data=data)

assert(ICL01Device.MSG_HDR.size == 64)

def enumerate_icl01():
    interfaces = None
    for d in hid.enumerate(0x320f, 0x5041):
        if d['interface_number'] == 0:
            if interfaces is not None:
                assert(len(interfaces) == 2)
                yield ICL01Device(interfaces)
            interfaces = [d['path']]
        else:
            assert(interfaces is not None)
            interfaces.append(d['path'])
    
    if interfaces is not None:
        assert(len(interfaces) == 2)
        yield ICL01Device(interfaces)

def patchconfig(d):
    with d:
        cfg = d.read_global_config()
        c = cfg.profiles[0]
        c.board.selectItem = 17
        c.board.speed = 0
        c.zzccledmode = 3
        c.coloroffset = 0
        c.scandelay = 0
        d.write_global_config(c, profile=0)
        
def live_colors_snake(d):
    sz = d.read_capabilities().map_size
    colors = [Color(0xff, 0, 0)] * sz
    colors[0] = Color(0xff, 0xff, 0xff)
    try:
        while True:
            for i in range(sz):
                d.write_computer_colors(colors)
                time.sleep(0.01)
                item = colors.pop()
                colors.insert(0, item)
    except KeyboardInterrupt:
        pass
    d.cancel_computer_colors()
    
def live_colors_test(d):
    d.write_computer_color(Color(0xff, 0xcc, 0x00))
    d.write_computer_colors([Color(0xff, 0x00, 0x00)], start=1)
    time.sleep(0.3)
    d.cancel_computer_colors()
    
def dump_mapping_table(d):
    physical = d.read_physical_map()
    orig = d.read_original_mapping_table()
    current = d.read_current_mapping_table()
    for key in physical:
        if key == 0xff:
            print("<Empty space>")
            continue
        
        o, c = orig[key], current[key]
        if c != o:
            print(str(o), "=>", str(c))
        else:
            print(str(o))
            


for d in enumerate_icl01():
    #print(d)
    
    print(d.read_capabilities())
    #print(d.read_physical_map())

    #patchconfig(d)

    #live_colors_snake(d)

    #live_colors_test(d)

    dump_mapping_table(d)
    
    print(d.read_macros())

    #d.reboot()
