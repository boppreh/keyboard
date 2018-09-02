import keyboard

print('Press and release your desired shortcut: ')
shortcut = keyboard.read_hotkey()
print('Shortcut selected:', shortcut)

def on_triggered():
	print("Triggered!")
keyboard.add_hotkey(shortcut, on_triggered)

print("Press ESC to stop.")
keyboard.wait('esc')
