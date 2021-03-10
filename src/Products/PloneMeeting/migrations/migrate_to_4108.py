# -*- coding: utf-8 -*-

from copy import deepcopy
from plone.app.controlpanel.mail import MailControlPanelAdapter
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import get_public_url


class Migrate_To_4108(Migrator):

    def _correctDashboardCollectionsQuery(self):
        """Format of DashboardCollection query is sometimes broken, instead containing
           list of <dict>, it contains list of <instance> ???."""
        logger.info("Correcting query for DashboardCollections...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            for subfolder in cfg.searches.objectValues():
                for search in subfolder.objectValues():
                    query = deepcopy(search.query)
                    query = [dict(crit) for crit in query]
                    search.setQuery(query)
        logger.info('Done.')

    def fix_email_from_address(self):
        logger.info("Fixing email from address...")
        mail_panel_adapter = MailControlPanelAdapter(self.portal)
        mail_address = mail_panel_adapter.get_email_from_address().strip()
        if "imio.be" in mail_address:
            public_url = get_public_url(self.portal)
            mail_address = public_url.replace("https://", "")\
                .replace("-pm.imio-app", "-delib@imio")
        mail_panel_adapter.set_email_from_address(mail_address.strip(" /."))
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4108...')
        self._correctDashboardCollectionsQuery()
        # fix wrong condition for 'searchmyitemstakenover'
        # that used omittedSuffixes instead omitted_suffixes
        self.updateTALConditions(old_word='omittedSuffixes', new_word='omitted_suffixes')
        self.fix_email_from_address()


def migrate(context):
    '''This migration function will:

       1) Make sure format of DashboardCollection.query is correct;
       2) Fix condition for 'searchmyitemstakenover'.
       3) Fix mail sender address;
       4) Re-apply typeinfo step to update directory schema policy.
    '''
    migrator = Migrate_To_4108(context)
    migrator.run()
    migrator.finish()
