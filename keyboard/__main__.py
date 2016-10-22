import keyboard
keyboard.wait('ctrl')
exit()
print('Press space twice to replay keyboard actions.')
while True:
    keyboard.play(keyboard.record('space, space'), 3)
