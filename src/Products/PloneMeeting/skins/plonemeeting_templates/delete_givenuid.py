## Python Script "delete_givenuid.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=selected_uid
##title=Deletes an object

rq = context.REQUEST
# Get the logger
import logging
from AccessControl import Unauthorized

logger = logging.getLogger('PloneMeeting')
user = context.portal_membership.getAuthenticatedMember()

# Get the object to delete
obj = context.uid_catalog(UID=selected_uid)[0].getObject()
objectUrl = obj.absolute_url()
parent = obj.getParentNode()
grandParent = None

event = rq.get('event_time', '')
if event:
    # We must not delete an object, but an event in the object's history
    context.portal_plonemeeting.deleteHistoryEvent(obj, event)
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
    except AttributeError, ae:
        mayDelete = True

# Delete the object if allowed
removeParent = False
if mayDelete:
    msg = {'message':'object_deleted', 'type':'info'}
    logMsg = '%s at %s deleted by "%s"' % \
             (obj.meta_type, obj.absolute_url_path(), user.id)
    # In the case of a meeting item, delete annexes, too.
    if obj.meta_type == 'MeetingItem':
        obj.removeAllAnnexes()
        if obj.hasMeeting():
            obj.getMeeting().removeItem(obj)
    elif obj.meta_type == 'MeetingFile':
        item = obj.getItem()
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
                for item in obj.getItems(): obj.removeGivenObject(item)
            allLateItems = obj.getLateItems()
            if allLateItems:
                logger.info('Removing %d late item(s)...' % len(allLateItems))
                for item in obj.getLateItems(): obj.removeGivenObject(item)
            if obj.getParentNode().id == obj.id:
                # We are on an archive site, and the meeting is in a folder
                # that we must remove, too.
                removeParent = True
                grandParent = parent.getParentNode()

    # Do a final check before calling a Manager proxy roled script
    # this is done because we want to workaround a Plone design strange
    # behaviour where a user needs to have the 'Delete objects' permission
    # on the object AND on his container to be able to remove the object.
    # if we check that we can really remove it, call a script to do the
    # work. This just to be sure that we have "Delete objects" on the container.
    if user.has_permission("Delete objects", obj):
        try:
            context.removeGivenObject(obj)
            logger.info(logMsg)
            if removeParent: context.removeGivenObject(parent)
        except Exception, e:
            # Catch here Exception like BeforeDeleteException
            msg = {'message':e, 'type':'error'}
    else:
        raise Unauthorized
else:
    msg = {'message':'cant_delete_object', 'type':'error'}

# Redirect the user to the correct page and display the correct message.
refererUrl = rq['HTTP_REFERER']
if not refererUrl.startswith(objectUrl):
    urlBack = refererUrl
else:
    # we were on the object, redirect to the home page of the current meetingConfig
    # redirect to the exact home page url or the portal_message is lost
    mc = context.portal_plonemeeting.getMeetingConfig(context)
    app = context.portal_plonemeeting.getPloneMeetingFolder(mc.id)
    urlBack = context.meeting_folder_view(app)

# Add the message. If I try to get plone_utils directly from context
# (context.plone_utils), in some cases (ie, the user does not own context),
# Unauthorized is raised (?).
context.portal_plonemeeting.plone_utils.addPortalMessage(**msg)
return rq.RESPONSE.redirect(urlBack)
