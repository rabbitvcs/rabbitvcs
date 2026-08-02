#!/bin/sh

# Sync our translation template file with the actual strings
# 1. Extracts strings from gtkbuilder xml files into .h files
# 2. Extracts gettext strings from py files
# 3. Deletes the glade .h files

cd ..

for i in `find . | grep '\.xml' | grep -v '\.svn' | grep -v '\.xml\.h'`;
do
	intltool-extract --type=gettext/glade $i
done

cd rabbitvcs

echo "util/helper.py" > POTFILES.in
find . -type f | egrep '(ui|.xml)' | grep -v \.svn | grep -v \.h | grep -v \.pyc >> POTFILES.in
sed -i 's|\.xml|.xml.h|g' POTFILES.in
sed -i 's|\.\/||g' POTFILES.in

mv POTFILES.in ../po/POTFILES.in

xgettext -L Python --keyword=_ --keyword=N_ -o ../po/RabbitVCS.pot -f ../po/POTFILES.in

for i in `find . | grep '\.xml\.h' | grep -v '\.svn'`;
do
	rm -f $i
done
