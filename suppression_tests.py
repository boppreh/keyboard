# Naming
#"a", "b", "left shift", "enter", etc: key
#"shift", "windows", "left ctrl", "right alt", etc: modifiers
#"shift+a", "ctrl+shift+z", "a+z", etc: hold
#"shift+a, b", "a, b, c", "enter, shift+b, shift+c", etc: sequence

KEY_DOWN = 'down'
KEY_UP = 'up'

def test(steps, events, expected):
	events += [(KEY_DOWN, 'z'), (KEY_UP, 'z')]
	expected += [(KEY_DOWN, 'z'), (KEY_UP, 'z')]
	steps[0] = sorted(steps[0].split("+"))
	accepted = []
	pressed_keys = ()
	pending_release = set()
	pending_test = set()

	for event in events:
		event_type, key = event

		if event_type == KEY_DOWN:
			pressed_keys = sorted(set(pressed_keys) | {key})

		if event_type == KEY_UP and key in pending_release:
			pending_release.discard(key)
		elif pressed_keys == steps[0]:
			pending_release.add(key)
			pending_test.clear()
		elif key in steps[0]:
			pending_test.add(key)
			pending_release.add(key)
		else:
			for pending_key in pending_test:
				accepted.append((KEY_DOWN, pending_key))
				if pending_key not in pending_release:
					accepted.append((KEY_UP, pending_key))
			pending_test.clear()
			accepted.append(event)

		if event_type == KEY_UP:
			pressed_keys = sorted(set(pressed_keys) | {key})
	print(expected, accepted, events, '\n\n---\n\n', sep='\n')
	assert accepted == expected, accepted[:-2]
Da = [(KEY_DOWN, 'a')]
Ua = [(KEY_UP, 'a')]
Db = [(KEY_DOWN, 'b')]
Ub = [(KEY_UP, 'b')]
Dz = [(KEY_DOWN, 'z')]
Uz = [(KEY_UP, 'z')]
Dshift = [(KEY_DOWN, 'shift')]
Ushift = [(KEY_UP, 'shift')]
Dctrl = [(KEY_DOWN, 'ctrl')]
Uctrl = [(KEY_UP, 'ctrl')]

a = 'a'
b = 'b'
z = 'z'
ctrl = 'ctrl+'
shift = 'shift+'

#test([a], Ua, []) # or Ua
# test([a], Da, []) # pending state, should not be tested
test([a], Da+Ua, [])
#test([a], Ua+Da+Da+Ua, []) # or Ua
test([a], Da+Da+Da+Ua, [])
test([a], Uz, Uz)
test([a], Dz, Dz)
test([a], Da+Dz+Ua+Uz, Dz+Uz)

test([ctrl+a], Dctrl+Uctrl, Dctrl+Uctrl)
test([ctrl+a], Da+Ua, Da+Ua)
test([ctrl+a], Dctrl+Da+Ua+Uctrl, [])
test([ctrl+a], Dctrl+Da+Uctrl+Ua, [])
test([ctrl+a], Da+Dctrl+Uctrl+Ua, []) # or Da+Dctrl+Uctrl+Ua
test([ctrl+a], Dctrl+Da+Da+Da+Ua+Uctrl, [])
test([ctrl+a], Dctrl+Da+Ua+Dz+Uz+Uctrl, Dctrl+Dz+Uz+Uctrl)
test([ctrl+a], Dctrl+Da+Dz+Ua+Uz+Uctrl, Dctrl+Dz+Uz+Uctrl)
test([ctrl+a], Dctrl+Da+Dz+Uz+Ua+Uctrl, Dctrl+Dz+Uz+Uctrl)
test([ctrl+a], Dctrl+Dz+Da+Uz+Ua+Uctrl, Dctrl+Dz+Da+Uz+Ua+Uctrl)

test([a, b], Da+Ua, Da+Ua)
test([a, b], Db+Ub, Db+Ub)
test([a, b], Dz+Uz, Dz+Uz)
test([a, b], Da+Ua+Db+Ub, [])
test([a, b], Da+Db+Ua+Ub, []) # or Da+Db+Ua+Ub
test([a, b], Da+Db+Ub+Ua, []) # or Da+Db+Ub+Ua
test([a, b], Da+Ua+Dz+Uz, Da+Ua+Dz+Uz)
test([a, b], Da+Ua+Da+Ua+Db+Ub, Da+Ua)
test([a, b], Da+Ua+Db+Dz+Uz+Ub, Dz+Uz)
test([a, b], Da+Ua+Db+Dz+Ub+Uz, Dz+Uz)

test([a, b], Dz+Uz, Dz+Uz)
test([a, a], Da+Ua, Da+Ua)
test([a, a], Da+Ua+Da+Ua, [])
test([a, a], Da+Da+Ua, []) # or Da+Da+Ua
test([a, a], Da+Da+Da+Da+Ua, []) # or Da+Da+Da+Da+Ua
test([a, a], Da+Da+Da+Ua, Da+Ua) # or Da+Da+Da+Ua


# Add implicit "Dz+Uz" to every test and expected result, just to make sure it didn't break after the test.
# Add fake "TRIGGERED" event?