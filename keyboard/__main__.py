# -*- coding: utf-8 -*-
import keyboard
import fileinput
import json
import sys

def print_event_json(event):
	print(event.to_json())
	sys.stdout.flush()
keyboard.hook(print_event_json)

parse_event_json = lambda line: keyboard.KeyboardEvent(**json.loads(line))
keyboard.play(parse_event_json(line) for line in fileinput.input())