# -*- coding: utf-8 -*-
#
# File: events.py
#
# Copyright (c) 2015 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

from Products.PloneMeeting import PloneMeetingError
from Products.PloneMeeting.tests.testViews import SAMPLE_ERROR_MESSAGE


def onItemListTypeChanged(item, event):
    '''Called when a MeetingItem.listType is changed.'''
    # raise a PloneMeetingError if title is already 'late - normal'
    if item.Title() == 'late - normal':
        raise PloneMeetingError(SAMPLE_ERROR_MESSAGE)
    # in this test, we just change item title and we
    # set old_listType and new listType
    item.setTitle("{0} - {1}".format(event.old_listType, item.getListType()))
    item.reindexObject()
