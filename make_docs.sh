set -e

cd docs
rm -rf source
sphinx-apidoc -o source ../keyboard
# sudo required to import keyboard module.
sudo make html
