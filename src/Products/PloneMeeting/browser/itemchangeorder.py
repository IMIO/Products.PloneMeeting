from AccessControl import Unauthorized
from zope.i18n import translate
from Products.Five import BrowserView
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from Products.PloneMeeting.utils import _storedItemNumber_to_itemNumber


class ChangeItemOrderView(BrowserView):
    """
      Manage the functionnality that change item order on a meeting.
      Change one level up/down or to a given p_moveNumber.
    """

    def _compute_value_to_add(self, itemNumber):
        """ """
        if float(itemNumber / 100).is_integer():
            return 100
        else:
            # XXX to be changed
            return 1

    def __call__(self, moveType, wishedNumber=None):
        """
          Change the items order on a meeting.
          This is an unrestricted method so a MeetingManager can change items
          order even if some items are no more movable because decided
          (and so no more 'Modify portal content' on it).
          We double check that current user can actually mayChangeItemsOrder.
          Anyway, this method move an item, one level up/down or at a given position.
        """
        # we do this unrestrictively but anyway respect the Meeting.mayChangeItemsOrder
        meeting = self.context.getMeeting()

        if not meeting.wfConditions().mayChangeItemsOrder():
            raise Unauthorized

        itemNumber = self.context.getItemNumber()

        # Move the item up (-1), down (+1) or at a given position ?
        if moveType == 'number':
            try:
                float(wishedNumber)
                # In this case, wishedNumber specifies the new position where
                # the item must be moved.
            except (ValueError, TypeError):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_number_invalid',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return

        nbOfItems = len(meeting.getRawItems())
        items = meeting.getItems(ordered=True)

        # Calibrate and validate moveValue
        if moveType == 'number':
            # we receive 2.1, 2.5 or 2.10 but we store 201, 205 and 210 so it is orderable integers
            moveNumber = _itemNumber_to_storedItemNumber(wishedNumber)
            # Is this move allowed ?
            if moveNumber == itemNumber:
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_did_not_move',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
            if (moveNumber < 100) or (moveNumber > items[-1].getItemNumber()):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_illegal_move',
                              mapping={'nbOfItems': nbOfItems},
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
            # we are using a decimal (like 1.1 or 12.4) check that it is allowed
            # if we specified "3.1", item number "3" must exist,
            # if we specified "3.3", item number "3.2" must exist
            if bool(moveNumber % 100):
                previousItemNumber = moveNumber - 1
                previousItem = meeting.getItemByNumber(previousItemNumber)
                if not previousItem or previousItem == self.context:
                    self.context.plone_utils.addPortalMessage(
                        translate(msgid='item_illegal_decimal',
                                  domain='PloneMeeting',
                                  context=self.request),
                        type='warning')
                    return

        # Move the item
        if nbOfItems >= 2:
            oldIndex = self.context.getItemNumber()
            if not moveType == 'number':
                # switch the items
                if moveType == 'up':
                    if oldIndex == 1:
                        # moving first item 'up', does not change anything
                        # actually it is not possible in the UI because the 'up'
                        # icon is not displayed on the first item
                        return
                    otherNumber = self.context.getSiblingItemNumber('previous')
                else:
                    # moveType == 'down'
                    otherNumber = self.context.getSiblingItemNumber('next')
                otherItem = meeting.getItemByNumber(otherNumber)
                self.context.setItemNumber(otherItem.getItemNumber())
                self.context.reindexObject(idxs=['getItemNumber'])
                otherItem.setItemNumber(oldIndex)
                otherItem.reindexObject(idxs=['getItemNumber'])
            else:
                # Move the item to an absolute position
                # are oldIndex and moveNumber, integer numbers or subnumbers?
                oldIndexIsInteger = not bool(oldIndex % 100)
                moveNumberIsInteger = not bool(moveNumber % 100)
                if not moveNumberIsInteger:
                    newInteger, newDecimal = str(wishedNumber).split('.')
                    newInteger = int(newInteger)
                    newDecimal = int(newDecimal.ljust(2, '0'))
                if moveNumber < oldIndex:
                    # We must move the item closer to the first items (up)
                    if oldIndexIsInteger and moveNumberIsInteger:
                        movingMasterElement = bool(meeting.getItemByNumber(oldIndex + 1))
                        movingToMasterElement = bool(meeting.getItemByNumber(moveNumber + 1))
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer = itemNumber % 100
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['getItemNumber'])
                            elif integer == oldIndex:
                                # if we moved the first element of subelements
                                # (like '2' and there is '2.1', '2.2')
                                # we need to remove 0.1 to following elements...
                                if movingToMasterElement:
                                    itemNumber += 100
                                item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            elif itemNumber >= moveNumber:
                                item.setItemNumber(itemNumber + 100)
                                item.reindexObject(idxs=['getItemNumber'])
                    elif oldIndexIsInteger and not moveNumberIsInteger:
                        # moving "13" to "12.1" or "12.5"
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer, decimal = _storedItemNumber_to_itemNumber(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['getItemNumber'])
                            elif itemNumber >= moveNumber:
                                # an itemNumber with decimal using same integer as moveNumber?
                                if integer == newInteger:
                                    item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber) - 1)
                                    item.reindexObject(idxs=['getItemNumber'])
                                elif itemNumber >= oldIndex:
                                    item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                    elif not oldIndexIsInteger and moveNumberIsInteger:
                        # moving "12.1" to "10" or "5"
                        oldInteger, oldDecimal = _storedItemNumber_to_itemNumber(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        # moving "7.3" to "7"
                        movingToSelfMaster = bool(oldInteger == moveNumber)
                        movingToMasterElement = bool(meeting.getItemByNumber(moveNumber + 1))
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer, decimal = _storedItemNumber_to_itemNumber(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['getItemNumber'])
                            elif movingToSelfMaster:
                                if moveNumber == oldInteger and integer == oldInteger and itemNumber < oldIndex:
                                    item.setItemNumber(itemNumber + self._compute_value_to_add(oldIndex))
                                    item.reindexObject(idxs=['getItemNumber'])
                            elif itemNumber >= moveNumber:
                                # like "12.2" that needs to become "12.1"
                                # special case when moving "7.2" to "7", just update the "7 and 7.x"
                                if moveNumber == oldInteger and integer == oldInteger:
                                    if itemNumber < oldIndex:
                                        item.setItemNumber(itemNumber + self._compute_value_to_add(oldIndex))
                                elif integer == oldInteger and decimal > oldDecimal:
                                    item.setItemNumber(itemNumber + 100 - self._compute_value_to_add(itemNumber))
                                else:
                                    item.setItemNumber(itemNumber + 100)
                                item.reindexObject(idxs=['getItemNumber'])
                    elif not oldIndexIsInteger and not moveNumberIsInteger:
                        # moving "4.2" to "2.1" or "12.4" to "12.2"
                        oldInteger, oldDecimal = _storedItemNumber_to_itemNumber(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        # in case we move "2.3" to "2.1"
                        movingSelfElement = bool(oldInteger == newInteger)
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer, decimal = str(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['getItemNumber'])
                            elif itemNumber >= moveNumber:
                                if movingSelfElement:
                                    if integer == newInteger and decimal < oldDecimal and decimal >= newDecimal:
                                        item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                else:
                                    # origin
                                    if integer == oldInteger and decimal > oldDecimal:
                                        item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                    # destination
                                    elif integer == newInteger and decimal >= newDecimal:
                                        item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                else:
                    if oldIndexIsInteger and moveNumberIsInteger:
                        # We must move the item closer to the last items (down)
                        movingMasterElement = bool(meeting.getItemByNumber(oldIndex + 100))
                        movingToMasterElement = bool(meeting.getItemByNumber(moveNumber + 100))
                        for item in items:
                            itemNumber = item.getItemNumber()
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['getItemNumber'])
                            elif (itemNumber > oldIndex) and (itemNumber <= moveNumber):
                                item.setItemNumber(itemNumber - 100)
                                item.reindexObject(idxs=['getItemNumber'])
                    elif oldIndexIsInteger and not moveNumberIsInteger:
                        # moving "4" to "12.1" or "12.5"
                        # here the problem is that if we move a "4" that has no subnumbers
                        # to "12.2", "12.2" will actually become "11.2"...
                        # we need to know if it has subnumbers
                        movingMasterElement = bool(meeting.getItemByNumber(oldIndex + 1))
                        oldInteger, oldDecimal = _storedItemNumber_to_itemNumber(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer, decimal = str(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if not movingMasterElement:
                                # we need to decrease number of every following elements
                                if itemNumber == oldIndex:
                                    item.setItemNumber(moveNumber - 1)
                                    item.reindexObject(idxs=['getItemNumber'])
                                # take every items before, including every 12.x
                                elif itemNumber > oldIndex:
                                    if integer == newInteger and decimal >= newDecimal:
                                        item.setItemNumber(itemNumber - 100 + self._compute_value_to_add(itemNumber))
                                    else:
                                        # use same integer as
                                        item.setItemNumber(itemNumber - 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            else:
                                # changing this item will not affect number of any other items
                                # that the subitems in which the item is inserted and from which it is sent
                                if itemNumber == oldIndex:
                                    item.setItemNumber(moveNumber)
                                    item.reindexObject(idxs=['getItemNumber'])
                                elif itemNumber > oldIndex:
                                    if integer == newInteger and decimal >= newDecimal:
                                        item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                    elif integer == oldInteger and decimal > oldDecimal:
                                        # use same integer as
                                        item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                    elif not oldIndexIsInteger and moveNumberIsInteger:
                        # moving "2.1" to "10" or "5"
                        oldInteger, oldDecimal = _storedItemNumber_to_itemNumber(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        # are we replacing a master item, aka an item having subnumered items?
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer, decimal = _storedItemNumber_to_itemNumber(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                            elif integer == oldInteger and decimal > oldDecimal:
                                item.setItemNumber(itemNumber - self._compute_value_to_add(oldIndex))
                            elif itemNumber >= moveNumber:
                                item.setItemNumber(itemNumber + 100)
                            item.reindexObject(idxs=['getItemNumber'])
                    elif not oldIndexIsInteger and not moveNumberIsInteger:
                        # moving "2.2" to "2.4" or "2.3" to "6.3"
                        oldInteger, oldDecimal = _storedItemNumber_to_itemNumber(oldIndex).split('.')
                        oldInteger = int(oldInteger)
                        oldDecimal = int(oldDecimal)
                        for item in items:
                            itemNumber = item.getItemNumber()
                            integer, decimal = _storedItemNumber_to_itemNumber(itemNumber).split('.')
                            integer = int(integer)
                            decimal = int(decimal)
                            if itemNumber == oldIndex:
                                item.setItemNumber(moveNumber)
                                item.reindexObject(idxs=['getItemNumber'])
                            elif itemNumber >= oldIndex:
                                if integer == oldInteger and decimal > oldDecimal:
                                    item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                elif integer == newInteger and decimal >= newDecimal:
                                    item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
        # when items order on meeting changed, it is considered modified
        meeting.notifyModified()
