## Script (Python) "displayContentsTab"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##

# XXX change by PloneMeeting, we do not show contents tab if current object layout
# is 'folder_contents', it is the case for the MeetingConfig 'itemtemplates' folder
# and for every folders added under it
if context.getLayout() == 'folder_contents':
    return False


# We won't deprecate this just yet, because people expect it to be acquired
# from context and frequently override it on their content classes.
return context.restrictedTraverse('@@plone').displayContentsTab()
