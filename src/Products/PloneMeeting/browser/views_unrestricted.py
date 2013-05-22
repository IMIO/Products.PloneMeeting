import logging
from AccessControl import Unauthorized
from AccessControl.SecurityManagement import newSecurityManager, getSecurityManager, setSecurityManager

from zope.component import getMultiAdapter

from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.tests.base.security import OmnipotentUser


class DeleteGivenUidView(BrowserView):
    """
      Method to ease deletion of elements.
      Callable using self.portal.restrictedTraverse('@@delete_givenuid)(element.UID()) in the code
      and using classic traverse in a url : http://nohost/plonesite/delete_givenuid?selected_uid=anUID
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def __call__(self, selected_uid):
        rq = self.request
        # Get the logger

        logger = logging.getLogger('PloneMeeting')
        user = self.context.portal_membership.getAuthenticatedMember()

        # Get the object to delete
        obj = self.context.uid_catalog(UID=selected_uid)[0].getObject()
        objectUrl = obj.absolute_url()
        parent = obj.aq_inner.aq_parent

        event = rq.get('event_time', '')
        if event:
            # We must not delete an object, but an event in the object's history
            self.context.portal_plonemeeting.deleteHistoryEvent(obj, event)
            return rq.RESPONSE.redirect(rq['HTTP_REFERER'])

        # Determine if the object can be deleted or not
        if obj.meta_type == 'MeetingFile':
            item = obj.getItem()
            mayDelete = True
            if item:
                mayDelete = item.wfConditions().mayDeleteAnnex(obj)
        else:
            try:
                mayDelete = obj.wfConditions().mayDelete()
            except AttributeError:
                mayDelete = True

        # Delete the object if allowed
        removeParent = False
        if mayDelete:
            msg = {'message': 'object_deleted',
                   'type': 'info'}
            logMsg = '%s at %s deleted by "%s"' % \
                     (obj.meta_type, obj.absolute_url_path(), user.id)
            # In the case of a meeting item, delete annexes, too.
            if obj.meta_type == 'MeetingItem':
                obj.removeAllAnnexes()
                if obj.hasMeeting():
                    obj.getMeeting().removeItem(obj)
            elif obj.meta_type == 'MeetingFile':
                if item:
                    item.updateAnnexIndex(obj, removeAnnex=True)
                    item.updateHistory(
                        'delete', obj, decisionRelated=obj.isDecisionRelated())
                    if item.willInvalidateAdvices():
                        item.updateAdvices(invalidate=True)
            elif obj.meta_type == 'Meeting':
                if rq.get('wholeMeeting', None):
                    # Delete all items and late items in the meeting
                    allItems = obj.getItems()
                    if allItems:
                        logger.info('Removing %d item(s)...' % len(allItems))
                        for item in obj.getItems():
                            obj.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(item)
                    allLateItems = obj.getLateItems()
                    if allLateItems:
                        logger.info('Removing %d late item(s)...' % len(allLateItems))
                        for item in obj.getLateItems():
                            obj.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(item)
                    if obj.getParentNode().id == obj.id:
                        # We are on an archive site, and the meeting is in a folder
                        # that we must remove, too.
                        removeParent = True

            # remove the object
            # just manage BeforeDeleteException because we rise it ourself
            from OFS.ObjectManager import BeforeDeleteException
            try:
                self.context.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(obj)
                logger.info(logMsg)
                # remove the parent object if necessary
                if removeParent:
                    self.context.restrictedTraverse('@@pm_unrestricted_methods').removeGivenObject(parent)
            except BeforeDeleteException, exc:
                msg = {'message': exc.message,
                       'type': 'error'}
            # fall back to original user
        else:
            msg = {'message': 'cant_delete_object',
                   'type': 'error'}

        # Redirect the user to the correct page and display the correct message.
        refererUrl = rq['HTTP_REFERER']
        if not refererUrl.startswith(objectUrl):
            urlBack = refererUrl
        else:
            # we were on the object, redirect to the home page of the current meetingConfig
            # redirect to the exact home page url or the portal_message is lost
            mc = self.context.portal_plonemeeting.getMeetingConfig(self.context)
            app = self.context.portal_plonemeeting.getPloneMeetingFolder(mc.id)
            urlBack = self.context.meeting_folder_view(app)

        # Add the message. If I try to get plone_utils directly from context
        # (context.plone_utils), in some cases (ie, the user does not own context),
        # Unauthorized is raised (?).
        self.context.portal_plonemeeting.plone_utils.addPortalMessage(**msg)
        return rq.RESPONSE.redirect(urlBack)


class UnrestrictedMethodsView(BrowserView):
    """
      This class contains every methods behaving as unrestricted.
      These methods were formerly Manager proxy roled python Scripts.
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def removeGivenObject(self, object_to_delete):
        """
          This view removes a given object even if the logged in user can not...
          This is protected because only callable in the code.
          Receives the object (so it is not callable in the UI) and removes it.
        """
        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
        # Do a final check before calling the view
        # this is done because we want to workaround a Plone design strange
        # behaviour where a user needs to have the 'Delete objects' permission
        # on the object AND on his container to be able to remove the object.
        # if we check that we can really remove it, call a script to do the
        # work. This just to be sure that we have "Delete objects" on the content.
        if member.has_permission("Delete objects", object_to_delete):
            # save current SecurityManager to fall back to it after deletion
            oldsm = getSecurityManager()
            # login as an omnipotent user
            newSecurityManager(None, PMOmnipotentUser().__of__(self.portal.aq_inner.aq_parent.acl_users))
            # removes the object
            parent = object_to_delete.aq_inner.aq_parent
            try:
                parent.manage_delObjects([object_to_delete.getId(), ])
            except Exception, exc:
                # in case something wrong happen, make sure we fall back to original user
                setSecurityManager(oldsm)
                raise exc
            # fall back to original user
            setSecurityManager(oldsm)
        else:
            raise Unauthorized

    def getLinkedMeetingTitle(self):
        """
          Return the title of the linked meeting in case current user can not access the meeting.
        """
        meeting = self.context.getMeeting()
        if meeting:
            return meeting.portal_plonemeeting.formatDate(meeting.getDate(), prefixed=True)

    def getLinkedMeetingDate(self):
        """
          Return the date of the linked meeting in case current user can not access the meeting.
        """
        meeting = self.context.getMeeting()
        if meeting:
            return meeting.getDate()


