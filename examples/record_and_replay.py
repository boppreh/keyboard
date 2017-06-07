"""
Prints lines with JSON object for each keyboard event, and reads similar events
from stdin to simulate events. Example:

	{"event_type": "down", "name": "a", "scan_code": 30, "time": 1491442622.6348252}
	{"event_type": "down", "name": "s", "scan_code": 31, "time": 1491442622.664881}
	{"event_type": "down", "name": "d", "scan_code": 32, "time": 1491442622.7148278}
	{"event_type": "down", "name": "f", "scan_code": 33, "time": 1491442622.7544951}
	{"event_type": "up", "name": "a", "scan_code": 30, "time": 1491442622.7748237}
	{"event_type": "up", "name": "s", "scan_code": 31, "time": 1491442622.825077}
	{"event_type": "up", "name": "d", "scan_code": 32, "time": 1491442622.8644736}
	{"event_type": "up", "name": "f", "scan_code": 33, "time": 1491442622.9056144}
"""
import sys
sys.path.append('..')

# Also available as just `python -m keyboard`.
from keyboard import __main__