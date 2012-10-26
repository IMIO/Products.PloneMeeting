## Python Script "meeting_presentseveralitems.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=uids=None
##title=Manage a massive presentation of selected items to a meeting

for uid in uids.split(',')[:-1]:
    obj = context.uid_catalog.searchResults(UID=uid)[0].getObject()
    context.portal_workflow.doActionFor(obj, 'present')

if not uids:
    msg = context.translate('no_selected_items', domain='PloneMeeting')
    context.plone_utils.addPortalMessage(msg)

return context.portal_plonemeeting.gotoReferer()
