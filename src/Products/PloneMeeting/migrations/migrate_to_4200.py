# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_organizations
from collective.eeafaceted.batchactions.interfaces import IBatchActionsMarker
from copy import deepcopy
from imio.helpers.content import richtextval
from persistent.mapping import PersistentMapping
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.browser.itemattendee import position_type_default
from Products.PloneMeeting.content.advice import IMeetingAdvice
from Products.PloneMeeting.interfaces import IMeetingDashboardBatchActionsMarker
from Products.PloneMeeting.interfaces import IMeetingItemDashboardBatchActionsMarker
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.ZCatalog.ProgressHandler import ZLogHandler
from zope.interface import alsoProvides
from zope.interface import noLongerProvides


class Migrate_To_4200(Migrator):

    def _configureItemWFValidationLevels(self):
        """Item WF validation levels (states itemcreated, proposed, pre-validated, ...)
           are now defined in MeetingConfig.itemWFValidationLevels."""
        logger.info("Configuring 'itemWFValidationLevels' for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            stored_itemWFValidationLevels = getattr(cfg, 'itemWFValidationLevels', [])
            stored_wfas = cfg.getWorkflowAdaptations()
            # necessary for profile inbetween (4.2beta...)
            if not stored_itemWFValidationLevels:
                itemWFValidationLevels = cfg.getItemWFValidationLevels()
                # a default value exist defining configuration for states
                # itemcreated/proposed/prevalidated/proposedToValidationLevel1/.../proposedToValidationLevel5
                # disable not used states.
                adapted_itemWFValidationLevels = []
                for level in itemWFValidationLevels:
                    adapted_level = deepcopy(level)
                    # proposedToValidationLevel1-5 are new, disable it by default
                    if adapted_level['state'].startswith('proposedToValidationLevel'):
                        adapted_level['enabled'] = '0'
                    # itemcreated, enabled by default
                    if adapted_level['state'] == 'itemcreated' and 'items_come_validated' in stored_wfas:
                        adapted_level['enabled'] = '0'
                    # proposed, enabled by default
                    if adapted_level['state'] == 'proposed':
                        if 'items_come_validated' in stored_wfas or 'no_proposal' in stored_wfas:
                            adapted_level['enabled'] = '0'
                        elif ('pre_validation_keep_reviewer_permissions' in stored_wfas or
                              'pre_validation' in stored_wfas):
                            adapted_level['suffix'] = 'prereviewers'
                            if 'pre_validation_keep_reviewer_permissions' in stored_wfas:
                                adapted_level['extra_suffixes'] = ['reviewers']
                    # prevalidated, disabled by default
                    if adapted_level['state'] == 'prevalidated' and \
                       ('pre_validation' in stored_wfas or
                            'pre_validation_keep_reviewer_permissions' in stored_wfas):
                        adapted_level['enabled'] = '1'
                    adapted_itemWFValidationLevels.append(adapted_level)
                    cfg.setItemWFValidationLevels(adapted_itemWFValidationLevels)

            # clean stored workflowAdaptations
            cleaned_wfas = [wfa for wfa in stored_wfas if wfa in cfg.listWorkflowAdaptations()]
            # make sure new wfAdaptations are enabled (were default, now optional)
            cleaned_wfas += [wfa for wfa in ('pre_accepted', 'delayed', 'accepted_but_modified', )
                             if wfa in cfg.listWorkflowAdaptations()]
            # remove duplicates (in case migration is launched several times)
            cleaned_wfas = tuple(set(cleaned_wfas))
            cfg.setWorkflowAdaptations(cleaned_wfas)
            # clean some parameters that use enabled suffixes and were not validated before
            # for example even when pre_validation was not enabled, it was possible
            # to select a "prereviewers" related value, it is no more the case
            for field_name in ("itemAnnexConfidentialVisibleFor",
                               "adviceAnnexConfidentialVisibleFor",
                               "meetingAnnexConfidentialVisibleFor"):
                field = cfg.getField(field_name)
                old_value = list(field.get(cfg))
                new_value = [v for v in old_value
                             if v in field.Vocabulary(cfg)]
                if old_value != new_value:
                    self.warn(
                        logger, "Value was adapted for field \"{0}\" "
                        "of MeetingConfig \"{1}\", old_value was \"{2}\", "
                        "new_value is \"{3}\".".format(
                            field_name, cfg.getId(), old_value, new_value))
                    field.set(cfg, new_value)
            cfg.at_post_edit_script()
        logger.info('Done.')

    def _configureVotes(self):
        """Some votes attributes on MeetingConfig already exist before changing all
           this, re-apply default values from MeetingConfigDescriptor."""
        logger.info("Configuring 'votes' for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            config_descr = MeetingConfigDescriptor(None, None, None)
            cfg.setUseVotes(config_descr.useVotes)
            cfg.setVotesEncoder(config_descr.votesEncoder)
            cfg.setUsedVoteValues(config_descr.usedVoteValues)
            cfg.setFirstLinkedVoteUsedVoteValues(config_descr.firstLinkedVoteUsedVoteValues)
            cfg.setNextLinkedVotesUsedVoteValues(config_descr.nextLinkedVotesUsedVoteValues)
            cfg.setVoteCondition(config_descr.voteCondition)
        # add itemVotes on every meetings
        brains = self.catalog(meta_type='Meeting')
        logger.info('Adding "itemVotes" to every meetings...')
        for brain in brains:
            meeting = brain.getObject()
            if hasattr(meeting, 'itemVotes'):
                continue
            meeting.itemVotes = PersistentMapping()
            # add the 'voter' key to Meeting.orderedContacts
            for value in meeting.orderedContacts.values():
                value['voter'] = False
            meeting._p_changed = True
        logger.info('Done.')

    def _updateItemSignatories(self):
        """Now that an arbitraty label may be defined when redefining item signatory,
           store it, the default value was the secondary_position_type or the position_type."""
        logger.info("Updating 'itemSignagtories' for every Meetings...")
        brains = self.catalog(meta_type='Meeting')
        for brain in brains:
            meeting = brain.getObject()
            for item_uid, signatories in meeting.itemSignatories.items():
                for signature_number, hp_uid in signatories.items():
                    if isinstance(hp_uid, PersistentMapping):
                        continue
                    self.request.set('person_uid', hp_uid)
                    position_type = position_type_default()
                    # make sure we have a PersistentMapping
                    meeting.itemSignatories[item_uid] = PersistentMapping(
                        meeting.itemSignatories[item_uid])
                    meeting.itemSignatories[item_uid][signature_number] = \
                        PersistentMapping({'hp_uid': hp_uid, 'position_type': position_type})
        logger.info('Done.')

    def _migrateKeepAccessToItemWhenAdviceIsGiven(self):
        """Boolean field MeetingConfig.keepAccessToItemWhenAdviceIsGiven
           is now single select MeetingConfig.keepAccessToItemWhenAdvice."""
        logger.info(
            "Migrationg field 'keepAccessToItemWhenAdviceIsGiven' for "
            "every MeetingConfigs and organizations...")
        # MeetingConfigs
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, 'keepAccessToItemWhenAdviceIsGiven'):
                old_value = cfg.keepAccessToItemWhenAdviceIsGiven
                if old_value is True:
                    cfg.setKeepAccessToItemWhenAdvice('is_given')
                delattr(cfg, 'keepAccessToItemWhenAdviceIsGiven')
        # organizations
        orgs = get_organizations(only_selected=False)
        for org in orgs:
            # org.keep_access_to_item_when_advice_is_given could not exist
            # for imported org never saved
            old_value = getattr(org, 'keep_access_to_item_when_advice_is_given', None)
            if old_value == '':
                org.keep_access_to_item_when_advice = 'use_meetingconfig_value'
            elif old_value == '1':
                org.keep_access_to_item_when_advice = 'is_given'
            elif old_value == '0':
                org.keep_access_to_item_when_advice = 'default'
        logger.info('Done.')

    def _removeMeetingItemsReferenceField(self):
        '''ReferenceField Meeting.items was removed and is now managed manually.'''
        logger.info("Removing Meeting.items reference field...")
        for brain in self.catalog(meta_type='Meeting'):
            meeting = brain.getObject()
            # get references from at_references so order is kept
            reference_uids = [ref.targetUID for ref in meeting.at_references.objectValues()
                              if ref.relationship == 'MeetingItems']
            if reference_uids:
                meeting.deleteReferences('MeetingItems')
                meeting_uid = meeting.UID()
                brains = self.catalog(UID=reference_uids)
                for brain in brains:
                    item = brain.getObject()
                    item._update_meeting_link(meeting_uid=meeting_uid)
        logger.info('Done.')

    def _fixRichTextValueMimeType(self):
        """Make sure RichTextValue stored on DX content (advices) have
           a correct mimeType and outputMimeType."""
        brains = self.catalog(object_provides=IMeetingAdvice.__identifier__)
        logger.info('Fixing mimeType/outputMimeType for every advices...')
        pghandler = ZLogHandler(steps=100)
        pghandler.init('Updating RichText fields for advices...', len(brains))
        i = 0
        for brain in brains:
            i += 1
            pghandler.report(i)
            advice = brain.getObject()
            for field_name in ['advice_comment', 'advice_observations']:
                field_value = getattr(advice, field_name)
                if field_value:
                    setattr(advice, field_name, richtextval(field_value.raw))
        pghandler.finish()
        logger.info('Done.')

    def _updateSearchedFolderBatchActionsMarkerInterface(self):
        """Update every MeetingConfig batch actions marker applied
           to sub folders, now there is a different marker for
           dashboards displaying items or meetings."""
        logger.info("Updating every meeting folders batch actions marker interfaces...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            folders = cfg._get_all_meeting_folders()
            for folder in folders:
                for sub_folder in folder.objectValues('ATFolder'):
                    if not sub_folder.getId().startswith('searches_') or \
                       not IBatchActionsMarker.providedBy(sub_folder):
                        continue
                    noLongerProvides(sub_folder, IBatchActionsMarker)
                    if sub_folder.getId() == "searches_items":
                        # item related searches
                        alsoProvides(sub_folder, IMeetingItemDashboardBatchActionsMarker)
                    else:
                        # meeting related searches
                        alsoProvides(sub_folder, IMeetingDashboardBatchActionsMarker)
                    sub_folder.reindexObject(idxs=['object_provides'])
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4200...')

        # apply correct batch actions marker on searches_* folders
        self._updateSearchedFolderBatchActionsMarkerInterface()
        return

        # remove useless catalog indexes and columns, were renamed to snake case
        self.removeUnusedIndexes(indexes=['getItemIsSigned', 'sendToAuthority', 'toDiscuss'])
        self.removeUnusedColumns(columns=['toDiscuss'])

        # manage link between item and meeting manually
        self._removeMeetingItemsReferenceField()
        self._configureVotes()
        # update stored Meeting.itemSignatories
        self._updateItemSignatories()

        # update RichTextValue stored on DX types (advices)
        self._fixRichTextValueMimeType()

        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')] + extra_omitted)

        # reinstall workflows before updating workflowAdaptations
        self.runProfileSteps('Products.PloneMeeting', steps=['workflow'], profile='default')
        # configure wfAdaptations before reinstall
        self._configureItemWFValidationLevels()
        self._migrateKeepAccessToItemWhenAdviceIsGiven()

        # reinstall so versions are correctly shown in portal_quickinstaller
        self.reinstall(profiles=['profile-Products.PloneMeeting:default', ],
                       ignore_dependencies=False,
                       dependency_strategy=DEPENDENCY_STRATEGY_NEW)
        if self.profile_name != 'profile-Products.PloneMeeting:default':
            self.reinstall(profiles=[self.profile_name, ],
                           ignore_dependencies=False,
                           dependency_strategy=DEPENDENCY_STRATEGY_NEW)

        # configure new WFs
        self.cleanMeetingConfigs(field_names=['itemDecidedStates', 'itemPositiveDecidedStates'])

        # init otherMeetingConfigsClonableToFieldXXX and XXXSuite/XXXEnd new fields
        self.initNewHTMLFields(query={'meta_type': ('Meeting', 'MeetingItem')})

        # update faceted filters
        self.updateFacetedFilters(xml_filename='upgrade_step_4200_add_item_widgets.xml')

        # update holidays
        self.updateHolidays()

        self.tool.updateAllLocalRoles(meta_type=('MeetingItem', ))
        self.refreshDatabase(workflows=True, catalogsToUpdate=[])


def migrate(context):
    '''This migration function will:

       1) Update applied batch actions marker interface on every member folders;
       2) Remove unused indexes and metadata;
       3) Remove Meeting.items reference field;
       4) Configure votes;
       5) Update Meeting.itemSignatories to manage stored position_type;
       6) Fix DX RichText mimetype;
       7) Configure field MeetingConfig.itemWFValidationLevels depending on old wfAdaptations;
       8) Migrate MeetingConfig.keepAccessToItemWhenAdviceIsGiven to
          MeetingConfig.keepAccessToItemWhenAdvice;
       9) Init otherMeetingConfigsClonableToFieldXXX new fields;
       10) Update faceted filters;
       11) Update holidays;
       12) Refresh items local roles and recatalog.
    '''
    migrator = Migrate_To_4200(context)
    migrator.run()
    migrator.finish()
