from AccessControl import Unauthorized
from zope.i18n import translate
from Products.Five import BrowserView
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber


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


class ChangeItemOrderView(BrowserView):
    """
      Manage the functionnality that change item order on a meeting.
      Change one level up/down or to a given p_moveNumber.
    """

    def _is_part_of_same_set(self, oldIndex, itemNumber):
        """Is p_itemNumber part of same set that p_oldIndex?
           A set is like :
           - 200 is in same set as 300, 400 or 500 but not as 301;
           - 201 is in same set as 202, 203 or 212 but not 300 or 302;
        """
        oldIndexIsInteger = _is_integer(oldIndex)
        itemNumberIsInteger = _is_integer(itemNumber)
        if oldIndexIsInteger and itemNumberIsInteger:
            return True

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

        # Move the item
        if nbOfItems >= 2:
            oldIndex = self.context.getItemNumber()
            if not moveType == 'number':
                # switch the items
                if moveType == 'up':
                    if oldIndex == 100:
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
                oldIndex = self.context.getItemNumber()
                self.context.setItemNumber(moveNumber)
                self.context.reindexObject(idxs=['getItemNumber'])
                # get items again now that context number was updated
                # we do another query to Meeting.getItems than previous one
                # because it use memoize
                items = meeting.getItems(ordered=True, **{'dummy': True})
                if moveNumber < oldIndex:
                    # We moved the item up
                    previousNumber = 0
                    for item in items:
                        itemNumber = item.getItemNumber()
                        if item == self.context:
                            if previousNumber > moveNumber:
                                # we already passed by other item having same number but that was increased...
                                continue
                        elif itemNumber == moveNumber:
                            item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                            item.reindexObject(idxs=['getItemNumber'])
                        else:
                            itemNumberIsInteger = _is_integer(itemNumber)
                            if (itemNumberIsInteger and itemNumber != _to_integer(previousNumber) + 100) or \
                               (not itemNumberIsInteger and itemNumber != previousNumber + 1):
                                if itemNumberIsInteger:
                                    item.setItemNumber(_to_integer(previousNumber) +
                                                       _compute_value_to_add(itemNumber))
                                else:
                                    item.setItemNumber(previousNumber + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                        previousNumber = item.getItemNumber()
                else:
                    # We moved the item down
                    previousNumber = 0
                    oldIndexIsInteger = _is_integer(oldIndex)
                    for item in items:
                        itemNumber = item.getItemNumber()
                        itemNumberIsInteger = _is_integer(itemNumber)
                        moveNumberIsInteger = _is_integer(moveNumber)
                        if item == self.context:
                            # moving 2 to 4
                            if (oldIndexIsInteger and moveNumberIsInteger):
                                pass
                            # moving 2.1 to 4
                            elif (not oldIndexIsInteger and moveNumberIsInteger):
                                pass
                            # moving 2 to 4.2
                            elif (oldIndexIsInteger and not moveNumberIsInteger):
                                item.setItemNumber(moveNumber - 100)
                                item.reindexObject(idxs=['getItemNumber'])
                            else:
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
                            else:
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
                            elif (not oldIndexIsInteger and moveNumberIsInteger) and itemNumber > moveNumber:
                                item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                            # moving 2 to 4.2
                            elif (oldIndexIsInteger and not moveNumberIsInteger) and itemNumber > oldIndex:
                                # decrease from 1 integer (100) every except > subnumbers of same interger, so 4.3, 4.4, ...
                                if (_to_integer(itemNumber) == _to_integer(moveNumber)) and itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                else:
                                    item.setItemNumber(itemNumber - 100)
                                    item.reindexObject(idxs=['getItemNumber'])
                            else:
                                # moving 2.1 to 3.2
                                # (not oldIndexIsInteger and not moveNumberIsInteger)
                                # decrease subnumbers of oldIndex integer that were >
                                if (_to_integer(itemNumber) == _to_integer(oldIndex)) and itemNumber > oldIndex:
                                    item.setItemNumber(itemNumber - _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])
                                # increase subnumbers of moveIndex integer that are >
                                if (_to_integer(itemNumber) == _to_integer(moveNumber)) and itemNumber > moveNumber:
                                    item.setItemNumber(itemNumber + _compute_value_to_add(itemNumber))
                                    item.reindexObject(idxs=['getItemNumber'])

        # when items order on meeting changed, it is considered modified
        meeting.notifyModified()
