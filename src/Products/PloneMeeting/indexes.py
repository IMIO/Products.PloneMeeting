# -*- coding: utf-8 -*-
#
# File: indexes.py
#
# Copyright (c) 2017 by Imio.be
#
# GNU General Public License (GPL)
#

from DateTime import DateTime

from OFS.interfaces import IItem

from zope.component import getAdapter
from imio.history.interfaces import IImioHistory
from plone import api
from plone.indexer import indexer
from Products.PluginIndexes.common.UnIndex import _marker
from Products.PloneMeeting.interfaces import IMeeting
from Products.PloneMeeting.interfaces import IMeetingItem
from Products.PloneMeeting.config import HIDDEN_DURING_REDACTION_ADVICE_VALUE
from Products.PloneMeeting.config import ITEM_NO_PREFERRED_MEETING_VALUE
from Products.PloneMeeting.config import NOT_GIVEN_ADVICE_VALUE
from Products.PloneMeeting.utils import get_annexes

REAL_GROUP_ID_PATTERN = 'real_group_id__{0}'
DELAYAWARE_REAL_GROUP_ID_PATTERN = 'delay_real_group_id__{0}'


@indexer(IItem)
def getConfigId(obj):
    """
      Indexes the MeetingConfig id.
    """
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(obj)
    return cfg and cfg.getId() or _marker


@indexer(IMeeting)
def sortable_title(obj):
    """
      Indexes the sortable_title of meeting based on meeting.date
    """
    return obj.getDate().strftime('%Y%m%d%H%M')


@indexer(IMeetingItem)
def title_or_id(obj):
    """
      Indexes the title_or_id, used in the referencebrowser popup
    """
    return obj.title_or_id(withTypeName=False)


@indexer(IMeetingItem)
def previous_review_state(obj):
    """
      Indexes the previous review_state, aka the review_state before current review_state
    """
    try:
        adapter = getAdapter(obj, IImioHistory, 'workflow')
        wf_history = adapter.getHistory()
    except KeyError:
        return _marker

    # check that there is more than one action triggered,
    # or we are in the initial state and previous action is None...
    if not wf_history or len(wf_history) == 1:
        return _marker

    # action [-1] is last triggered action, but we want the previous one...
    previous_action = wf_history[-2]['review_state']
    return previous_action


@indexer(IMeetingItem)
def Description(obj):
    """
      Make sure to use 'text/plain' version of description field as it is normally
      a TextField and that we store HTML data into it for MeetingItem
    """
    return obj.Description(mimetype='text/plain')


@indexer(IItem)
def getRawClassifier(obj):
    """
      Make sure this returns not 'None' because ZCatalog 3
      does not want to index a 'None'...
    """
    classifier = obj.getRawClassifier()
    if classifier is None:
        return _marker
    return classifier


@indexer(IMeetingItem)
def getCopyGroups(obj):
    """
      Compute getCopyGroups to take auto copyGroups into account.
    """
    return obj.getAllCopyGroups(auto_real_group_ids=True)


@indexer(IMeetingItem)
def reviewProcessInfo(obj):
    """
      Compute a reviewProcessInfo, this concatenate the group managing item
      and the item review_state so it can be queryable in the catalog.
    """
    item_state = obj.queryState()
    return '%s__reviewprocess__%s' % (
        obj.adapted()._getGroupManagingItem(item_state).getId(), item_state)


@indexer(IMeetingItem)
def linkedMeetingUID(obj):
    """
      Store the linked meeting UID.
    """
    res = ITEM_NO_PREFERRED_MEETING_VALUE
    meeting = obj.getMeeting()
    if meeting:
        res = meeting.UID()
    # we use same 'None' value as for getPreferredMeeting so we may use the same
    # vocabulary in the meeting date/preferred meeting date faceted filters
    return res


@indexer(IMeetingItem)
def linkedMeetingDate(obj):
    """
      Store the linked meeting date.
    """
    res = []
    meeting = obj.getMeeting()
    if meeting:
        res = meeting.getDate()
    else:
        # for sorting it is necessary to have a date
        res = DateTime('1950/01/01')
    return res


