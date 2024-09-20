import keyboard


def callback(e: keyboard.KeyboardEvent):
    print(f"scan_code: {e.scan_code}, name: {e.name}")
    isPressed = e.event_type == keyboard.KEY_DOWN
    if not e.name == 'menu':
        keyboard.send(e.scan_code, isPressed, not isPressed)
    else:
        print('me')
        keyboard.send('b', isPressed, not isPressed)


# keyboard.remap_key(121, '1')
keyboard.hook(callback, True)
# keyboard.remap_key(115, '2')
# keyboard.hook(callback=callback, suppress=True)

try:
    keyboard.wait()
except KeyboardInterrupt:
    print('shut')
finally:
    keyboard.unhook_all()
