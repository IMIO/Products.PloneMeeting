#!/bin/sh
/srv/archgenxml/agxtrunk/bin/archgenxml --cfg generate.conf PloneMeeting.zargo -o ..

# remove the uselessly created 'locales' now managed by imio.pm.locales
rm -rf ../locales
