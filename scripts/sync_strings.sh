#!/bin/sh

cd ../rabbitvcs

# Find files from gtkbuilder (.xml)
find . -type f | grep \.xml | grep -v \.svn | sort > ../POTFILES.glade.in
sed -i 's|\.\/||g' ../POTFILES.glade.in

# Find python files (.py)
echo "util/helper.py" > ../POTFILES.py.in
find . -type f | egrep '(ui)' | grep \.py | grep -v \.svn | grep -v \.pyc | sort >> ../POTFILES.py.in
sed -i 's|\.\/||g' ../POTFILES.py.in

# Extract gettext strings
xgettext -L Python --keyword=_ --keyword=N_ -o ../po/RabbitVCS.pot -f ../POTFILES.py.in
xgettext -j -L Glade -o ../po/RabbitVCS.pot -f ../POTFILES.glade.in

# Cleanup
cat ../POTFILES.py.in ../POTFILES.glade.in > ../po/POTFILES.in
rm ../POTFILES.py.in ../POTFILES.glade.in
