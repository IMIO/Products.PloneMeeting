# -*- coding: utf-8 -*-

from plone.app.controlpanel.mail import MailControlPanelAdapter
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import get_public_url


class Migrate_To_4109(Migrator):

    def force_email_from_address(self):
        logger.info("Fixing email from address...")
        mail_panel_adapter = MailControlPanelAdapter(self.portal)
        smtp_host = mail_panel_adapter.smtp_host or u''
        if smtp_host.strip() != u'localhost':
            logger.info("Bypassing, smtp_host is not localhost...")
        else:
            public_url = get_public_url(self.portal)
            mail_address = public_url.replace("https://", "")
            if "-pm" not in mail_address:
                logger.info("Bypassing, \"-pm\" not found in public_url...")
            else:
                index = mail_address.index("-pm")
                mail_address = "%s-delib@imio.be" % mail_address[:index]
                logger.info("Setting \"{0}\" as email_from_address.".format(mail_address))
                mail_panel_adapter.set_email_from_address(mail_address)
        logger.info('Done.')

    def run(self, from_migration_to_41=False):
        logger.info('Migrating to PloneMeeting 4109...')
        self.force_email_from_address()


def migrate(context):
    '''This migration function will:

       1) Force mail sender address.
    '''
    migrator = Migrate_To_4109(context)
    migrator.run()
    migrator.finish()
