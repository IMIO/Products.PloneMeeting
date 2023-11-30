# -*- coding: utf-8 -*-

from DateTime import DateTime
from imio.history.utils import add_event_to_history
from persistent.list import PersistentList
from plone import api
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.content.advice import IMeetingAdvice
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.setuphandlers import _configurePortalRepository
from Products.PloneMeeting.utils import get_dx_data
from Products.PloneMeeting.utils import getAdvicePortalTypeIds
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.event import notify


class Migrate_To_4205(Migrator):

    def _updateConfigCommitteesAndVotesResult(self):
        """MeetingConfig.committees get a new value "enable_groups" and
           init new field MeetingItem.votesResult."""
        logger.info('Updating datagridfield "committees" for every MeetingConfigs...')
        # reinstall workflows to take new role "MeetingCommitteeEditor" into account
        self.runProfileSteps('Products.PloneMeeting', steps=['rolemap', 'workflow'], profile='default')
        for cfg in self.tool.objectValues('MeetingConfig'):
            committees = cfg.getCommittees()
            for committee in committees:
                if "enable_editors" not in committee or \
                   not committee["enable_editors"]:
                    committee["enable_editors"] = "0"
            cfg.setCommittees(committees)
            notify(ObjectEditedEvent(cfg))
        # update new fields committeeTranscript and votesResult on items
        self.initNewHTMLFields(
            query={'meta_type': ('MeetingItem')},
            field_names=('committeeTranscript', 'votesResult'))
        logger.info('Done.')

    def _updateMeetingCommittees(self):
        """Initialize "committee_observations" column for every meetings..."""
        logger.info('Initializing "committee_observations" for every meetings "committees"...')
        brains = self.catalog(object_provides=IMeeting.__identifier__)
        for brain in brains:
            meeting = brain.getObject()
            committees = meeting.committees
            if not committees or "committee_observations" in committees[0]:
                continue
            for committee in committees:
                committee["committee_observations"] = None
            meeting.committees = committees
            meeting._p_changed = True
        logger.info('Done.')

    def _initAdviceGivenHistory(self):
        """Moving from versioning to imio.history advice_given_history."""
        # if using MeetingConfig.enableAdviceInvalidation, clean potential orphan brains
        # enableAdviceInvalidation is disabled during migrations and stored in cfgsAdvicesInvalidation
        if True in self.cfgsAdvicesInvalidation.values():
            self.clean_orphan_brains(
                query={"object_provides": IMeetingAdvice.__identifier__})

        pr = api.portal.get_tool('portal_repository')
        phs = api.portal.get_tool('portal_historiesstorage')
        h_repo = phs._getZVCRepo()
        logger.info('Moving to "advice_given_history"...')
        brains = self.catalog(object_provides=IMeetingAdvice.__identifier__)
        pghandler = ZLogHandler(steps=1000)
        pghandler.init('Moving to "advice_given_history"...',
                       len(brains))
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            advice = brain.getObject()
            if base_hasattr(advice, "advice_given_history"):
                continue
            advice.advice_given_history = PersistentList()
            h_metadata = pr.getHistoryMetadata(advice)
            if h_metadata:
                for version_info in h_metadata._full.values():
                    vc_info = version_info['vc_info']
                    version_advice = h_repo._histories[vc_info.history_id]._versions[
                        vc_info.version_id]._data._object.object
                    if version_advice:
                        # save info in advice_given_history attribute
                        item_data = list(getattr(version_advice, "historized_item_data", []))
                        # get_dx_data does not work because version_advice
                        # is an Acquisition.ImplicitAcquisitionWrapper without acquisition
                        version_advice.aq_parent = advice.aq_parent
                        version_advice.REQUEST = self.request
                        advice_data = get_dx_data(version_advice)
                        version_advice.aq_parent = None
                        version_advice.REQUEST = None
                        meta = version_info["metadata"]["sys_metadata"]
                        # replace some automatic comments
                        comment = meta["comment"]
                        comment = comment.replace("Versioned", "Historized")
                        add_event_to_history(
                            advice,
                            'advice_given_history',
                            action='advice_given_or_modified',
                            actor=api.user.get(meta["principal"]),
                            time=DateTime(meta["timestamp"]),
                            comments=comment,
                            extra_infos={'item_data': item_data,
                                         'advice_data': advice_data})
                    else:
                        logger.info('Could not find version_id {0} for advice version of {1}!'.format(
                            vc_info.version_id, advice.absolute_url_path()))

        # nothing should be versionned anymore
        if self.portal.portal_historiesstorage._shadowStorage is not None:
            self.portal.portal_historiesstorage._shadowStorage._storage.clear()
        self.portal.portal_historiesstorage.zvc_repo._histories.clear()
        # remove every meetingadvice portal_types from portal_repository
        _configurePortalRepository(removed_types=getAdvicePortalTypeIds())
        # MeetingConfig.versionateAdviceIfGivenAndItemModified was renamed to
        # MeetingConfig.historizeAdviceIfGivenAndItemModified
        self.cleanMeetingConfigs(
            field_names=['versionateAdviceIfGivenAndItemModified'],
            renamed={
                'versionateAdviceIfGivenAndItemModified':
                'historizeAdviceIfGivenAndItemModified'})

    def _updateLocalRolesItemBeforeStateValidated(self):
        """Add permissions were not correctly setup on items in state before "validated"."""
        logger.info('Updating "Add permissions" for every items before "validated"...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            review_states = cfg.getItemWFValidationLevels(data='state', only_enabled=True)
            brains = self.catalog(portal_type=cfg.getItemTypeName(), review_state=review_states)
            if brains:
                self.tool.update_all_local_roles(brains=brains)
        logger.info('Done.')

    def _removeCfgUseGroupsAsCategories(self):
        """Field MeetingConfig.useGroupsAsCategories was removed,
           enable 'category' in MeetingConfig.usedItemAttributes when relevant."""
        logger.info('Removing field "MeetingConfig.useGroupsAsCategories" from every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if not base_hasattr(cfg, 'useGroupsAsCategories'):
                continue
            enable_category = not cfg.useGroupsAsCategories
            if enable_category:
                logger.info("'category' was enabled for MeetingConfig %s" % cfg.getId())
                used_item_attrs = list(cfg.getUsedItemAttributes())
                used_item_attrs.append('category')
                cfg.setUsedItemAttributes(used_item_attrs)
            delattr(cfg, 'useGroupsAsCategories')
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4205...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            # will upgrade collective.documentgenerator and collective.messagesviewlet
            self.upgradeAll(omit=['Products.PloneMeeting:default'])
            self._updateConfigCommitteesAndVotesResult()
            self._updateMeetingCommittees()
            self._updateLocalRolesItemBeforeStateValidated()
            self.addNewSearches()

        self._initAdviceGivenHistory()
        self._removeCfgUseGroupsAsCategories()
        logger.info('Migrating to PloneMeeting 4205... Done.')


def migrate(context):
    '''This migration function will:

       1) Update MeetingConfig.committees to add "enable_groups",
          init new MeetingItem fields 'committeeTranscript' and 'votesResult';
       2) Update meetig.committees to add "committee_observations";
       3) Update local roles of items in before review_state "validated";
       4) Move from advice versioning to "advice_given_history";
       5) Remove field "MeetingConfig.useGroupsAsCategories".
    '''
    migrator = Migrate_To_4205(context)
    migrator.run()
    migrator.finish()
