try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()

from setuptools import setup

setup(
    name='keyboard',
    version='0.6.1',
    author='BoppreH',
    author_email='boppreh@gmail.com',
    packages=['keyboard'],
    url='https://github.com/boppreh/keyboard',
    license='MIT',
    description='Hook and simulate keyboard events on Windows and Linux',
    keywords = 'keyboard hook simulate hotkey',
    long_description=long_description,

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ],
)
