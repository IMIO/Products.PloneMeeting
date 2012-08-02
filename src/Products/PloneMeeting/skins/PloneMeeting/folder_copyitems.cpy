## Controller Python Script "folder_copyitems"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=
##title=Copy items from a folder to the clipboard
##
## This is based on Plone's folder_copy script
## We just filter objects to be sure that copied objects are items
## and that the user is in the same proposingGroup
##

from OFS.CopySupport import CopyError
from Products.CMFPlone.utils import transaction_note
from Products.CMFPlone import PloneMessageFactory as _

REQUEST=context.REQUEST
if REQUEST.has_key('paths'):
    ids = [p.split('/')[-1] or p.split('/')[-2] for p in REQUEST['paths']]
    
    #check that copied items are OK...
    #only MeetingItems and self proposinggroup that current user
    for id in ids:
        try:
            item = getattr(context, id)
            if item.meta_type != "MeetingItem":
                msg = _(u"You can not copy this element : '${title}' is not an item.", mapping={u'title' : item.Title().decode('utf-8')})
                raise CopyError, msg
            #we use this method that do what we need here and a little more...
            if not item.showCopyItemAction():
                msg = _(u"You can not copy this item : ${title}, your are not in the same proposing group (${proposingGroup}).", mapping={u'title':item.Title(), u'proposingGroup':context.displayValue(item.listProposingGroup(), item.getProposingGroup())})
                raise CopyError, msg
        except CopyError:
            context.plone_utils.addPortalMessage(msg)
            return state.set(status = 'failure')

    try:
        context.manage_copyObjects(ids, REQUEST, REQUEST.RESPONSE)
    except CopyError:
        message = _(u'One or more items not copyable.')
        context.plone_utils.addPortalMessage(message)
        return state.set(status = 'failure')
    except AttributeError:
        message = _(u'One or more selected items is no longer available.')
        context.plone_utils.addPortalMessage(message)
        return state.set(status = 'failure')

    transaction_note('Copied %s from %s' % (str(ids), context.absolute_url()))

    message = _(u'${count} item(s) copied.', mapping={u'count' : len(ids)})

    context.plone_utils.addPortalMessage(message)
    return state

context.plone_utils.addPortalMessage(_(u'Please select one or more items to copy.'))
return state.set(status='failure')
