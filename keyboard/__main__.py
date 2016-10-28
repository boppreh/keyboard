# -*- coding: utf-8 -*-
import keyboard
#keyboard.add_abbreviation('123', '123456/!') and input()

print('Press space twice to replay keyboard actions.')
keyboard.play(keyboard.record('space, space'), 3)