## Script (Python) "paste_items"
##bind container=container
##bind context=context
##bind namespace=
##bind state=state
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Paste meetingItems into the parent/this folder
##

from AccessControl import Unauthorized
from ZODB.POSException import ConflictError
from Products.CMFPlone import PloneMessageFactory as _

msgtype='error'
if context.cb_dataValid:
    try:
        tool = context.portal_plonemeeting
        # Check that we can paste items
        # Check that items we want to paste are in the same meetingConfig
        tool.checkMayPasteItems(context, context.REQUEST['__cp'], applyPaste=True)
        context.plone_utils.addPortalMessage(_(u'Item(s) pasted.'))
        msgtype='info'
        return state
    except ConflictError:
        raise
    except ValueError, error:
        msg = _(error) or _(u'Disallowed to paste item(s).')
    except (Unauthorized, 'Unauthorized'):
        msg=_(u'Unauthorized to paste item(s).')
    except: # fallback
        msg=_(u'Paste could not find clipboard content.')

context.plone_utils.addPortalMessage(msg, type=msgtype)
return state.set(status='failure')
