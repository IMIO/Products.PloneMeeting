# -*- coding: utf-8 -*-

from copy import deepcopy
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


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

    def run(self, extra_omitted=[]):
        logger.info('Migrating to PloneMeeting 4200...')

        self.upgradeAll(omit=['Products.PloneMeeting:default',
                              self.profile_name.replace('profile-', '')] + extra_omitted)

        # reinstall workflows before updating workflowAdaptations
        self.runProfileSteps('Products.PloneMeeting', steps=['workflow'], profile='default')
        # configure wfAdaptations before reinstall
        self._configureItemWFValidationLevels()

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

        self.tool.updateAllLocalRoles(meta_type=('MeetingItem', ))
        self.refreshDatabase(workflows=True, catalogsToUpdate=[])


def migrate(context):
    '''This migration function will:

       1) Configure field MeetingConfig.itemWFValidationLevels depending on old wfAdaptations.

    '''
    migrator = Migrate_To_4200(context)
    migrator.run()
    migrator.finish()
