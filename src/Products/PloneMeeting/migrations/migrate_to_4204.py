# -*- coding: utf-8 -*-

from imio.helpers.setup import load_type_from_package
from persistent.mapping import PersistentMapping
from Products.Archetypes.event import ObjectEditedEvent
from Products.CMFPlone.utils import base_hasattr
from Products.PloneMeeting.content.meeting import IMeeting
from Products.PloneMeeting.migrations import logger
from Products.PloneMeeting.migrations import Migrator
from Products.PloneMeeting.setuphandlers import _configurePortalRepository
from zope.event import notify


class Migrate_To_4204(Migrator):

    def _reloadItemTemplateAndRecurringTypes(self):
        """Reload MeetingItemTemplate/MeetingItemRecurring portal_types to fix
           the allowed_content_types to only accept "Image"."""
        logger.info('Reloading MeetingItemTemplate/MeetingItemRecurring portal_types...')
        # first update MeetingItemTemplate/MeetingItemRecurring base portal_types
        load_type_from_package('MeetingItemTemplate', 'Products.PloneMeeting:default')
        load_type_from_package('MeetingItemRecurring', 'Products.PloneMeeting:default')
        for cfg in self.tool.objectValues('MeetingConfig'):
            notify(ObjectEditedEvent(cfg))
        logger.info('Done.')

    def _initMeetingsItemAttendeesOrder(self):
        """Initialize the item_attendees_order attribute for existing meetings."""
        logger.info('Initializing "item_attendees_order" for every meetings...')
        brains = self.catalog(object_provides=IMeeting.__identifier__)
        for brain in brains:
            meeting = brain.getObject()
            if base_hasattr(meeting, "item_attendees_order"):
                continue
            meeting.item_attendees_order = PersistentMapping()
            meeting._p_changed = True
        logger.info('Done.')

    def _migrateMCYearlyInitMeetingNumber(self):
        """Boolean field yearlyInitMeetingNumber is not a list of choices called
           yearlyInitMeetingNumbers."""
        logger.info('Migrating field "yearlyInitMeetingNumber" to '
                    '"yearlyInitMeetingNumbers" for every MeetingConfigs...')
        for cfg in self.tool.objectValues('MeetingConfig'):
            if hasattr(cfg, "yearlyInitMeetingNumber"):
                if cfg.yearlyInitMeetingNumber is True:
                    cfg.setYearlyInitMeetingNumbers(("meeting_number", ))
                delattr(cfg, "yearlyInitMeetingNumber")
                # fields Meeting.meeting_number and Meeting.first_item_number
                # are now optionnal so select it by default
                used_attrs = list(cfg.getUsedMeetingAttributes())
                used_attrs.append("meeting_number")
                used_attrs.append("first_item_number")
                cfg.setUsedMeetingAttributes(used_attrs)
        logger.info('Done.')

    def run(self, extra_omitted=[], from_migration_to_4200=False):

        logger.info('Migrating to PloneMeeting 4204...')

        # not necessary if executing the full upgrade to 4200
        if not from_migration_to_4200:
            _configurePortalRepository()
            self._reloadItemTemplateAndRecurringTypes()
            self._initMeetingsItemAttendeesOrder()
            self.updateHolidays()
        self._migrateMCYearlyInitMeetingNumber()

        # ToolPloneMeeting.get_plone_groups_for_user parameter userId is now user_id
        self.updateTALConditions("get_plone_groups_for_user(userId",
                                 "get_plone_groups_for_user(user_id")
        # ToolPloneMeeting.get_plone_groups_for_user is deprecated
        # use imio.helpers.cache.get_plone_groups_for_user that is available in pm_utils
        self.updateTALConditions("tool.get_plone_groups_for_user(",
                                 "pm_utils.get_plone_groups_for_user(")
        self.updateTALConditions("portal_plonemeeting.get_plone_groups_for_user(",
                                 "pm_utils.get_plone_groups_for_user(")

        # remove field MeetingConfig.transitionsForPresentingAnItem
        self.cleanMeetingConfigs(field_names=['transitionsForPresentingAnItem'])
        logger.info('Done.')


def migrate(context):
    '''This migration function will:

       1) Configure portal_repository;
       2) Reload MeetingItemTemplate/Recurring portal_types;
       3) Init attribute item_attendees_order for every meetings.
    '''
    migrator = Migrate_To_4204(context)
    migrator.run()
    migrator.finish()
