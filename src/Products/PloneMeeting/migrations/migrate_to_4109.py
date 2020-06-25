# -*- coding: utf-8 -*-

from plone.app.controlpanel.mail import MailControlPanelAdapter
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import get_public_url
from copy import deepcopy


class Migrate_To_4109(Migrator):

    def force_email_from_address(self):
        mail_panel_adapter = MailControlPanelAdapter(self.portal)
        public_url = get_public_url(self.portal)
        mail_address = public_url.replace("https://", "")
        index = mail_address.index("-pm")
        mail_address = "%s-delib@imio.be" % mail_address[:index]
        mail_panel_adapter.set_email_from_address(mail_address)

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
