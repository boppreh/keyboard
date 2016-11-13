import re
import sys
import os
from subprocess import run, check_output
import atexit
import requests

run(['bash', 'make_readme.sh'], check=True)

if not os.path.exists('README.rst'):
    import pypandoc
    long_description = pypandoc.convert_file('README.md', 'rst', outputfile='README.rst', extra_args=['--no-wrap'])
    atexit.register(lambda: os.remove('README.rst'))
run(['python', 'setup.py', 'check', '-rms'], check=True)

version_pattern = '(\d+(?:\.\d+)+)'
last_version = re.search(version_pattern, open('CHANGES.md').read()).group(1)
print('The last version was: {}'.format(last_version))
new_version = input('Enter new version: ') if len(sys.argv) == 1 else sys.argv[1]
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
message = '\n'.join(lines).strip()
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
if input('Commit CHANGES.md file? ').lower().startswith('y'):
    run(['git', 'add', 'CHANGES.md'])
    run(['git', 'commit', '-m', 'Update changes for {}'.format(tag_name)])
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