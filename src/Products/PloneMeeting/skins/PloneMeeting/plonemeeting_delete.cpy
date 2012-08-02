## Controller Python Script "plonemeeting_delete"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=
##title=Delete objects from a folder in the meetingfolder_view
##

from Products.CMFPlone import PloneMessageFactory as _

req = context.REQUEST
paths=req.get('paths', [])

tool = context.portal_plonemeeting

status='failure'
message=_(u'Please select one or more items to delete.')

success, failure = tool.deleteObjectsByPaths(paths)

if success:
    status='success'
    message = _(u'Item(s) deleted.')

if failure:
    message = _(failure)

context.plone_utils.addPortalMessage(message)
return state.set(status=status)
