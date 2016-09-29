# -*- coding: utf-8 -*-
#
# File: events.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


import logging
logger = logging.getLogger('PloneMeeting')
import md5

from AccessControl import Unauthorized
from DateTime import DateTime
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from OFS.ObjectManager import BeforeDeleteException
from zope.annotation import IAnnotations
from zope.event import notify
from zope.i18n import translate
from zope.lifecycleevent import IObjectRemovedEvent
from Products.CMFCore.WorkflowCore import WorkflowException
from plone.app.textfield import RichText
from plone.app.textfield.value import RichTextValue
from plone import api
from collective.documentviewer.async import queueJob
from collective.documentviewer.settings import STORAGE_VERSION
from collective.iconifiedcategory.interfaces import IIconifiedPreview
from imio.actionspanel.utils import unrestrictedRemoveGivenObject
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.xhtml import storeExternalImagesLocally
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.config import ADVICE_GIVEN_HISTORIZED_COMMENT
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.utils import _addImagePermission
from Products.PloneMeeting.utils import addRecurringItemsIfRelevant
from Products.PloneMeeting.utils import AdviceAfterAddEvent
from Products.PloneMeeting.utils import AdviceAfterModifyEvent
from Products.PloneMeeting.utils import applyOnTransitionFieldTransform
from Products.PloneMeeting.utils import ItemAfterTransitionEvent
from Products.PloneMeeting.utils import MeetingAfterTransitionEvent
from Products.PloneMeeting.utils import meetingTriggerTransitionOnLinkedItems
from Products.PloneMeeting.utils import sendMailIfRelevant

podTransitionPrefixes = {'MeetingItem': 'pod_item', 'Meeting': 'pod_meeting'}


# Code executed after a workflow transition has been triggered
def do(action, event):
    '''What must I do when a transition is triggered on a meeting or item?'''
    objectType = event.object.meta_type
    actionsAdapter = event.object.wfActions()
    # Execute some actions defined in the corresponding adapter
    actionMethod = getattr(actionsAdapter, action)
    actionMethod(event)
    if objectType == 'MeetingItem':
        # Update every local roles : advices, copyGroups, powerObservers, budgetImpactEditors, ...
        event.object.updateLocalRoles(triggered_by_transition=event.transition.id)
        # Send mail regarding advices to give if relevant
        event.object.sendAdviceToGiveMailIfRelevant(event.old_state.id, event.new_state.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "item_state_changed_%s" % event.transition.id, 'View')
        # apply on transition field transform if any
        applyOnTransitionFieldTransform(event.object, event.transition.id)
    elif objectType == 'Meeting':
        # update every local roles
        event.object.updateLocalRoles()
        # Add recurring items to the meeting if relevant
        addRecurringItemsIfRelevant(event.object, event.transition.id)
        # Send mail if relevant
        sendMailIfRelevant(event.object, "meeting_state_changed_%s" % event.transition.id, 'View')
        # trigger some transitions on contained items depending on
        # MeetingConfig.onMeetingTransitionItemTransitionToTrigger
        meetingTriggerTransitionOnLinkedItems(event.object, event.transition.id)

    # update modification date upon state change
    event.object.setModificationDate(DateTime())


def onItemTransition(item, event):
    '''Called whenever a transition has been fired on an item.'''
    if not event.transition or (item != event.object):
        return
    transitionId = event.transition.id
    if transitionId.startswith('backTo'):
        action = 'doCorrect'
    elif transitionId.startswith('item'):
        action = 'doItem%s%s' % (transitionId[4].upper(), transitionId[5:])
    else:
        action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)

    # check if we need to send the item to another meetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(item)
    if item.queryState() in cfg.getItemAutoSentToOtherMCStates():
        otherMCs = item.getOtherMeetingConfigsClonableTo()
        for otherMC in otherMCs:
            # if already cloned to another MC, pass.  This could be the case
            # if the item is accepted, corrected then accepted again
            if not item._checkAlreadyClonedToOtherMC(otherMC):
                item.cloneToOtherMeetingConfig(otherMC, automatically=True)

    # if 'takenOverBy' is used, it is automatically set after a transition
    # to last user that was taking the item over or to nothing
    wf_state = "%s__wfstate__%s" % (cfg.getItemWorkflow(), event.new_state.getId())
    item.adapted().setHistorizedTakenOverBy(wf_state)
    # notify an ItemAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting item transition
    notify(ItemAfterTransitionEvent(item))
    # just reindex the entire object
    item.reindexObject()