@indexer(IMeetingItem)
def getPreferredMeetingDate(obj):
    """
      Store the preferredMeeting date.
    """
    res = []
    preferredMeetingUID = obj.getPreferredMeeting()
    if preferredMeetingUID != ITEM_NO_PREFERRED_MEETING_VALUE:
        # use uid_catalog because as getPreferredMeetingDate is in the portal_catalog
        # if we clear and rebuild the portal_catalog, preferredMeetingUID will not be found...
        uid_catalog = api.portal.get_tool('uid_catalog')
        res = uid_catalog(UID=preferredMeetingUID)[0].getObject().getDate()
    else:
        res = DateTime('1950/01/01')
    return res or _marker


@indexer(IItem)
def sentToInfos(obj):
    """
      Index other meetingConfigs the item will be/has been cloned to.
      We append :
      - __clonable_to to a meetingConfig id the item is clonable to;
      - __cloned_to to a meetingConfig id the item is cloned to.
      An item that does not have to be send to another meetingConfig
      will receive the 'not_to_be_cloned_to' value so we can filter it out.
    """
    res = []
    clonableTo = obj.getOtherMeetingConfigsClonableTo()
    clonableToEmergency = obj.getOtherMeetingConfigsClonableToEmergency()
    clonedTo = obj._getOtherMeetingConfigsImAmClonedIn()
    for cfgId in clonableTo:
        if cfgId not in clonedTo:
            term_suffix = '__clonable_to'
            if cfgId in clonableToEmergency:
                term_suffix = '__clonable_to_emergency'
            res.append(cfgId + term_suffix)
    for cfgId in clonedTo:
        term_suffix = '__cloned_to'
        if cfgId in clonableToEmergency:
            term_suffix = '__cloned_to_emergency'
        res.append(cfgId + term_suffix)
    if not clonableTo and not clonedTo:
        res.append('not_to_be_cloned_to')
    return res or _marker


@indexer(IMeetingItem)
def SearchableText(obj):
    """
      Contained annex title is indexed in the item's SearchableText.
    """
    res = []
    res.append(obj.SearchableText())
    for annex in get_annexes(obj):
        res.append(annex.SearchableText())
    res = ' '.join(res)
    return res or _marker


@indexer(IMeetingItem)
def sendToAuthority(obj):
    """
      Index the MeetingItem.sendToAuthority to be searchable in a faceted navigation.
    """
    if obj.getSendToAuthority():
        return '1'
    else:
        return '0'


@indexer(IMeetingItem)
def hasAnnexesToPrint(obj):
    """
      Index the fact that an item has annexes to_print.
    """
    # use objectValues because with events order, an annex
    # could be added but still not registered in the categorized_elements dict
    for annex in get_annexes(obj):
        if annex.to_print:
            return '1'
    return '0'


@indexer(IMeetingItem)
def hasAnnexesToSign(obj):
    """
      Index the fact that an item has annexes to_sign/signed.
      - '-1' is not to_sign;
      - '0' is to_sign but not signed;
      - '1' is signed.
    """
    # use objectValues because with events order, an annex
    # could be added but still not registered in the categorized_elements dict
    res = []
    for annex in get_annexes(obj):
        if annex.to_sign:
            if annex.signed:
                res.append('1')
            else:
                res.append('0')
        else:
            res.append('-1')
    return res


@indexer(IItem)
def templateUsingGroups(obj):
    """
      Index used to build the item templates tree.
      If not attribute 'templateUsingGroups' (so not a MeetingItem)
      or a MeetingItem with no selected templateUsingGroups.
      In the query, we will query '__nothing_selected__' + groups the current
      user is creator for.
    """
    if obj.meta_type == 'MeetingItem':
        templateUsingGroups = obj.getTemplateUsingGroups()
        return templateUsingGroups and templateUsingGroups or ('__nothing_selected__', )
    elif obj.portal_type == 'Folder':
        return ('__folder_in_itemtemplates__', )
    return _marker


