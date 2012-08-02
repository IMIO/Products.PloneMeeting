## Script (Python) "showPasteMeetingItemAction"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=

# Show the action if :
# We have a content to paste
if not context.cb_dataValid():
    return False

# We are in PloneMeeting
meetingConfig = context.portal_plonemeeting.getMeetingConfig(context)
if not meetingConfig:
    return False

return True