def onMeetingTransition(meeting, event):
    '''Called whenever a transition has been fired on a meeting.'''
    if not event.transition or (meeting != event.object):
        return
    transitionId = event.transition.id
    action = 'do%s%s' % (transitionId[0].upper(), transitionId[1:])
    do(action, event)
    # notify a MeetingAfterTransitionEvent for subplugins so we are sure
    # that it is called after PloneMeeting meeting transition
    notify(MeetingAfterTransitionEvent(meeting))
    # just reindex the entire object
    event.object.reindexObject()


def onItemBeforeTransition(item, event):
    '''Called before a transition is triggered on an item.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed nevertheless?
    pass


def onMeetingBeforeTransition(meeting, event):
    '''Called before a transition is triggered on a meeting.'''
    # when raising exceptions in a WF script, this needs to be done in the
    # before transition or state is changed nevertheless?
    if event.new_state.id == 'closed':
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(meeting)
        if 'return_to_proposing_group' in cfg.getWorkflowAdaptations():
            # raise a WorkflowException in case there are items still in state 'returned_to_proposing_group'
            additional_catalog_query = {'review_state': 'returned_to_proposing_group'}
            if meeting.getItems(useCatalog=True, additional_catalog_query=additional_catalog_query):
                msg = _('Can not close a meeting containing items returned to proposing group!')
                raise WorkflowException(msg)


def onGroupTransition(mGroup, event):
    '''Called whenever a transition has been fired on a MeetingGroup.'''
    if not event.transition or (mGroup != event.object):
        return
    transitionId = event.transition.id

    tool = api.portal.get_tool('portal_plonemeeting')
    if transitionId == 'deactivate':
        # Remove the group from every meetingConfigs.selectableCopyGroups
        for mc in tool.objectValues('MeetingConfig'):
            for ploneGroupId in mGroup.getPloneGroups(idsOnly=True):
                selectableCopyGroups = list(mc.getSelectableCopyGroups())
                if ploneGroupId in selectableCopyGroups:
                    selectableCopyGroups.remove(ploneGroupId)
                mc.setSelectableCopyGroups(selectableCopyGroups)
        # Remove the group from every meetingConfigs.selectableAdvisers
        for mc in tool.objectValues('MeetingConfig'):
            selectableAdvisers = list(mc.getSelectableAdvisers())
            if mGroup.getId() in mc.getSelectableAdvisers():
                selectableAdvisers.remove(mGroup.getId())
            mc.setSelectableAdvisers(selectableAdvisers)
        # add a portal_message explaining what has been done to the user
        plone_utils = api.portal.get_tool('plone_utils')
        plone_utils.addPortalMessage(
            _('meetinggroup_removed_from_meetingconfigs_selectablecopygroups_selectableadvisers'),
            'info')


def onGroupWillBeRemoved(group, event):
    '''Checks if the current meetingGroup can be deleted:
      - it can not be linked to an existing meetingItem;
      - it can not be referenced in an existing meetingConfig;
      - the linked ploneGroups must be empty of members.'''
    # Do lighter checks first...  Check that the meetingGroup is not used
    # in a meetingConfig
    # If we are trying to remove the whole Plone Site, bypass this hook.
    # bypass also if we are in the creation process
    if event.object.meta_type == 'Plone Site' or group._at_creation_flag:
        return

    tool = api.portal.get_tool('portal_plonemeeting')
    groupId = group.getId()
    for mc in tool.objectValues('MeetingConfig'):
        # The meetingGroup can be referenced in selectableAdvisers/selectableCopyGroups.
        customAdvisersGroupIds = [customAdviser['group'] for customAdviser in mc.getCustomAdvisers()]
        if groupId in customAdvisersGroupIds or \
           groupId in mc.getPowerAdvisersGroups() or \
           groupId in mc.getSelectableAdvisers():
            raise BeforeDeleteException(translate("can_not_delete_meetinggroup_meetingconfig",
                                                  domain="plone",
                                                  context=group.REQUEST))
        for groupSuffix in MEETING_GROUP_SUFFIXES:
            ploneGroupId = group.getPloneGroupId(groupSuffix)
            if ploneGroupId in mc.getSelectableCopyGroups():
                raise BeforeDeleteException(translate("can_not_delete_meetinggroup_meetingconfig",
                                                      domain="plone",
                                                      context=group.REQUEST))
    # Then check that every linked Plone group is empty because we are
    # going to delete them.
    portal = api.portal.get()
    for suffix in MEETING_GROUP_SUFFIXES:
        ploneGroupId = group.getPloneGroupId(suffix)
        # using acl_users.source_groups.listAssignedPrincipals will
        # show us 'not found' members
        groupMembers = portal.acl_users.source_groups.listAssignedPrincipals(ploneGroupId)
        # groupMembers is something like :
        # [('a_removed_user', '<a_removed_user: not found>'), ('pmCreator1', 'pmCreator1'), ]
        groupsMembersWithoutNotFound = [member for member in groupMembers if 'not found' not in member[1]]
        if groupsMembersWithoutNotFound:
            raise BeforeDeleteException(translate("can_not_delete_meetinggroup_plonegroup",
                                                  domain="plone",
                                                  context=group.REQUEST))
    # And finally, check that meetingGroup is not linked to an existing item.
    # In the configuration
    for cfg in tool.objectValues('MeetingConfig'):
        for item in (cfg.recurringitems.objectValues('MeetingItem') +
                     cfg.itemtemplates.objectValues('MeetingItem')):
            if item.getProposingGroup() == groupId or \
               groupId in item.getAssociatedGroups():
                raise BeforeDeleteException(
                    translate("can_not_delete_meetinggroup_config_meetingitem",
                              domain="plone",
                              mapping={'url': item.absolute_url()},
                              context=group.REQUEST))
    # In the application
    # most of times, the real groupId is stored, but for MeetingItem.copyGroups, we
    # store suffixed elements of the group, so compute suffixed elements for self and compare
    suffixedGroups = set()
    for groupSuffix in MEETING_GROUP_SUFFIXES:
        suffixedGroups.add(group.getPloneGroupId(groupSuffix))
    catalog = api.portal.get_tool('portal_catalog')
    for brain in catalog(meta_type="MeetingItem"):
        obj = brain.getObject()
        if (obj.getProposingGroup() == groupId) or \
           (groupId in obj.getAssociatedGroups()) or \
           (groupId in obj.adviceIndex) or \
           set(obj.getCopyGroups()).intersection(suffixedGroups):
            # The meetingGroup is linked to an existing item, we can not
            # delete it.
            raise BeforeDeleteException(
                translate("can_not_delete_meetinggroup_meetingitem",
                          domain="plone",
                          context=group.REQUEST))
    # If everything passed correctly, we delete every linked (and empty)
    # Plone groups.
    portal_groups = api.portal.get_tool('portal_groups')
    for suffix in MEETING_GROUP_SUFFIXES:
        ploneGroupId = group.getPloneGroupId(suffix)
        pGroup = portal_groups.getGroupById(ploneGroupId)
        if pGroup:
            portal_groups.removeGroup(ploneGroupId)


def onGroupRemoved(group, event):
    '''Called when a MeetingGroup is removed.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    # clean cache for "Products.PloneMeeting.vocabularies.proposinggroupsvocabulary" and
    # "Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary" vocabularies
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.proposinggroupacronymsvocabulary")
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.askedadvicesvocabulary")


