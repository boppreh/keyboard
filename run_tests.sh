# Requires `sudo python3 -m pip install coverage`
coverage3 run -m keyboard._keyboard_tests && coverage3 run -am keyboard._mouse_tests && coverage report
