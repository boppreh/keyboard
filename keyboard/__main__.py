import keyboard
print('Press space twice to replay keyboard actions.')
while True:
    keyboard.play(keyboard.record('space, space'), 3)
input()
