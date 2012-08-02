## Python Script "meetingitem_discuss.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=itemUid,discussAction
##title=Updates the "to discuss" flag on a meeting item

item = context.uid_catalog(UID=itemUid)[0].getObject()
if discussAction == 'ask':
    # I must send a mail to MeetingManagers for notifying them that a reviewer
    # wants to discuss this item.
    sendMailEnabled = item.sendMailIfRelevant('askDiscussItem',
        'MeetingManager', isRole=True)
    if sendMailEnabled:
        msgId = 'to_discuss_ask_mail_sent'
    else:
        msgId = 'to_discuss_ask_mail_not_sent'
    context.plone_utils.addPortalMessage(
        item.translate(msgId, domain='PloneMeeting'))
else:
    # Backward compatibility for plugins not using toggleDiscuss
    # I must toggle the "toDiscuss" switch on the item
    toDiscuss = (discussAction == 'yes')
    item.setToDiscuss(toDiscuss)
    item.adapted().onDiscussChanged(toDiscuss)
return context.portal_plonemeeting.gotoReferer()
