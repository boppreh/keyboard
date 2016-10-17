cp description.md README.md
echo -e '\n\n# API\n#### Table of Contents\n\n' >> README.md
python3 ../docstring2markdown/docstring2markdown.py keyboard "https://github.com/boppreh/keyboard/blob/master" >> README.md
