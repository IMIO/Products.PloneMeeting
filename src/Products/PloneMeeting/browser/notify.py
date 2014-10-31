from zope.event import notify
from Products.Archetypes.event import EditBegunEvent
from Products.Archetypes.event import EditCancelledEvent
from Products.Five import BrowserView


class NotifyEvent(BrowserView):
    """This is used to notify some events from various places."""

    def notifyEditBegunEvent(self):
        notify(EditBegunEvent(self.context))

    def notifyEditCancelledEvent(self):
        notify(EditCancelledEvent(self.context))

