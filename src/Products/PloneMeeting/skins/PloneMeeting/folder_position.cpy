## Controller Python Script "folder_position"
##title=Move objects in a ordered folder
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=position, id, template_id='folder_contents'
##

from Products.CMFPlone import PloneMessageFactory as _
allObjectIds = context.objectIds()
pos = allObjectIds.index(id)
metaType = getattr(context, id).meta_type
mtObjectIds = context.objectIds(metaType)
delta = 1

if position.lower()=='up':
    previousFound = False
    while not previousFound and ((pos-delta)>0):
        previousId = allObjectIds[pos-delta]
        if previousId not in mtObjectIds:
            delta += 1
        else:
            previousFound = True
    if previousFound:
        context.moveObjectsUp(id, delta=delta)

if position.lower()=='down':
    nextFound = False
    while not nextFound and ((pos+delta)< len(allObjectIds)):
        nextId = allObjectIds[pos+delta]
        if nextId not in mtObjectIds:
            delta += 1
        else:
            nextFound = True
    if nextFound:
        context.moveObjectsDown(id, delta=delta)

if position.lower()=='top':
    context.moveObjectsToTop(id)

if position.lower()=='bottom':
    context.moveObjectsToBottom(id)

# order folder by field
# id in this case is the field
if position.lower()=='ordered':
    context.orderObjects(id)

context.plone_utils.reindexOnReorder(context)

msg=_(u'Item\'s position has changed.')
context.plone_utils.addPortalMessage(msg)

return state
