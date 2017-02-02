"""
This little guy streamliens the release process of Python packages.

By running `python3 make_release.py` it'll do the following tasks automatically:

- Update README by calling `make_readme.sh` if this file exists.
- Check PyPI RST long_description syntax.
- Show the latest version from CHANGES.md and ask for a new version number.
- Open vim to allow you to edit the list of changes for this new version, showing a list of commits since the last version.
- Prepend your list of changes to CHANGES.md (and ask if you want to commit it now).
- Add a git tag to the current commit.
- Push tag to GitHub.
- Publish a new release to GitHub, asking for the authentication token (optional).
- Publish a new release on PyPI.

Suggested way to organize your project for a smooth process:

- Use Markdown everywhere.
- Keep a description of your project in the package's docstring.
- Generate your README from the package docstring plus API docs.
- Convert your package docstring to RST in setup.py and use that as long_description.
- Use raw semantic versioning for CHANGES.md and PyPI (e.g. 2.3.1), and prepend 'v' for git tags and releases (e.g. v2.3.1).

"""
import re
import sys
import os
from subprocess import run, check_output
import atexit
import requests

run(['bash', '-c', 'find . \( -name "*.py" -o -name "*.sh" -o -name "* .md" \) -exec dos2unix {} \;'], check=True)
run(['bash', '-c', 'make clean readme tests'], check=True)
run(['python', 'setup.py', 'check', '-rms'], check=True)

version_pattern = '(\d+(?:\.\d+)+)'
last_version = re.search(version_pattern, open('CHANGES.md').read()).group(1)
print('The last version was: {}'.format(last_version))
new_version = input('Enter new version or leave empty to only update metadata: ') if len(sys.argv) == 1 else sys.argv[1]
if new_version.startswith('v'):
    new_version = new_version[1:]

if not new_version:
    if input('Commit README.md files? ').lower().startswith('y'):
        run(['git', 'add', 'README.md'])
        run(['git', 'commit', '-m', 'Update README'])
        run(['git', 'push'])
    run(['python', 'setup.py', 'register'], check=True)
    exit()

assert re.fullmatch(version_pattern, new_version)

commits = check_output(['git', 'log', 'v{}..HEAD'.format(last_version), '--oneline'], universal_newlines=True)
with open('message.txt', 'w') as message_file:
    atexit.register(lambda: os.remove('message.txt'))

    message_file.write('\n\n\n')
    message_file.write('# Enter changes one per line like this:\n')
    message_file.write('# - Added `foobar`.\n\n\n')
    message_file.write('# As a reminder, here\'s the last commits since version {}:\n\n'.format(last_version))
    for line in commits.strip().split('\n'):
        message_file.write('# {}\n'.format(line))

run(['vim', 'message.txt'])
with open('message.txt') as message_file:
    lines = [line for line in message_file.readlines() if not line.startswith('#')]
message = ''.join(lines).strip()
if not message:
    print('Aborting release due to empty message.')
    exit()
with open('message.txt', 'w') as message_file:
    message_file.write(message)

with open('CHANGES.md') as changes_file:
    old_changes = changes_file.read()
with open('CHANGES.md', 'w') as changes_file:
    changes_file.write('# {}\n\n{}\n\n\n{}'.format(new_version, message, old_changes))


tag_name = 'v' + new_version
if input('Commit README.md and CHANGES.md files? ').lower().startswith('y'):
    run(['git', 'add', 'CHANGES.md', 'README.md'])
    run(['git', 'commit', '-m', 'Update changes for {}'.format(tag_name)])
    run(['git', 'push'])
run(['git', 'tag', '-a', tag_name, '--file', 'message.txt'], check=True)
run(['git', 'push', 'origin', tag_name], check=True)

token = input('To make a release enter your GitHub repo authorization token: ').strip()
if token:
    git_remotes = check_output(['git', 'remote', '-v']).decode('utf-8')
    repo_path = re.search(r'([^/]+/[^/. ]+)(?:\.git)? \(push\)', git_remotes).group(1)
    releases_url = 'https://api.github.com/repos/{}/releases'.format(repo_path)
    print(releases_url)
    release = {
        "tag_name": tag_name,
        "target_commitish": "master",
        "name": tag_name,
        "body": message,
        "draft": False,
        "prerelease": False,
    }
    response = requests.post(releases_url, json=release, headers={'Authorization': 'token ' + token})
    print(response.status_code, response.text)

run(['python', 'setup.py', 'sdist', '--format=zip', 'bdist', '--format=zip', 'bdist_wheel', '--universal', 'bdist_wininst', 'register', 'upload'], check=True)
