# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#

from AccessControl import Unauthorized
from plone import api
from Products.PloneMeeting.indexes import DELAYAWARE_ROW_ID_PATTERN
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN

import logging


logger = logging.getLogger('PloneMeeting')


def commonChecks(group_id):
    """ """
    portal = api.portal.get()
    tool = api.portal.get_tool('portal_plonemeeting')
    # some verifications, must be Manager and new_proposing_group_id must be valid
    if not tool.isManager(portal, realManagers=True):
        raise Unauthorized
    if group_id not in tool.objectIds('MeetingGroup'):
        raise KeyError('{0} is not a valid proposingGroup id!'.format(group_id))


def changeProposingGroupFor(old_proposing_group_id, new_proposing_group_id, ):
    '''Change items having p_old_proposing_group_id by p_new_proposing_group_id.'''
    commonChecks(new_proposing_group_id)
    catalog = api.portal.get_tool('portal_catalog')
    brains = catalog(meta_type='MeetingItem',
                     getProposingGroup=old_proposing_group_id)
    # if reindexObject is called without idxs, it is notifyModified...
    catalog_indexes = catalog.Indexes.keys()
    for brain in brains:
        obj = brain.getObject()
        obj.setProposingGroup(new_proposing_group_id)
        obj.update_local_roles()
        obj.reindexObject(idxs=catalog_indexes)
        logger.info('Obj at {0} proposingGroup is now {1}'.format('/'.join(obj.getPhysicalPath()),
                                                                  new_proposing_group_id))


def lookForCopyGroups(group_id):
    """Check if some copy groups of a given p_group_id is used by any items in the application."""
    commonChecks(group_id)
    tool = api.portal.get_tool('portal_plonemeeting')
    catalog = api.portal.get_tool('portal_catalog')
    group = getattr(tool, group_id)
    suffixes = group.get_all_suffixes(group_id)
    res = {}
    for suffix in suffixes:
        ploneGroupId = group.getPloneGroupId(suffix)
        brains = catalog(getCopyGroups=ploneGroupId)
        if brains:
            res[suffix] = [brain.getURL() for brain in brains]

    output = []
    for k, v in res.items():
        output.append(k)
        for value in v:
            output.append(value)
    return '\n'.join(output)


def lookForAdvisers(group_id):
    """Check if given p_group_id is used as adviser."""
    commonChecks(group_id)
    tool = api.portal.get_tool('portal_plonemeeting')
    catalog = api.portal.get_tool('portal_catalog')
    # get row_ids of customAdvisers the group_id is used with
    delayAwareCustomAdvisersRowIds = []
    for mc in tool.objectValues('MeetingConfig'):
        delayAwareCustomAdvisersRowIds += [customAdviser['row_id'] for customAdviser in mc.getCustomAdvisers()
                                           if (customAdviser['group'] == group_id and customAdviser['delay'])]
    delay_aware_values = [DELAYAWARE_ROW_ID_PATTERN.format(delay_aware_group_id)
                          for delay_aware_group_id in delayAwareCustomAdvisersRowIds]
    real_group_id_value = REAL_ORG_UID_PATTERN.format(group_id)

    res = []
    brains = catalog(indexAdvisers=delay_aware_values + [real_group_id_value])
    if brains:
        res = [brain.getURL() for brain in brains]

    return '\n'.join(res)
