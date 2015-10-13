from AccessControl import Unauthorized
from zope.i18n import translate
from Products.Five import BrowserView
from Products.PloneMeeting.utils import _itemNumber_to_storedItemNumber


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
        oldIndexIsInteger = not bool(oldIndex % 100)
        itemNumberIsInteger = not bool(itemNumber % 100)
        if oldIndexIsInteger and itemNumberIsInteger:
            return True

    def _compute_value_to_add(self, itemNumber):
        """ """
        itemNumberIsInteger = not bool(itemNumber % 100)
        if itemNumberIsInteger:
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
                itemsList = meeting.getItems(ordered=True)
                if moveNumber < oldIndex:
                    # We must move the item closer to the first items (up)
                    for item in itemsList:
                        itemNumber = item.getItemNumber()
                        if (itemNumber < oldIndex) and (itemNumber >= moveNumber):
                            if self._is_part_of_same_set(oldIndex, itemNumber):
                                item.setItemNumber(itemNumber + self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])
                        elif itemNumber == oldIndex:
                            item.setItemNumber(moveNumber)
                            item.reindexObject(idxs=['getItemNumber'])
                else:
                    # We must move the item closer to the last items (down)
                    for item in itemsList:
                        itemNumber = item.getItemNumber()
                        if itemNumber == oldIndex:
                            item.setItemNumber(moveNumber)
                            item.reindexObject(idxs=['getItemNumber'])
                        elif (itemNumber > oldIndex) and (itemNumber <= moveNumber):
                            if self._is_part_of_same_set(oldIndex, itemNumber):
                                item.setItemNumber(itemNumber - self._compute_value_to_add(itemNumber))
                                item.reindexObject(idxs=['getItemNumber'])

        # when items order on meeting changed, it is considered modified
        meeting.notifyModified()
