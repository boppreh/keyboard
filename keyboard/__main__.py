# -*- coding: utf-8 -*-
import keyboard
#keyboard.add_abbreviation('aaa', '123456')
#input()
#keyboard.hook(print)

print('Press space twice to replay keyboard actions.')
keyboard.play(keyboard.record('space, space'), 3)