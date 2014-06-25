# -*- coding: utf-8 -*-
#
# File: Searcher.py
#
# Copyright (c) 2013 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


from Products.CMFPlone.PloneBatch import Batch
from Products.PloneMeeting.utils import getDateFromRequest, prepareSearchValue


class Searcher:
    '''The searcher creates and executes queries in the portal_catalog
       which are triggered by the user from the "advanced search" screen in
       PloneMeeting.'''
    def __init__(self, meetingConfig, searchedType, sortKey, sortOrder,
                 filterKey, filterValue):
        self.meetingConfig = meetingConfig
        self.portalCatalog = meetingConfig.portal_catalog
        self.tool = meetingConfig.getParentNode()
        self.rq = meetingConfig.REQUEST  # The Zope REQUEST object.
        self.searchedType = searchedType
        self.sortKey = sortKey
        self.sortOrder = sortOrder
        self.filterKey = filterKey
        self.filterValue = filterValue
        self.searchParams = eval(self.rq.form['searchParams'])
        self.keywords = None

    def getMultiValue(self, paramName):
        '''Gets a multi-valued element.'''
        res = self.searchParams.get(paramName, [])
        if isinstance(res, basestring):
            res = [res]
        # For every string value, there may be several values within one value,
        # separated with char "*".
        valuesToAdd = None
        valuesToRemove = None
        for v in res:
            if '*' in v:
                values = v.split('*')
                if not valuesToAdd:
                    valuesToAdd = []
                if not valuesToRemove:
                    valuesToRemove = []
                valuesToAdd += values
                valuesToRemove.append(v)
        if valuesToAdd:
            res += valuesToAdd
            for v in valuesToRemove:
                res.remove(v)
        return res

    def addKeywords(self, res, fieldName):
        '''Adds self.keywords to the search parameters p_res for the field
           named p_fieldName.'''
        res[fieldName] = self.keywords

    def getItemSearchParams(self, mainParams, dateInterval):
        '''Adds to dict p_mainParams the parameters which are specific for
           performing (an) item-specific query(ies) in the portal_catalog.'''
        res = mainParams.copy()
        res['portal_type'] = self.meetingConfig.getItemTypeName()
        res['created'] = {'query': dateInterval, 'range': 'minmax'}
        res['sort_on'] = self.sortKey or 'created'
        res['isDefinedInTool'] = False
        if self.keywords:
            # What fields need to be queried?
            kTarget = self.searchParams.get('item_keywords_target', 'all')
            if kTarget == 'all':
                # In this case we search within the combined search index
                # SearchableText.
                self.addKeywords(res, 'SearchableText')
            else:
                self.addKeywords(res, kTarget)
        proposingGroups = self.getMultiValue('proposingGroups')
        if proposingGroups:
            res['getProposingGroup'] = proposingGroups
        associatedGroups = tuple(self.getMultiValue('associatedGroups'))
        if associatedGroups:
            operator = self.searchParams.get('ag_operator', 'or')
            if (operator == 'and') and (len(associatedGroups) > 1):
                associatedGroups = {'operator': 'and', 'query': associatedGroups, }
            res['getAssociatedGroups'] = associatedGroups
        categories = self.getMultiValue('categories')
        if categories:
            res['getCategory'] = categories
        classifiers = self.getMultiValue('classifiers')
        if classifiers:
            res['getRawClassifier'] = classifiers
        # Must we filter base on some item states ?
        itemStates = self.searchParams.get('itemState', None)
        if itemStates:
            res['review_state'] = itemStates
        return res

    def getMeetingSearchParams(self, mainParams, dateInterval):
        '''Adds to dict p_mainParams the parameters which are specific for
           performing (a) meeting-specific query(ies) in the portal_catalog.'''
        res = mainParams.copy()
        res['portal_type'] = self.meetingConfig.getMeetingTypeName()
        res['getDate'] = {'query': dateInterval, 'range': 'minmax'}
        res['sort_on'] = self.sortKey or 'getDate'
        if self.keywords:
            self.addKeywords(res, 'Title')
        return res

    def getAnnexSearchParams(self, mainParams, dateInterval):
        '''Adds to dict p_mainParams the parameters which are specific for
           performing (an) annex-specific query(ies) in the portal_catalog.'''
        res = mainParams.copy()
        res['portal_type'] = 'MeetingFile'
        res['created'] = {'query': dateInterval, 'range': 'minmax'}
        res['sort_on'] = self.sortKey or 'created'
        if self.keywords:
            # Search among annex title and content
            self.addKeywords(res, 'Title')
            if self.tool.getExtractTextFromFiles():
                self.addKeywords(res, 'indexExtractedText')
        return res

    def queryCatalog(self, params):
        '''Performs a single query catalog.'''
        return self.portalCatalog(**params)[:params['sort_limit']]

    def getValueFromIndex(self, brain, indexName):
        '''Gets the value of index named p_indexName on a b_brain.'''
        if hasattr(brain, indexName):
            return getattr(brain, indexName)
        else:
            index = self.portalCatalog.Indexes[indexName]
            return index.getEntryForObject(brain.getRID())

    def mergeResults(self, results, sortKey):
        '''p_results contains several lists of brains that we need to merge.
           We need to take the p_sortKey into account.'''
        res = []
        moreBrains = True
        nextIndexes = [0] * len(results)
        nextCandidates = {}  # ~{i_listNumber: brain}~
        while moreBrains:
            # Compute next candidates
            nextCandidates.clear()
            i = -1
            for nextIndex in nextIndexes:
                i += 1
                brainsList = results[i]
                if nextIndex < len(brainsList):
                    # There is at least one more candidate in this list
                    nextCandidates[i] = brainsList[nextIndex]
            if not nextCandidates:
                moreBrains = False
            else:
                # Compute the winner among all candidates
                winner = None
                winnerListNumber = None
                for listNumber, candidate in nextCandidates.iteritems():
                    if not winner:
                        winner = candidate
                        winnerListNumber = listNumber
                    else:
                        # Compare the current winner to this candidate
                        winnerKey = self.getValueFromIndex(winner, sortKey)
                        candidateKey = self.getValueFromIndex(candidate, sortKey)
                        # The comparison condition follows sort order
                        if self.sortOrder == 'reverse':
                            condition = winnerKey < candidateKey
                        else:
                            condition = winnerKey > candidateKey
                        if condition:
                            winner = candidate
                            winnerListNumber = listNumber
                        if winner.getRID() == candidate.getRID():
                            nextIndexes[listNumber] += 1
                # Add the winner to the result and prepare next iteration
                res.append(winner)
                nextIndexes[winnerListNumber] += 1
        return res

    def searchAnnexes(self, params):
        '''Executes the portal_catalog search(es) for querying annexes, and
           returns corresponding brains.'''
        res = []  # We will begin by storing here a list of lists of brains.
        # Indeed, several queries may be performed.
        if 'Title' in params:
            # Execute the Title-related query
            tParams = params.copy()
            if 'indexExtractedText' in tParams:
                del tParams['indexExtractedText']
            res.append(self.queryCatalog(tParams))
            del params['Title']  # The title has been "consumed".
            if 'indexExtractedText' in params:
                # Execute the extractedText-related query
                res.append(self.queryCatalog(params))
        # No result yet? Execute the single query from p_params.
        if not res:
            res.append(self.queryCatalog(params))
        if len(res) == 1:
            return res[0]
        else:
            sortKey = params['sort_on']
            return self.mergeResults(res, sortKey)[:params['sort_limit']]

    def run(self):
        '''Creates and executes queries and returns the result.'''
        rq = self.searchParams
        # Determine the start number
        batchStart = int(self.rq.get('b_start', 0))
        # Determine "from" and "to" dates that determine the time period for
        # the search.
        fromDate = getDateFromRequest(rq.get('from_day'),
                                      rq.get('from_month'),
                                      rq.get('from_year'),
                                      start=True)
        toDate = getDateFromRequest(rq.get('to_day'),
                                    rq.get('to_month'),
                                    rq.get('to_year'),
                                    start=False)
        # Prepare the keywords query if keywords have been entered by the user
        if rq.get('keywords', None):
            self.keywords = prepareSearchValue(rq.get('keywords'))
        # Prepare main search parameters.
        mainParams = {'sort_limit': self.tool.getMaxSearchResults(),
                      'sort_order': self.sortOrder}
        # If a filter has been defined on a field (ie the user typed some
        # keywords in a column header for further filtering the search), we take
        # it into account here.
        if self.filterKey:
            mainParams[self.filterKey] = prepareSearchValue(self.filterValue)
        # Perform the search.
        batchSize = self.tool.getMaxShownFound(self.searchedType)
        if self.searchedType == 'MeetingItem':
            params = self.getItemSearchParams(mainParams, [fromDate, toDate])
            itemBrains = self.queryCatalog(params)
            res = Batch(itemBrains, batchSize, batchStart, orphan=0)
        elif self.searchedType == 'Meeting':
            params = self.getMeetingSearchParams(mainParams, [fromDate, toDate])
            meetingBrains = self.queryCatalog(params)
            res = Batch(meetingBrains, batchSize, batchStart, orphan=0)
        elif self.searchedType == 'MeetingFile':
            params = self.getAnnexSearchParams(mainParams, [fromDate, toDate])
            annexBrains = self.searchAnnexes(params)
            res = Batch(annexBrains, batchSize, batchStart, orphan=0)
        return res
# ------------------------------------------------------------------------------