class ItemSign(BrowserView):
    """
      Item is signed after it as been closed and so, user has no more "Modify portal content" permission.
      We use maySignItem to check if the current user can actually sign/unsignItem.
    """
    IMG_TEMPLATE = u'<img class="%s" src="%s" title="%s" name="%s" %s />'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()

    def toggle(self, UID):
        member = self.portal.restrictedTraverse('@@plone_portal_state').member()
        if not self.context.adapted().maySignItem(member):
            raise Unauthorized

        # save current SecurityManager to fall back to it after deletion
        oldsm = getSecurityManager()
        # login as an omnipotent user
        newSecurityManager(None, PMOmnipotentUser().__of__(self.portal.aq_inner.aq_parent.acl_users))
        uid_catalog = getToolByName(self.context, 'uid_catalog')
        item = uid_catalog(UID=UID)[0].getObject()
        itemIsSigned = not item.getItemIsSigned()
        item.setItemIsSigned(itemIsSigned)
        item.reindexObject(idxs=('getItemIsSigned',))
        setSecurityManager(oldsm)

        # check again if member can signItem now that it has been signed
        # by default, when an item is signed, it can not be unsigned
        maySignItem = item.maySignItem(member)
        if itemIsSigned:
            filename = 'itemIsSignedYes.png'
            name = 'itemIsSignedNo'
            if maySignItem:
                title_msgid = 'item_is_signed_yes_edit'
            else:
                title_msgid = 'item_is_signed_yes'
        else:
            filename = 'itemIsSignedNo.png'
            name = 'itemIsSignedYes'
            if maySignItem:
                title_msgid = 'item_is_signed_no_edit'
            else:
                title_msgid = 'item_is_signed_no'

        title = item.utranslate(title_msgid,
                                domain="PloneMeeting")
        portal_state = getMultiAdapter((self.context, self.request), name=u"plone_portal_state")
        portal_url = portal_state.portal_url()
        src = "%s/%s" % (portal_url, filename)
        # manage the onclick if the user still may change the value
        # let onclick be managed by the jQuery method if we do not need to change it
        # just redefines it to "" if we really want to specify that we do not want an onclick
        onclick = not maySignItem and 'onclick=""' or ''
        # manage the applied css_class : if the user still may edit the value, use 'itemIsSignedEditable'
        # if he can no more change the value, do not use a css_class
        css_class = maySignItem and 'itemIsSignedEditable' or ''
        html = self.IMG_TEMPLATE % (css_class, src, title, name, onclick)
        return html


class PMOmnipotentUser(OmnipotentUser):
    """
      Omnipotent for PloneMeeting.  Heritates from Products.CMFCore's OmnipotentUser
      but add a missing 'has_role' method...
    """
    def has_role(self, roles, obj=None):
        return True
