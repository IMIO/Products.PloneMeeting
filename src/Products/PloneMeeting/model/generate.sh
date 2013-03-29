#!/bin/sh
/srv/archgenxml/agx27/bin/archgenxml --cfg generate.conf PloneMeeting.zargo -o ..

echo "Removing useless 'locales' folder managed by imio.pm.locales"
rm -rf ../locales
echo "Removing 'locales' registration from configure.zcml"
sed '/registerTranslations/d' ../configure.zcml >> ../tmp.zcml
rm ../configure.zcml
mv ../tmp.zcml ../configure.zcml