def onItemMoved(item, event):
    '''Called when an item is pasted cut/pasted, we need to update annexIndex.'''
    # this is also called when removing an item, in this case, we do nothing
    if IObjectRemovedEvent.providedBy(event):
        return
    # ???


def onItemAdded(item, event):
    '''This method is called every time a MeetingItem is created, even in
       portal_factory. Local roles defined on an item define who may view
       or edit it. But at the time the item is created in portal_factory,
       local roles are not defined yet. So here we add a temporary local
       role to the currently logged user that allows him to create the
       item. In item.at_post_create_script we will remove this temp local
       role.'''
    user = api.user.get_current()
    item.manage_addLocalRoles(user.getId(), ('MeetingMember',))
    # Add a place to store adviceIndex
    item.adviceIndex = PersistentMapping()
    # Add a place to store emergency changes history
    item.emergency_changes_history = PersistentList()
    # Add a place to store completeness changes history
    item.completeness_changes_history = PersistentList()
    # Add a place to store takenOverBy by review_state user id
    item.takenOverByInfos = PersistentMapping()


def onItemModified(item, event):
    '''Called when an item is modified so we can invalidate caching on linked meeting.'''
    meeting = item.getMeeting()
    if meeting:
        meeting.invalidate_meeting_actions_panel_cache = True

    # reactivate rename_after_creation as long as item is in it's initial_state
    if item._at_rename_after_creation:
        wfTool = api.portal.get_tool('portal_workflow')
        itemWF = wfTool.getWorkflowsFor(item)[0]
        initial_state = itemWF.initial_state
        if initial_state == item.queryState():
            # in case a user of same group is editing the item of another user
            # he does not have the 'Add portal content' permission that is necessary
            # when renaming so do this as Manager
            with api.env.adopt_roles(['Manager']):
                item._renameAfterCreation(check_auto_id=False)