def _to_coded_adviser_index(obj, groupId, advice):
    """Build an 'index' version of the adviser state so it is searchable and so on."""
    def _computeSuffixFor(groupId, advice, advice_type):
        '''
          Compute the suffix that will be appended depending on advice state.
        '''
        suffixes = []
        # still not given but still giveable?  Not giveable?  Delay exceeded? Asked again?
        if advice_type in (NOT_GIVEN_ADVICE_VALUE,
                           'asked_again',
                           HIDDEN_DURING_REDACTION_ADVICE_VALUE):
            if obj._adviceDelayIsTimedOut(groupId):
                # delay is exceeded, advice was not given
                suffixes.append('_advice_delay_exceeded')
            else:
                # does the relevant group may add the advice in current item state?
                if advice['advice_addable']:
                    suffixes.append('_advice_not_given')
                elif advice['advice_editable']:
                    if advice_type == 'asked_again':
                        suffixes.append('_advice_asked_again')
                    elif advice_type == HIDDEN_DURING_REDACTION_ADVICE_VALUE:
                        suffixes.append('_advice_{0}'.format(HIDDEN_DURING_REDACTION_ADVICE_VALUE))
                else:
                    suffixes.append('_advice_not_giveable')

        if advice['type'] != NOT_GIVEN_ADVICE_VALUE:
            # if advice was given, is it still editable or not?
            # we return the current advice review_state
            # by default, a still editable advice is 'advice_under_edit'
            # and a no more editable advice is 'advice_given'
            advice = getattr(obj, advice['advice_id'])
            suffixes.append('_%s' % advice.queryState())
        return suffixes

    res = []
    isDelayAware = obj.adviceIndex[groupId]['delay'] and True or False
    # compute suffixes
    # we compute the 'advice_type' to take into account 'hidden_during_redaction'
    advice_type = obj._shownAdviceTypeFor(advice)
    suffixes = _computeSuffixFor(groupId, advice, advice_type)
    # we also index the 'real_group_id_' so we can query who we asked
    # advice to, without passing the advice state
    for suffix in suffixes:
        if isDelayAware:
            res.append('delay__' + groupId + suffix)
            # 'real_group_id_'
            real_group_id = DELAYAWARE_REAL_GROUP_ID_PATTERN.format(advice['row_id'])
            res.append(real_group_id)
            # 'real_group_id_' with suffixed advice_type
            res.append(real_group_id + '__' + advice_type)
        else:
            res.append(groupId + suffix)
            # 'real_group_id_'
            real_group_id = REAL_GROUP_ID_PATTERN.format(groupId)
            res.append(real_group_id)
            # 'real_group_id_' with suffixed advice_type
            res.append(real_group_id + '__' + advice_type)
    # advice_type
    if advice_type not in res:
        res.append(advice_type)
    return res


@indexer(IMeetingItem)
def indexAdvisers(obj):
    """
      Build the index specifying advices to give.
      Values are different if it is a delay-aware or not advice :
      Delay-aware advice is like "delay__developers_advice_not_given":
      - delay__ specifies that it is a delay-aware advice;
      - developers is the name of the group the advice is asked to;
      Non delay-aware advice is like "developers_advice_not_given".
      In both cases (delay-aware or not), we have a suffix :
        - '_advice_not_giveable' for advice not given and not giveable;
        - '_advice_not_given' for advice not given/asked again but giveable;
        - '_advice_delay_exceeded' for delay-aware advice not given but
           no more giveable because of delay exceeded;
    """
    if not hasattr(obj, 'adviceIndex'):
        return _marker

    res = []
    for groupId, advice in obj.adviceIndex.iteritems():
        res += _to_coded_adviser_index(obj, groupId, advice)
    # remove double entry, it could be the case for the 'advice_type' alone
    res = list(set(res))
    res.sort()
    return res
