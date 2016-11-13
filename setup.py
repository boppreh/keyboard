"""
Usage instructions:

- If you are installing: `python setup.py install`
- If you are developing: `python setup.py sdist bdist --format=zip bdist_wheel --universal`
"""
try:
    long_description = open('README.rst').read()
except FileNotFoundError:
    try:
        import pypandoc
        long_description = pypandoc.convert('README.md', 'rst')
    except ImportError:
        long_description = open('README.md').read()

import re
last_version = re.search('(\d+(?:\.\d+)+)', open('CHANGES.md').read()).group(1)

from setuptools import setup
setup(
    name='keyboard',
    version=last_version,
    author='BoppreH',
    author_email='boppreh@gmail.com',
    packages=['keyboard'],
    url='https://github.com/boppreh/keyboard',
    license='MIT',
    description='Hook and simulate keyboard events on Windows and Linux',
    keywords = 'keyboard hook simulate hotkey',
    long_description=long_description,

    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)