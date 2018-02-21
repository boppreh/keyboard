# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import platform

# TODO: add values from https://svn.apache.org/repos/asf/xmlgraphics/commons/tags/commons-1_0/src/java/org/apache/xmlgraphics/fonts/Glyphs.java

# Defaults to Windows canonical names (platform-specific overrides below)
canonical_names = {
    'escape': 'esc',
    'return': 'enter',
    'del': 'delete',
    'control': 'ctrl',

    'left arrow': 'left',
    'up arrow': 'up',
    'down arrow': 'down',
    'right arrow': 'right',

    ' ': 'space', # Prefer to spell out keys that would be hard to read.
    '\x1b': 'esc',
    '\x08': 'backspace',
    '\n': 'enter',
    '\t': 'tab',
    '\r': 'enter',

    'scrlk': 'scroll lock',
    'prtscn': 'print screen',
    'prnt scrn': 'print screen',
    'snapshot': 'print screen',
    'ins': 'insert',
    'pause break': 'pause',
    'ctrll lock': 'caps lock',
    'capslock': 'caps lock',
    'number lock': 'num lock',
    'numlock:': 'num lock',
    'space bar': 'space',
    'spacebar': 'space',
    'linefeed': 'enter',
    'win': 'windows',

    # Mac keys
    'command': 'windows',
    'cmd': 'windows',
    'control': 'ctrl',
    'option': 'alt',

    'app': 'menu',
    'apps': 'menu',
    'application': 'menu',
    'applications': 'menu',

    'pagedown': 'page down',
    'pageup': 'page up',
    'pgdown': 'page down',
    'pgup': 'page up',
    'next': 'page down', # This looks wrong, but this is how Linux reports.
    'prior': 'page up',

    'underscore': '_',
    'equal': '=',
    'minplus': '+',
    'plus': '+',
    'add': '+',
    'subtract': '-',
    'minus': '-',
    'multiply': '*',
    'asterisk': '*',
    'divide': '/',

    'question': '?',
    'exclam': '!',
    'slash': '/',
    'bar': '|',
    'backslash': '\\',
    'braceleft': '{',
    'braceright': '}',
    'bracketleft': '[',
    'bracketright': ']',
    'parenleft': '(',
    'parenright': ')',

    'period': '.',
    'dot': '.',
    'comma': ',',
    'semicolon': ';',
    'colon': ':',

    'less': '<',
    'greater': '>',
    'ampersand': '&',
    'at': '@',
    'numbersign': '#',
    'hash': '#',
    'hashtag': '#',

    'dollar': '$',
    'sterling': '£',
    'pound': '£',
    'yen': '¥',
    'euro': '€',
    'cent': '¢',
    'currency': '¤',
    'registered': '®',
    'copyright': '©',
    'notsign': '¬',
    'percent': '%',
    'diaeresis': '"',
    'quotedbl': '"',
    'onesuperior': '¹',
    'twosuperior': '²',
    'threesuperior': '³',
    'onehalf': '½',
    'onequarter': '¼',
    'threequarters': '¾',
    'paragraph': '¶',
    'section': '§',
    'ssharp': '§',
    'division': '÷',
    'questiondown': '¿',
    'exclamdown': '¡',
    'degree': '°',
    'guillemotright': '»',
    'guillemotleft': '«',
    
    'acute': '´',
    'agudo': '´',
    'grave': '`',
    'tilde': '~',
    'asciitilde': '~',
    'til': '~',
    'cedilla': ',',
    'circumflex': '^',
    'apostrophe': '\'',
    
    'adiaeresis': 'ä',
    'udiaeresis': 'ü',
    'odiaeresis': 'ö',
    'oe': 'Œ',
    'oslash': 'ø',
    'ooblique': 'Ø',
    'ccedilla': 'ç',
    'ntilde': 'ñ',
    'eacute': 'é',
    'uacute': 'ú',
    'oacute': 'ó',
    'thorn': 'þ',
    'ae': 'æ',
    'eth': 'ð',
    'masculine': 'º',
    'feminine': 'ª',
    'iacute': 'í',
    'aacute': 'á',
    'mu': 'Μ',
    'aring': 'å',

    'zero': '0',
    'one': '1',
    'two': '2',
    'three': '3',
    'four': '4',
    'five': '5',
    'six': '6',
    'seven': '7',
    'eight': '8',
    'nine': '9',

    'play/pause': 'play/pause media',

    'num multiply': '*',
    'num divide': '/',
    'num add': '+',
    'num plus': '+',
    'num minus': '-',
    'num sub': '-',
    'num enter': 'enter',
    'num 0': '0',
    'num 1': '1',
    'num 2': '2',
    'num 3': '3',
    'num 4': '4',
    'num 5': '5',
    'num 6': '6',
    'num 7': '7',
    'num 8': '8',
    'num 9': '9',

    'left win': 'left windows',
    'right win': 'right windows',
    'left control': 'left ctrl',
    'right control': 'right ctrl',
    'left menu': 'left alt', # Windows...
}
sided_modifiers = {'ctrl', 'alt', 'shift', 'windows'}
all_modifiers = {'alt', 'alt gr', 'ctrl', 'shift', 'windows'} | set('left ' + n for n in sided_modifiers) | set('right ' + n for n in sided_modifiers)

# Platform-specific canonical overrides

if platform.system() == 'Darwin':
    canonical_names.update({
        "command": "command",
        "windows": "command",
        "cmd": "command",
        "win": "command",
        "backspace": "delete"
    })
    all_modifiers = {'alt', 'ctrl', 'shift', 'windows'}