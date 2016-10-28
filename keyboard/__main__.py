# -*- coding: utf-8 -*-
import keyboard
import fileinput
import json
import sys

def print_event_json(event):
	if event.name.isalnum():
		print('{{"type": "{}", "name": "{}", "scan_code": {}, "time": {}}}'.format(event.event_type, event.name, event.scan_code, event.time))
	else:
		print('{{"type": "{}", "scan_code": {}, "time": {}}}'.format(event.event_type, event.scan_code, event.time))
	sys.stdout.flush()
keyboard.hook(print_event_json)

for line in fileinput.input():
	event_json = json.loads(line)
	key = event_json.get('name') or event_json.get('scan_code')
	if event_json['type'] == keyboard.KEY_DOWN:
		keyboard.press(key)
	elif event_json['type'] == keyboard.KEY_UP:
		keyboard.release(key)
	else:
		raise ValueError('Invalid event type: {}'.format(event_json['type']))