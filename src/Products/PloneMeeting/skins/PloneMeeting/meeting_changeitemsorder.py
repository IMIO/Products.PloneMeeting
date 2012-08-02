## Python Script "meeting_changeitemsorder"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=itemUid,moveType,moveNumber
##title=Allows to move up or down an item into a meeting, from 1 or several places

tool = context.portal_plonemeeting

# Move the item up (-1), down (+1) or at a given position ?
if moveType == 'number':
    isDelta = False
    try:
        move = int(moveNumber)
        # In this case, moveNumber specifies the new position where
        # the item must be moved.
    except ValueError:
        context.plone_utils.addPortalMessage(
            context.translate('item_number_invalid', domain='PloneMeeting'))
        return tool.gotoReferer()
else:
    isDelta = True
    if moveType == 'up':
        move = -1
    elif moveType == 'down':
        move = 1

# Find the item to move (in "normal" or "late" items lists)
itemToMove = None
catalogRes = context.uid_catalog(UID=itemUid)
if catalogRes:
    itemToMove = catalogRes[0].getObject()
    isLate = itemUid in context.getRawLateItems()
    if isLate:
        nbOfItems = len(context.getRawLateItems())
    else:
        nbOfItems = len(context.getRawItems())

# Calibrate and validate moveValue
if itemToMove and (not isDelta):
    # Recompute p_move according to "normal" or "late" items list
    if isLate:
        move -= len(context.getRawItems())
    # Is this move allowed ?
    if move in (itemToMove.getItemNumber(), itemToMove.getItemNumber()+1):
        context.plone_utils.addPortalMessage(
            context.translate('item_did_not_move', domain='PloneMeeting'))
        return tool.gotoReferer()
    if (move < 1) or (move > (nbOfItems+1)):
        context.plone_utils.addPortalMessage(
            context.translate('item_illegal_move', domain='PloneMeeting'))
        return tool.gotoReferer()

# Move the item
if itemToMove and (nbOfItems >= 2):
    if isDelta:
        # Move the item with a delta of +1 or -1
        oldIndex = itemToMove.getItemNumber()
        newIndex = oldIndex + move
        if (newIndex >= 1) and (newIndex <= nbOfItems):
            # Find the item having newIndex and intervert indexes
            if isLate: itemsList = context.getLateItems()
            else: itemsList = context.getItems()
            for item in itemsList:
                if item.getItemNumber() == newIndex:
                    item.setItemNumber(oldIndex)
                    break
            itemToMove.setItemNumber(newIndex)
    else:
        # Move the item to an absolute position
        oldIndex = itemToMove.getItemNumber()
        if isLate: itemsList = context.getLateItems()
        else: itemsList = context.getItems()
        if move < oldIndex:
            # We must move the item closer to the first items (up)
            for item in itemsList:
                itemNumber = item.getItemNumber()
                if (itemNumber < oldIndex) and (itemNumber >= move):
                    item.setItemNumber(itemNumber+1)
                elif itemNumber == oldIndex:
                    item.setItemNumber(move)
        else:
            # We must move the item closer to the last items (down)
            for item in itemsList:
                itemNumber = item.getItemNumber()
                if itemNumber == oldIndex:
                    item.setItemNumber(move-1)
                elif (itemNumber > oldIndex) and (itemNumber < move):
                    item.setItemNumber(itemNumber-1)

return tool.gotoReferer()
