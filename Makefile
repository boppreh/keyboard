test: tests
tests:
	python2 -m coverage run -m keyboard._keyboard_tests
	python2 -m coverage run -am keyboard._mouse_tests
	python -m coverage run -am keyboard._keyboard_tests
	python -m coverage run -am keyboard._mouse_tests
	python -m coverage report && coverage3 html

format:
	black --line-length 120 --exclude="keyboard/_keyboard_tests.py" keyboard || true

docs:
	python ../docstring2markdown/docstring2markdown.py keyboard "https://github.com/boppreh/keyboard/blob/master" > api_reference.md

build: format docs tests keyboard setup.py README.md CHANGES.md MANIFEST.in
	find . \( -name "*.py" -o -name "*.sh" -o -name "* .md" \) -exec dos2unix {} \;
	python setup.py sdist --format=zip bdist_wheel && twine check dist/*

release:
	python make_release.py

clean:
	rm -rfv dist build coverage_html_report keyboard.egg-info
