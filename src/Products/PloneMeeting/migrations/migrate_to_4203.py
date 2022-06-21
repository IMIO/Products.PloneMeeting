# -*- coding: utf-8 -*-

from DateTime import DateTime
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.utils import get_public_url


class Migrate_To_4203(Migrator):

    def _adaptInternalImagesLinkToUseResolveUID(self):
        """We make sure we use resolveuid in src to internal images."""
        logger.info('Adapting link to internal images to use resolveuid...')
        # as bug was introduced in version 4.2, update items that were updated after
        # in portal_setup logs, collective.fontawesome first appearance is when applying
        # upgrade step to 4200, we use it as base modified time query
        ps_logs = sorted([log for log in self.ps.objectValues()
                          if 'fontawesome' in log.__name__])
        install_time = DateTime('1990/01/01')
        if ps_logs:
            install_time = ps_logs[0].bobobase_modification_time()
        # take only items modified since upgrade to 4200
        brains = self.catalog(meta_type='MeetingItem',
                              modified={'range': 'min', 'query': install_time})
        i = 1
        total = len(brains)
        number_of_migrated_links = 0
        for brain in brains:
            logger.info('Migrating links to image {0}/{1} ({2})...'.format(
                i,
                total,
                brain.getPath()))
            i = i + 1
            item = brain.getObject()
            for image in [obj for obj in item.objectValues() if obj.portal_type == 'Image']:
                # get image url taking env var PUBLIC_URL into account
                image_url = get_public_url(image)
                image_UID = image.UID()
                for field in item.Schema().filterFields(default_content_type='text/html'):
                    content = field.getRaw(item)
                    if content.find(image_url) != -1:
                        content = content.replace(image_url, 'resolveuid/{0}'.format(image_UID))
                        logger.info('Replaced image link in field {0}'.format(field.getName()))
                        number_of_migrated_links = number_of_migrated_links + 1
                        field.set(item, content)
        logger.info('Adapted {0} links.'.format(number_of_migrated_links))
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4203...')

        # not necessary if executing the full upgrade to 4200
        # as problem was introduced after 4200...
        if not from_migration_to_4200:
            self._adaptInternalImagesLinkToUseResolveUID()
        logger.info('Done.')


def migrate(context):
    '''This migration function will:

       1) Adapt link to images to ensure it uses resolveuid.
    '''
    migrator = Migrate_To_4203(context)
    migrator.run()
    migrator.finish()
