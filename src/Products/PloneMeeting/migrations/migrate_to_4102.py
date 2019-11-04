# -*- coding: utf-8 -*-

from ftw.labels.interfaces import ILabelJar
from persistent.mapping import PersistentMapping
from plone.app.textfield.value import RichTextValue
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from zope.i18n import translate


class Migrate_To_4102(Migrator):

    def _updateFTWLabelsStorage(self):
        """ftw.labels jar was created using dict we need PersistentMappings..."""
        logger.info("Updating ftw.labels jar for every MeetingConfigs...")
        for cfg in self.tool.objectValues('MeetingConfig'):
            jar_storage = ILabelJar(cfg).storage
            for k, v in jar_storage.items():
                jar_storage[k] = PersistentMapping(v)
        logger.info('Done.')

    def _adaptHolidaysWarningMessage(self):
        '''Adapt holidays warning message to be less panicking...'''
        logger.info("Adapting content for message 'Holidays warning'...")
        message = self.portal.get('messages-config').get('holidays_warning')
        text = translate('holidays_warning_message',
                         domain='PloneMeeting',
                         context=self.request)
        message.text = RichTextValue(
            raw=text,
            mimeType='text/html',
            outputMimeType='text/html',
            encoding='utf-8')
        logger.info('Done.')

    def _fixBadHolidayValue(self):
        """A bad value was historically added '2017/2/25', turn it to '2017/12/25'."""
        logger.info("Fix wrong value in ToolPloneMeeting.holidays...")
        storedHolidays = self.tool.getHolidays()
        holidays = []
        for holiday in storedHolidays:
            if holiday['date'] == '2017/2/25':
                holidays.append({'date': '2017/12/25'})
                logger.info('Wrong value "2017/2/25" was fixed!')
            else:
                holidays.append(holiday)
        self.tool.setHolidays(holidays)
        logger.info('Done.')

    def run(self):
        logger.info('Migrating to PloneMeeting 4102...')
        self._updateFTWLabelsStorage()
        self._adaptHolidaysWarningMessage()
        self._fixBadHolidayValue()


def migrate(context):
    '''This migration function will:

       1) Update ftw.labels jar storage to use PersistentMappings;
       2) Update collective.messagesviewlet 'holidays warning' text;
       3) Fix bad value '2017/2/25' in ToolPloneMeeting.holidays.
    '''
    migrator = Migrate_To_4102(context)
    migrator.run()
    migrator.finish()
