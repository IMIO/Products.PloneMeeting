# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_organizations
from copy import deepcopy
from persistent.mapping import PersistentMapping
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.profiles import MeetingConfigDescriptor


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
                            adapted_level['suffix'] = ['prereviewers']
                            if 'pre_validation_keep_reviewer_permissions' in stored_wfas:
                                adapted_level['extra_suffixes'] = ['reviewers']
                    # prevalidated, disabled by default
                    if adapted_level['state'] == 'prevalidated' and \
                       ('pre_validation' in stored_wfas or
                            'pre_validation_keep_reviewer_permissions' in stored_wfas):
                        adapted_level['enabled'] = '1'
                        if 'pre_validation_keep_reviewer_permissions' in stored_wfas:
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
            old_value = org.keep_access_to_item_when_advice_is_given
            if old_value == '':
                org.keep_access_to_item_when_advice = 'use_meetingconfig_value'
            elif old_value == '1':
                org.keep_access_to_item_when_advice = 'is_given'
            elif old_value == '0':
                org.keep_access_to_item_when_advice = 'default'
        logger.info('Done.')

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4200...')

        # remove useless catalog indexes and columns, were renamed to snake case
        self.removeUnusedIndexes(indexes=['getItemIsSigned', 'sendToAuthority', 'toDiscuss'])
        self.removeUnusedColumns(columns=['toDiscuss'])

        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')] + extra_omitted)

        # reinstall workflows before updating workflowAdaptations
        self.runProfileSteps('Products.PloneMeeting', steps=['workflow'], profile='default')
        # configure wfAdaptations before reinstall
        self._configureItemWFValidationLevels()
        self._configureVotes()
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
        self.initNewHTMLFields()

        # update faceted filters
        self.updateFacetedFilters(xml_filename='upgrade_step_4200_add_item_widgets.xml')

        # update holidays
        self.updateHolidays()

        self.tool.updateAllLocalRoles(meta_type=('MeetingItem', ))
        self.refreshDatabase(workflows=True, catalogsToUpdate=[])


def migrate(context):
    '''This migration function will:

       1) Configure field MeetingConfig.itemWFValidationLevels depending on old wfAdaptations;
       2) Migrate MeetingConfig.keepAccessToItemWhenAdviceIsGiven to
          MeetingConfig.keepAccessToItemWhenAdvice;
       3) Init otherMeetingConfigsClonableToFieldXXX new fields.
    '''
    migrator = Migrate_To_4200(context)
    migrator.run()
    migrator.finish()
