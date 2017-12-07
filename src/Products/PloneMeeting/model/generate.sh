#!/bin/sh
archgenxml --cfg generate.conf PloneMeeting.zargo -o tmp

# only keep workflows
cp -rf tmp/profiles/default/workflows ../profiles/default
rm -rf tmp
