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


ButtonEvent = namedtuple('ButtonEvent', ['type', 'button'])
WheelEvent = namedtuple('WheelEvent', ['delta'])
MoveEvent = namedtuple('MoveEvent', ['dx', 'dy'])