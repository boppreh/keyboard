# -*- coding: utf-8 -*-
import keyboard
import fileinput
import json
import sys

def print_event_json(event):
	# Could use json.dumps(event.__dict__()), but this way we guarantee semantic order.
	if event.name:
		print('{{"event_type": "{}", "name": "{}", "scan_code": {}, "time": {}}}'.format(event.event_type, event.name, event.scan_code, event.time))
	else:
		print('{{"event_type": "{}", "scan_code": {}, "time": {}}}'.format(event.event_type, event.scan_code, event.time))
	sys.stdout.flush()
keyboard.hook(print_event_json)

parse_event_json = lambda line: keyboard.KeyboardEvent(**json.loads(line))
keyboard.play(parse_event_json(line) for line in fileinput.input())