def storeExternalImagesLocallyDexterity(advice):
    '''Store external images of every RichText field of a dexterity object locally.'''
    portal_types = api.portal.get_tool('portal_types')
    fti = portal_types[advice.portal_type]
    schema = fti.lookupSchema()
    for field_id, field in schema._v_attrs.items():
        if isinstance(field, RichText) and getattr(advice, field_id, None):
            # avoid infinite loop because this is called in a ObjectModifiedEvent
            # and we are modifying the advice...
            advice.REQUEST.set('currentlyStoringExternalImages', True)
            newValue = storeExternalImagesLocally(advice, getattr(advice, field_id).output)
            setattr(advice, field_id, RichTextValue(newValue))
            advice.REQUEST.set('currentlyStoringExternalImages', False)


def onAdviceAdded(advice, event):
    '''Called when a meetingadvice is added so we can warn parent item.'''
    # if advice is added because we are pasting, pass as we will remove the advices...
    if advice.REQUEST.get('currentlyPastingItems', False):
        return

    # update advice_row_id if it was not already done before
    # for example in a onAdviceTransition event handler that is called
    # before the onAdviceAdded...
    if not advice.advice_row_id:
        advice._updateAdviceRowId()

    item = advice.getParentNode()
    item.updateLocalRoles()
    # make the entire _advisers group able to edit the meetingadvice
    advice.manage_addLocalRoles('%s_advisers' % advice.advice_group, ('Editor', ))

    # ATContentTypes: Add Image permission
    _addImagePermission(advice)

    # make sure external images used in RichText fields are stored locally
    storeExternalImagesLocallyDexterity(advice)

    # notify our own PM event so we are sure that this event is called
    # after the onAviceAdded event
    notify(AdviceAfterAddEvent(advice))

    # redirect to referer after add if it is not the edit form
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit') and not http_referer.endswith('/@@edit'):
        advice.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')

    # reindexObject in case for example we have custom indexes
    # depending on the advice value
    item.reindexObject()

    # log
    userId = api.user.get_current().getId()
    logger.info('Advice at %s created by "%s".' %
                (advice.absolute_url_path(), userId))


def onAdviceModified(advice, event):
    '''Called when a meetingadvice is modified so we can warn parent item.'''
    if advice.REQUEST.get('currentlyStoringExternalImages', False) is True:
        return

    # update advice_row_id
    advice._updateAdviceRowId()

    item = advice.getParentNode()
    item.updateLocalRoles()

    # make sure external images used in RichText fields are stored locally
    storeExternalImagesLocallyDexterity(advice)

    # notify our own PM event so we are sure that this event is called
    # after the onAviceModified event
    notify(AdviceAfterModifyEvent(advice))

    # reindexObject in case for example we have custom indexes
    # depending on the advice value
    item.reindexObject()

    # log
    userId = api.user.get_current().getId()
    logger.info('Advice at %s edited by "%s".' %
                (advice.absolute_url_path(), userId))


def onAdviceEditFinished(advice, event):
    '''Called when a meetingadvice is edited and we are at the end of the editing process.'''
    item = advice.getParentNode()
    item.updateLocalRoles()

    # redirect to referer after edit if it is not the edit form
    http_referer = item.REQUEST['HTTP_REFERER']
    if not http_referer.endswith('/edit') and not http_referer.endswith('/@@edit'):
        advice.REQUEST.RESPONSE.redirect(http_referer + '#adviceAndAnnexes')


