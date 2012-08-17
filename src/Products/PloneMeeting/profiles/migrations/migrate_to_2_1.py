# ------------------------------------------------------------------------------
from Acquisition import aq_base
from Products.PloneMeeting.profiles.migrations import Migrator
from Products.PloneMeeting.config import *
from Products.PloneMeeting.profiles.migrations.migrate_to_2_0 import migrateExistingPloneGroupsTitle
import logging
logger = logging.getLogger('PloneMeeting')

# The migration class ----------------------------------------------------------
class Migrate_To_2_1(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def _addPrereviewerGroups(self):
        '''Adds, for every existing MeetingGroup, the new Plone group for
           pre-reviewers.'''
        logger.info('Adding new Plone groups for pre-reviewers...')
        groups = self.portal.acl_users.source_groups
        for meetingGroup in self.tool.objectValues('MeetingGroup'):
            ploneGroupId = meetingGroup.getPloneGroupId('prereviewers')
            if ploneGroupId not in groups.listGroupIds():
                meetingGroup._createPloneGroup('prereviewers')
        logger.info('Done.')

    def _addPloneMeetingTabs(self):
        '''Make sure that every meetingConfigs has his portal_tab as this
           functionnality was deactivated for the 2.1.0 tag'''
        logger.info('Adding necessary tabs...')
        meetingConfigs = self.portal.portal_plonemeeting.objectValues('MeetingConfig')
        for meetingConfig in meetingConfigs:
            meetingConfig.createTab()
        logger.info('Done.')

    def _reindexAnnexes(self):
        '''Reindex annexes as the stored url has changed'''
        logger.info('Reindexing annexes for every item...')
        for brain in self.portal.portal_catalog(meta_type='MeetingItem'):
            brain.getObject().updateAnnexIndex()

    def _updateAdvicesFormat(self):
        '''Update every given advices because the format of 'comment' and
           'name' has changed'''
        logger.info('Updating advices format for every items...')
        for brain in self.portal.portal_catalog(meta_type='MeetingItem'):
            obj = brain.getObject()
            # In some case, for example a recurring item has been catalogued
            # the advices dict is not available...
            if not hasattr(obj.aq_base, 'advices'):
                continue
            for advice in obj.advices:
                if obj.advices[advice].has_key('comment'):
                    obj.advices[advice]['comment'] = \
                        obj.advices[advice]['comment'].replace('&nbsp;', ' ')
                if obj.advices[advice].has_key('name'):
                    obj.advices[advice]['name'] = \
                        obj.advices[advice]['name'].replace('&nbsp;', ' ')

    def _patchFileSecurity(self):
        '''Plone 4 migration requires every ATFile object to be deletable by
           admin, because it converts it to a blob. From a HS/PM point of view,
           it only concerns frozen documents.'''
        brains = self.portal.portal_catalog(meta_type='ATFile')
        if not brains: return
        logger.info('Security fix: scanning %s ATFile objects...' % len(brains))
        user = self.portal.portal_membership.getAuthenticatedMember()
        patched = 0
        for brain in brains:
            fileObject = brain.getObject()
            if user.has_permission('Delete objects', fileObject): continue
            fileObject._Delete_objects_Permission = \
                fileObject._Delete_objects_Permission + ('Manager',)
            patched += 1
        logger.info('Done (%d file(s) patched).' % patched)

    def _finalizeClosedSessionRemoval(self):
        '''The MeetingItem.closedSession field has been removed.  We use the
           field 'privacy' now.  Update existing meetingItems and also update
           meetingConfigs as closedSession was an optional field.'''
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        if not brains: return
        logger.info('Finalizing "closedSession" removal: scanning %s MeetingItem objects...' % len(brains))
        for brain in brains:
            item = aq_base(brain.getObject())
            if not hasattr(item, 'closedSession'):
                #item already migrated, continue (even if every items should alraedy have be migrated...)
                continue
            closedSession = getattr(item, 'closedSession')
            if closedSession:
                item.setPrivacy('secret')
            else:
                item.setPrivacy('public')
            delattr(item, 'closedSession')
        # Update meetingConfigs
        mcs = self.portal.portal_plonemeeting.objectValues('MeetingConfig')
        logger.info('Finalizing "closedSession" removal: updating %d meetingConfigs...' % len(mcs))
        for mc in mcs:
            usedItemAttributes = list(mc.getUsedItemAttributes())
            if 'closedSession' in usedItemAttributes:
                usedItemAttributes.remove('closedSession')
                if not 'privacy' in usedItemAttributes:
                    usedItemAttributes.append('privacy')
                mc.setUsedItemAttributes(usedItemAttributes)
        logger.info('Finalizing "closedSession" removal: Done!')

    def _updateMailingListConditionFormat(self):
        '''Add a 'python:' suffix to every old mailinglist conditions'''
        logger.info('Update mailinglists conditions...')
        cfgs = self.portal.portal_plonemeeting.objectValues('MeetingConfig')
        for cfg in cfgs:
            for template in cfg.podtemplates.objectValues('PodTemplate'):
                mailingInfo = template.getMailingLists().strip()
                if not mailingInfo: continue
                res = []
                for line in mailingInfo.split('\n'):
                    name, condition, userIds = line.split(';')
                    condition = condition.strip()
                    # check if the condition do not already starts with 'python:'
                    # or if the format is a 'TAL-like' format
                    if condition.startswith('python:') or \
                       ('/' in condition and not ' ' in condition.strip()):
                        # we found an already right formatted condition
                        res = []
                        break
                    else:
                        res.append(('%s;python:%s;%s'%(name,condition,userIds)))
                if res:
                    template.setMailingLists('\n'.join(res))
        logger.info('Done.')

    def _updateMeetingsTitle(self):
        '''The title format of meetings has changed, so update every title'''
        brains = self.portal.portal_catalog(meta_type='Meeting')
        if not brains: return
        logger.info('Updating every meetings title: scanning %s ' \
                    'Meeting objects...' % len(brains))
        for brain in brains:
            meeting = brain.getObject()
            meeting.updateTitle()
            meeting.reindexObject(idxs=['Title', 'SearchableText'])
        logger.info('Done.')

    def _updateItemInitiatorField(self):
        '''The field MeetingItem.ItemInitiator is now multivalued'''
        logger.info('Updating every items ItemInitiator...')
        cfgs = self.portal.portal_plonemeeting.objectValues('MeetingConfig')
        for cfg in cfgs:
            brains = self.portal.portal_catalog(portal_type=cfg.getItemTypeName())
            logger.info("Updating '%d' items in MeetingConfig '%s'" % (len(brains), cfg.getId()))
            defineAvailableInitiators = True
            for brain in brains:
                item = brain.getObject()
                #first item of this meetingConfig, define available item intiators
                if defineAvailableInitiators:
                    availableInitiators = item.listItemInitiators().keys()
                    defineAvailableInitiators = False
                itemInitiators = item.getItemInitiator()
                #check if we need to migrate the initiator
                for itemInitiator in itemInitiators:
                    if not itemInitiator in availableInitiators:
                        #we need to migrate this item
                        newValue = [''.join(itemInitiators),]
                        if not newValue[0] in availableInitiators:
                            raise ValueError, "Unable to migrate ItemInitiator field for item at %s" % item.absolute_url()
                        item.setItemInitiator(newValue)
                        break

    def _updateTopicsWithSearchScripts(self):
        '''Topics criteria are now taken into account so remove wrongly added criteria
           on topics having a searchScript.'''
        logger.info('Updating every topics having a searchScript...')
        cfgs = self.portal.portal_plonemeeting.objectValues('MeetingConfig')
        for cfg in cfgs:
            for topic in cfg.topics.objectValues('ATTopic'):
                #only update topics having a searchScript
                if not topic.getProperty(TOPIC_SEARCH_SCRIPT, None):
                    continue
                for criterion in topic.listCriteria():
                    # we just keep the 'Type' criterion, every other criteria are removed
                    if not criterion.field == 'Type':
                        topic.manage_delObjects([criterion.getId(),])
                        #manage several state criterion?  continue...


    def run(self, refreshCatalogs=True, refreshWorkflows=True):
        logger.info('Migrating to HubSessions 2.1...')
        self._addPrereviewerGroups()
        self._addPloneMeetingTabs()
        self._reindexAnnexes()
        self._updateAdvicesFormat()
        self._patchFileSecurity()
        self._finalizeClosedSessionRemoval()
        self._updateMailingListConditionFormat()
        self._updateMeetingsTitle()
        migrateExistingPloneGroupsTitle(self.context)
        self._updateItemInitiatorField()
        self._updateTopicsWithSearchScripts()
        self.finish()

# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) adds, for every existing MeetingGroup, the new Plone group for
          pre-reviewers;
       2) Add portal_tabs for every meetingConfigs;
       3) Reindexes all annexes for items;
       4) Update advices format for items;
       5) Patches security of File objects;
       6) Remove attribute 'closedSession' on items;
       7) Update mailinglists conditions format to use TAL expressions and not Python expressions;
       8) Update every meetings title;
       9) Adapt existing Plone groups title to ensure it is NOT unicode;
       10) Update field MeetingItem.ItemInitiator to multivalued;
       11) Update topics having a searchScript as now defined criteria are taken into account.
    '''
    if context.readDataFile("PloneMeeting_migrations_marker.txt") is None:return
    Migrate_To_2_1(context).run()
# ------------------------------------------------------------------------------
