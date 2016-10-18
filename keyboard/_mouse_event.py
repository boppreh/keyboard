# -*- coding: utf-8 -*-
from collections import namedtuple

LEFT = 'left'
RIGHT = 'right'
MIDDLE = 'middle'
X = 'x'
X2 = 'x2'

UP = 'up'
DOWN = 'down'
DOUBLE = 'double'


ButtonEvent = namedtuple('ButtonEvent', ['event_type', 'button', 'time'])
WheelEvent = namedtuple('WheelEvent', ['delta', 'time'])
MoveEvent = namedtuple('MoveEvent', ['x', 'y', 'time'])
