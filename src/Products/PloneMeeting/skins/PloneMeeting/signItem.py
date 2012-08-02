## Script (Python) "signItem"
##title=Apply or remove a signature on an item (field 'itemIsSigned')
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=

from AccessControl import Unauthorized

member = context.portal_membership.getAuthenticatedMember()

if not context.adapted().maySignItem(member):
    raise Unauthorized
else:
    return context.restrictedTraverse('@@toggle_item_is_signed').toggle(context.UID())