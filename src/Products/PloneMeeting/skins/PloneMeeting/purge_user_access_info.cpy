## Controller Python Script "purge_user_access_info.cpy"
##bind container=container
##bind context=context
##bind namespace=
##bind state=state
##parameters=uids=None
##title=Removes user access info related to deleted users

deletedEntries = context.purgeAccessInfo()
if deletedEntries:
    msg = 'access_info_purged'
else:
    msg = 'no_access_info_purged'

context.plone_utils.addPortalMessage(
    context.translate(msg, {'usersRemoved': str(deletedEntries)},
                     domain="PloneMeeting"))

return state.set(status='success')