def onAdviceRemoved(advice, event):
    '''Called when a meetingadvice is removed so we can warn parent item.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    item = advice.getParentNode()

    # clean advice inheritance if necessary
    _cleanAdviceInheritance(item, advice.advice_group)

    # do not call this if an advice is removed because the item is removed
    if item not in item.aq_inner.aq_parent.objectValues():
        return

    try:
        item.updateLocalRoles()
    except TypeError:
        # while removing an advice, if it was not anymore in the advice index
        # it can raise a TypeError, this can be the case when using ToolPloneMeeting.pasteItems
        # the newItem has an empty adviceIndex but can contain advices that will be removed
        logger.info('Removal of advice at %s raised TypeError.' % advice.absolute_url_path())

    # reindexObject in case for example we have custom indexes
    # depending on the advice value
    item.reindexObject()


def onAdviceTransition(advice, event):
    '''Called whenever a transition has been fired on an advice.'''
    if not event.transition or (advice != event.object):
        return

    # in transition 'giveAdvice', historize the advice
    # and save item's relevant data if MeetingConfig.historizeItemDataWhenAdviceIsGiven
    # make sure also the 'advice_given_on' data is correct in item's adviceIndex
    if event.transition.id == 'giveAdvice':
        # historize
        advice.versionate_if_relevant(ADVICE_GIVEN_HISTORIZED_COMMENT)
        # manage 'advice_given_on' dates
        parent = advice.getParentNode()
        advice_given_on = advice.get_advice_given_on()
        toLocalizedTime = parent.restrictedTraverse('@@plone').toLocalizedTime
        parent.adviceIndex[advice.advice_group]['advice_given_on'] = advice_given_on
        parent.adviceIndex[advice.advice_group]['advice_given_on_localized'] = toLocalizedTime(advice_given_on)

    _addImagePermission(advice)


def onAnnexAdded(annex, event):
    ''' '''
    parent = annex.getParentNode()
    if '/++add++annex' in annex.REQUEST.getURL():
        annex.REQUEST.RESPONSE.redirect(parent.absolute_url() + '/@@categorized-annexes')

    # if it is an annex added on an item, versionate given advices if necessary
    if parent.meta_type == 'MeetingItem':
        parent._versionateAdvicesOnItemEdit()
        parent.updateHistory('add',
                             annex,
                             decisionRelated=annex.portal_type == 'annexDecision' and True or False)
        if annex.portal_type == 'annex' and parent.willInvalidateAdvices():
            parent.updateLocalRoles(invalidate=True)

        # Potentially I must notify MeetingManagers through email.
        if parent.wfConditions().meetingIsPublished():
            parent.sendMailIfRelevant('annexAdded', 'MeetingManager', isRole=True)

    # update modificationDate, it is used for caching and co
    parent.setModificationDate(DateTime())
    # just reindex the entire object
    parent.reindexObject()

    # log
    userId = api.user.get_current().getId()
    logger.info('Annex at %s created by "%s".' %
                (annex.absolute_url_path(), userId))


def onAnnexEditFinished(annex, event):
    ''' '''
    # redirect to the annexes table view after edit
    if event.object.REQUEST['PUBLISHED'].__name__ == 'edit':
        parent = annex.getParentNode()
        return annex.REQUEST.RESPONSE.redirect(parent.absolute_url() + '/@@categorized-annexes')


def onAnnexRemoved(annex, event):
    '''When an annex is removed, we need to update item (parent).'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    parent = annex.getParentNode()
    # do not call this if an annex is removed because the item is removed
    if parent not in parent.aq_inner.aq_parent.objectValues():
        return

    # if it is an annex added on an item, versionate given advices if necessary
    if parent.meta_type == 'MeetingItem':
        parent._versionateAdvicesOnItemEdit()
        parent.updateHistory('delete',
                             annex,
                             decisionRelated=annex.portal_type == 'annexDecision' and True or False)
        if parent.willInvalidateAdvices():
            parent.updateLocalRoles(invalidate=True)

    # update modification date and SearchableText
    parent.setModificationDate(DateTime())
    # just reindex the entire object
    parent.reindexObject()


def _annexWasUpdatedAfterConversion(annex):
    """If annex.modified is > 'last_updated' value, check that md5 of
       stored file correspond to 'filehash' stored in c.documentviewer annotation."""
    ann = IAnnotations(annex)['collective.documentviewer']
    if annex.modified() > DateTime(ann['last_updated']) and \
       md5.md5(annex.file.data) != ann['filehash']:
        return True
    return False


def onAnnexToPrintChanged(annex, event):
    """ """
    annex = event.object

    # None (deactivated) or False, we return
    if event.new_value is not True:
        # set c.documentviewer back to not converted
        ann = IAnnotations(annex)
        ann['collective.documentviewer'] = PersistentMapping()
        ann['last_updated'] = DateTime('1901/01/01').ISO8601()
        ann['storage_version'] = STORAGE_VERSION
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(annex)
    # in case we are updating an annex that was already converted,
    # c.documentviewer does not manage that, so check if annex.modified
    # after c.documentviewer 'last_updated' value
    if cfg.getAnnexToPrintMode() == 'enabled_for_printing' and \
       (not IIconifiedPreview(annex).converted or _annexWasUpdatedAfterConversion(annex)):
        queueJob(annex)


