## Script (Python) "showFolderCopyMeetingItemAction"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=

meetingConfig = context.portal_plonemeeting.getMeetingConfig(context)
if not meetingConfig:
    return False
# We are in PloneMeeting
return True
