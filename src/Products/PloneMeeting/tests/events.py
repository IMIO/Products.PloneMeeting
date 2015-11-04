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


def onItemListTypeChanged(item, event):
    '''Called when a MeetingItem.listType is changed.'''
    # in this test, we just change item title and we
    # set old_listType and new listType
    item.setTitle("{0} - {1}".format(event.old_listType, item.getListType()))
    item.reindexObject()
