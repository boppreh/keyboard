set -e

cd docs
rm -rf source
sphinx-apidoc -o source ../keyboard
make html
