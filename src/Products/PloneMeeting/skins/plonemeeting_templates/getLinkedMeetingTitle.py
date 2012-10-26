## Python Script "getLinkedMeetingTitle.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Return the title of the linked meeting. This script use a Manager proxy role so the title is always available even when the meeting is not...
##

meeting = context.getMeeting()
if meeting:
    return meeting.portal_plonemeeting.formatDate(meeting.getDate(), prefixed=True)
