# -*- coding: utf-8 -*-

from imio.esign.config import set_esign_registry_enabled
from imio.helpers.setup import load_type_from_package
from Products.GenericSetup.tool import DEPENDENCY_STRATEGY_NEW
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator


class Migrate_To_4218(Migrator):

    def _configureEsign(self):
        """Configure imio.esign."""
        logger.info('Configuring imio.esign...')
        # install imio.esign, but do not reinstall imio.fpaudit
        # because of difference between installed profile and profile name (install-base)
        # collective.documentgenerator is reinstalled, so re-configure it
        self.reinstall(['profile-imio.esign:default'], dependency_strategy=DEPENDENCY_STRATEGY_NEW)
        # re-apply ConfigurablePODTemplate to add esign_signers_expr field
        load_type_from_package('ConfigurablePODTemplate', 'Products.PloneMeeting:default')
        load_type_from_package('StyleTemplate', 'Products.PloneMeeting:default')
        # hide document-generation-link default viewlet
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'viewlets')
        # add searchitemsinesignsessions/searchmeetingsinesignsessions, first remove it as it evolved
        for cfg in self.tool.objectValues('MeetingConfig'):
            searches_items = cfg.searches.searches_items
            if "searchitemsinesignsessions" in searches_items.objectIds():
                searches_items.manage_delObjects(ids=['searchitemsinesignsessions'])
            searches_decisions = cfg.searches.searches_decisions
            if "searchmeetingsinesignsessions" in searches_decisions.objectIds():
                searches_decisions.manage_delObjects(ids=['searchmeetingsinesignsessions'])
        self.addNewSearches()
        # re-apply actions.xml to manage add_to_session/remove_from_session actions
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'actions')
        # re-apply rolemap to give "imio.esign: Manage Sessions" to MeetingManager
        self.ps.runImportStepFromProfile('profile-Products.PloneMeeting:default', 'rolemap')
        # create esignwatchers group per MeetingConfig
        for cfg in self.tool.objectValues('MeetingConfig'):
            cfg._createOrUpdateAllPloneGroups()
        # disable it by default
        set_esign_registry_enabled(False)
        # update held_positions that should be "signer":
        # if having a signture_number
        # if used in MeetingConfig.certifiedSignatures
        hp_in_all_cfg_certified_signatures = []
        for cfg in self.tool.objectValues('MeetingConfig'):
            hp_in_cfg_certified_signatures = [
                row['held_position'] for row in cfg.getCertifiedSignatures()
                if row['held_position'] not in ('_none_', '')]
            hp_in_all_cfg_certified_signatures += hp_in_cfg_certified_signatures
        for brain in self.catalog(portal_type='held_position'):
            hp = brain.getObject()
            if 'signer' in hp.usages:
                continue
            if hp.signature_number is not None or \
               hp.UID() in hp_in_all_cfg_certified_signatures:
                hp.usages = hp.usages + ['signer']
                logger.info("Usage \"signer\" was added to held position at %s" % hp.absolute_url())
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4218...')
        if not from_migration_to_4200:
            # this will upgrade collective.contact.plonegroup especially
            self.upgradeAll(omit=['Products.PloneMeeting:default',
                                  self.profile_name.replace('profile-', '')])
        self._configureEsign()
        logger.info('Migrating to PloneMeeting 4218... Done.')


def migrate(context):
    '''This migration function will:

        1) Configure imio.esign.
    '''
    migrator = Migrate_To_4218(context)
    migrator.run()
    migrator.finish()
