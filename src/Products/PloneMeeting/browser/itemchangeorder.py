from AccessControl import Unauthorized
from Products.Five import BrowserView
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber
from zope.i18n import translate


def _to_integer(number):
    """
      Return the entire value of p_number :
      - 200 is 200;
      - 202 is 200;
      - 305 is 300.
    """
    return number / 100 * 100


def _is_integer(number):
    """Is p_number an integer item number or a subnumber?"""
    return not bool(number % 100)


def _compute_value_to_add(number):
    """ """
    number_is_integer = _is_integer(number)
    if number_is_integer:
        return 100
    else:
        return 1


def _use_same_integer(number1, number2):
    """Is p_number1 part using same integer as p_number2?
       200 is using same integer as 201, 202.
    """
    if _to_integer(number1) == _to_integer(number2):
        return True
    return False


class ChangeItemOrderView(BrowserView):
    """
      Manage the functionnality that change item order on a meeting.
      Change one level up/down or to a given p_moveNumber.
    """

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
        oldIndex = self.context.getItemNumber()

        # Calibrate and validate moveValue
        if moveType == 'number':
            # we receive 2.1, 2.5 or 2.10 but we store 201, 205 and 210 so it is orderable integers
            moveNumber = _itemNumber_to_storedItemNumber(wishedNumber)
            moveNumberIsInteger = _is_integer(moveNumber)
            # Is this move allowed ?
            if moveNumber == itemNumber:
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_did_not_move',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
            # check that moveNumber is not < 1 or not > next possible item
            # check that the moveNumber is valid, aka integer (4) or max 2 decimal number (4.1 or 4.13)
            # check also that if we use a subnumber, the previous exists (22.2 exists if we specified 22.3)
            # check finally that if we are moving an item to a subnumber,
            # the master exists (moving to 12.1, 12 has to exist)
            last_item = items[-1]
            moving_last_item = self.context == last_item
            if (moveNumber < 100) or \
               (not moving_last_item and moveNumber > _to_integer(last_item.getItemNumber()) + 99) or \
               (not moveNumberIsInteger and len(wishedNumber.split('.')[1]) > 2) or \
               (not moveNumberIsInteger and
                (not meeting.getItemByNumber(moveNumber - 1) or
                 moveNumber - 1 == oldIndex)):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_illegal_move',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
        else:
            # down, must not be last
            # up, must not be first
            if (moveType == 'down' and self.context == items[-1]) or \
               (moveType == 'up' and self.context == items[0]):
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_illegal_switch',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return
            # 'down' or 'up' may not switch an integer and a subnumber
            currentIsInteger = _is_integer(self.context.getItemNumber())
            illegal_swtich = False
            if moveType == 'down':
                nextIsInteger = _is_integer(self.context.getSiblingItem('next'))
                if (currentIsInteger and not nextIsInteger) or (not currentIsInteger and nextIsInteger):
                    illegal_swtich = True
            elif moveType == 'up':
                previousIsInteger = _is_integer(self.context.getSiblingItem('previous'))
                if (currentIsInteger and not previousIsInteger) or (not currentIsInteger and previousIsInteger):
                    illegal_swtich = True
            if illegal_swtich:
                self.context.plone_utils.addPortalMessage(
                    translate(msgid='item_illegal_switch',
                              domain='PloneMeeting',
                              context=self.request),
                    type='warning')
                return

        # Move the item
        if nbOfItems >= 2:
            if not moveType == 'number':
                # switch the items
                if moveType == 'up':
                    if oldIndex == 100:
                        # moving first item 'up', does not change anything
                        # actually it is not possible in the UI because the 'up'
                        # icon is not displayed on the first item
                        return
                    otherNumber = self.context.getSiblingItem('previous')
                else:
                    # moveType == 'down'
                    otherNumber = self.context.getSiblingItem('next')
                otherItem = meeting.getItemByNumber(otherNumber)
                self.context.setItemNumber(otherItem.getItemNumber())
                self.context.reindexObject(idxs=['getItemNumber'])
                otherItem.setItemNumber(oldIndex)
                otherItem.reindexObject(idxs=['getItemNumber'])
            else:
                # Move the item to an absolute position
                oldIndex = self.context.getItemNumber()
                self.context.setItemNumber(moveNumber)
                self.context.reindexObject(idxs=['getItemNumber'])
                # get items again now that context number was updated
                # we do another query to Meeting.getItems than previous one
                # because it use memoize
                items = meeting.getItems(ordered=True, **{'dummy': True})
                oldIndexIsInteger = _is_integer(oldIndex)
                oldIndexHasSubnumbers = meeting.getItemByNumber(oldIndex + 1)
                if moveNumber < oldIndex:
                    # We moved the item up
                    for item in items:
                        itemNumber = item.getItemNumber()
                        # moved item
                        if item == self.context:
                            # moving 4 to 2
                            if (oldIndexIsInteger and moveNumberIsInteger):
                                pass
                            # moving 4.1 to 2
                            elif (not oldIndexIsInteger and moveNumberIsInteger):
                                pass
                            # moving 4 to 2.1
                            elif (oldIndexIsInteger and not moveNumberIsInteger):
                                pass
                            elif (not oldIndexIsInteger and not moveNumberIsInteger):
                                # moving 3.1 to 2.2
                                pass
                        # item that was at the moveNumber position
                        elif itemNumber == moveNumber:
                            # moving 4 to 2
                            if (oldIndexIsInteger and moveNumberIsInteger):
                                item.setItemNumber(itemNumber + 100)
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 4.1 to 2
                            elif (not oldIndexIsInteger and moveNumberIsInteger):
                                item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 4 to 2.1
                            elif (oldIndexIsInteger and not moveNumberIsInteger):
                                item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            elif (not oldIndexIsInteger and not moveNumberIsInteger):
                                # moving 3.1 to 2.2
                                item.setItemNumber(itemNumber + 1)
                                item.reindexObject(idxs=['getItemNumber'])
                        # other items
                        else:
                            # moving 4 to 2
                            if (oldIndexIsInteger and moveNumberIsInteger) and \
                               (itemNumber < oldIndex and itemNumber > moveNumber):
                                item.setItemNumber(itemNumber + 100)
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 4.1 to 2
                            elif (not oldIndexIsInteger and moveNumberIsInteger) and itemNumber > moveNumber:
                                # subnumbers of oldIndex (4.2, 4.3, ...) must be decreased of 0.1
                                if _use_same_integer(itemNumber, oldIndex) and itemNumber > oldIndex:
                                    item.setItemNumber(itemNumber + 100 - _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                else:
                                    item.setItemNumber(itemNumber + 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            # moving 4 to 2.1
                            elif (oldIndexIsInteger and not moveNumberIsInteger):
                                # moving master, decrease old subnumbers if > oldIndex
                                if _use_same_integer(itemNumber, oldIndex):
                                    item.setItemNumber(itemNumber - _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                # increase subnumbers > moveNumber
                                if _use_same_integer(itemNumber, moveNumber) and itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                # decrease every number > oldIndex if oldIndex was not a master number
                                elif not oldIndexHasSubnumbers and itemNumber > oldIndex:
                                    item.setItemNumber(itemNumber - 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            elif (not oldIndexIsInteger and not moveNumberIsInteger):
                                # moving 3.1 to 2.2
                                # decrease oldIndex subnumbers of 0.1 (3.2 to 3.1, 3.3 to 3.2)
                                if _use_same_integer(itemNumber, oldIndex) and itemNumber > oldIndex:
                                    item.setItemNumber(itemNumber - 1)
                                    item.reindexObject(idxs=['getItemNumber'])
                                # increase moveNumber subnumber of 0.1 (2.2 to 2.3, 2.3 to 2.4)
                                elif _use_same_integer(itemNumber, moveNumber) and itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber + 1)
                                    item.reindexObject(idxs=['getItemNumber'])
                else:
                    # We moved the item down
                    for item in items:
                        itemNumber = item.getItemNumber()
                        if item == self.context:
                            # moving 2 to 4
                            if (oldIndexIsInteger and moveNumberIsInteger):
                                pass
                            # moving 2.1 to 4
                            elif (not oldIndexIsInteger and moveNumberIsInteger):
                                pass
                            # moving 2 to 4.2
                            elif (oldIndexIsInteger and not moveNumberIsInteger):
                                if not oldIndexHasSubnumbers:
                                    item.setItemNumber(moveNumber - 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            elif (not oldIndexIsInteger and not moveNumberIsInteger):
                                # moving 2.1 to 3.2
                                # (not oldIndexIsInteger and not moveNumberIsInteger)
                                pass
                        elif itemNumber == moveNumber:
                            # moving 2 to 4
                            if (oldIndexIsInteger and moveNumberIsInteger):
                                item.setItemNumber(itemNumber - _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 2.1 to 4
                            elif (not oldIndexIsInteger and moveNumberIsInteger):
                                item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 2 to 4.2
                            elif (oldIndexIsInteger and not moveNumberIsInteger):
                                item.setItemNumber(itemNumber - 100 + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            elif (not oldIndexIsInteger and not moveNumberIsInteger):
                                # moving 2.1 to 3.2
                                # (not oldIndexIsInteger and not moveNumberIsInteger)
                                item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                        else:
                            # moving 2 to 4
                            if (oldIndexIsInteger and moveNumberIsInteger) and \
                               (itemNumber > oldIndex and itemNumber < moveNumber):
                                item.setItemNumber(itemNumber - 100)
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 2.1 to 4
                            elif (not oldIndexIsInteger and moveNumberIsInteger) and itemNumber > oldIndex:
                                # decrease elements having same subnumber as oldIndex
                                if (_use_same_integer(itemNumber, oldIndex)):
                                    item.setItemNumber(itemNumber - _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                elif itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber + 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            # moving 2 to 4.2
                            elif (oldIndexIsInteger and not moveNumberIsInteger) and itemNumber > oldIndex:
                                # decrease from 1 but add + 0.1 to subnumbers > moveNumber
                                if (_use_same_integer(itemNumber, moveNumber)) and itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber - 100 + _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                # decrease subnumbers of master we moved
                                elif (_use_same_integer(itemNumber, oldIndex)):
                                    item.setItemNumber(itemNumber - _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                elif not oldIndexHasSubnumbers:
                                    item.setItemNumber(itemNumber - 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            elif (not oldIndexIsInteger and not moveNumberIsInteger):
                                # moving 2.1 to 3.2
                                # (not oldIndexIsInteger and not moveNumberIsInteger)
                                # decrease subnumbers of oldIndex integer that were >
                                if (_use_same_integer(itemNumber, oldIndex)) and itemNumber > oldIndex:
                                    item.setItemNumber(itemNumber - _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                # increase subnumbers of moveIndex integer that are >
                                if (_use_same_integer(itemNumber, moveNumber)) and itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])

        # when items order on meeting changed, it is considered modified,
        # do this before updateItemReferences
        meeting.notifyModified()

        # update item references starting from minus between oldIndex and new itemNumber
        meeting.updateItemReferences(startNumber=min(oldIndex, self.context.getItemNumber()))