def onItemEditBegun(item, event):
    '''When an item edit begun, if it is an item in creation, we check that
       if MeetingConfig.itemCreatedOnlyUsingTemplate is True, the user is not trying to create
       an fresh item not from an item template.  Do not check this for items added to the
       configuration (recurring items and item templates).'''
    if item.isTemporary() and not item.isDefinedInTool():
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(item)
        if cfg.getItemCreatedOnlyUsingTemplate():
            raise Unauthorized


def onItemEditCancelled(item, event):
    '''When cancelling an edit, if item is not in portal_factory but have
       the _at_creation to True, it means we are creating an item from a template,
       we need to delete it if first edit was cancelled.'''
    if item._at_creation_flag and not item.isTemporary():
        parent = item.getParentNode()
        parent.manage_delObjects(ids=[item.getId()])


def _cleanAdviceInheritance(item, adviceId):
    '''Clean advice inheritance for given p_adviceId on p_item.'''
    def cleanAdviceInheritanceFor(backPredecessors):
        for backPredecessor in backPredecessors:
            if backPredecessor.adviceIndex[adviceId]['inherited']:
                backPredecessor.adviceIndex[adviceId]['inherited'] = False
                backPredecessor.updateLocalRoles()
                cleanAdviceInheritanceFor(backPredecessor.getBRefs('ItemPredecessor'))
    cleanAdviceInheritanceFor(item.getBRefs('ItemPredecessor'))


def onItemRemoved(item, event):
    '''When an item is removed, we check that every contained advices were not inherited
       by other items for which removed item is the predecessor.'''
    for adviceId in item.adviceIndex.keys():
        _cleanAdviceInheritance(item, adviceId)


def onMeetingAdded(meeting, event):
    '''This method is called every time a Meeting is created, even in
       portal_factory. Local roles defined on a meeting define who may view
       or edit it. But at the time the meeting is created in portal_factory,
       local roles are not defined yet. This can be a problem when some
       workflow adaptations are enabled. So here
       we grant role 'Owner' to the currently logged user that allows him,
       in every case, to create the meeting.'''
    userId = api.user.get_current().getId()
    meeting.manage_addLocalRoles(userId, ('Owner',))
    # clean cache for "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.meetingdatesvocabulary")


def onMeetingRemoved(meeting, event):
    '''When a meeting is removed, check if we need to remove every linked items,
       this is the case if the current user is a Manager.
       Moreover, check that meeting is no more selected as preferred meeting for existing items.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return
    if 'items_to_remove' in meeting.REQUEST:
        logger.info('Removing %d item(s) linked to meeting at %s...' %
                    (len(meeting.REQUEST.get('items_to_remove')),
                     meeting.absolute_url()))
        # use an intermediate list to avoid changing value in REQUEST
        items_to_remove = [item for item in meeting.REQUEST.get('items_to_remove')]
        for item in items_to_remove:
            unrestrictedRemoveGivenObject(item)
        meeting.REQUEST.set('items_to_remove', ())

    # update items for which current meeting is selected as preferred meeting
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(getPreferredMeeting=meeting.UID())
    for brain in brains:
        item = brain.getObject()
        item.setPreferredMeeting(ITEM_NO_PREFERRED_MEETING_VALUE)
        item.reindexObject('getPreferredMeeting')
    # clean cache for "Products.PloneMeeting.vocabularies.meetingdatesvocabulary"
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.meetingdatesvocabulary")


def onCategoryRemoved(category, event):
    '''Called when a MeetingCategory is removed.'''
    # bypass this if we are actually removing the 'Plone Site'
    if event.object.meta_type == 'Plone Site':
        return

    # clean cache for "Products.PloneMeeting.vocabularies.categoriesvocabulary"
    invalidate_cachekey_volatile_for("Products.PloneMeeting.vocabularies.categoriesvocabulary")


def onDashboardCollectionAdded(collection, event):
    '''Called when a DashboardCollection is created.'''
    # we update customViewFields to fit the MeetingConfig
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(collection)
    if cfg:
        cfg.updateCollectionColumns()
