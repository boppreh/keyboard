test: tests

tests:
	coverage2 run -m keyboard._keyboard_tests
	coverage2 run -am keyboard._mouse_tests
	coverage3 run -am keyboard._keyboard_tests
	coverage3 run -am keyboard._mouse_tests
	coverage3 report && coverage3 html

release:
	python3 make_release.py

readme:
	PYTHONIOENCODING=utf-8 python3 ../docstring2markdown/docstring2markdown.py keyboard "https://github.com/boppreh/keyboard/blob/master" > README.md

clean:
	rm -rfv dist build coverage_html_report keyboard.egg-info

install:
	pip install .

all: clean tests readme release
