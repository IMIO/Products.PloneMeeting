# -*- coding: utf-8 -*-
#
# File: validators.py
#
# Copyright (c) 2017 by Imio.be
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

from DateTime import DateTime
from Products.PloneMeeting.utils import getInterface
from Products.validation.interfaces.IValidator import IValidator
from zope.component import getGlobalSiteManager
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import implements


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


class CertifiedSignaturesValidator:
    ''' '''
    implements(IValidator)

    def __init__(self, name, title='', description=''):
        self.name = name
        self.title = title
        self.description = description

    def __call__(self, value, *args, **kwargs):
        '''Validate the 'certifiedSignatures' field, check that :
           - signatures are sorted by signature number;
           - if dates (date_from and date_to) are provided, both are provided and it respects correct format;
           - 2 lines are not using same 'number/datefrom/dateto'.'''
        lastSignatureNumber = 0
        row_number = 0
        portal = getSite()
        # we will store a "hash" of every signatures so we may check
        # that 2 signatures does not use same number/datefrom/dateto
        signHashes = []
        for signature in value:
            # bypass 'template_row_marker'
            if 'orderindex_' in signature and signature['orderindex_'] == 'template_row_marker':
                continue
            row_number += 1
            # check that signatures are correctly ordered by signature number
            signatureNumber = int(signature['signatureNumber'])
            if signatureNumber < lastSignatureNumber:
                return translate('error_certified_signatures_order',
                                 domain='PloneMeeting',
                                 context=portal.REQUEST)
            lastSignatureNumber = signatureNumber
            # if a date_from is defined, a date_to is required and vice versa
            date_from = signature['date_from']
            date_to = signature['date_to']
            # stop checks if no date provided
            if not date_from and not date_to:
                pass
            else:
                # if a date is provided, both are required
                if (date_from and not date_to) or \
                   (date_to and not date_from):
                    return translate('error_certified_signatures_both_dates_required',
                                     mapping={'row_number': row_number},
                                     domain='PloneMeeting',
                                     context=portal.REQUEST)
                try:
                    datetime_from = DateTime(date_from)
                    datetime_to = DateTime(date_to)
                    # respect right string format?
                    # datefrom <= dateto?
                    if not datetime_from.strftime('%Y/%m/%d') == date_from or \
                       not datetime_to.strftime('%Y/%m/%d') == date_to or \
                       not datetime_from <= datetime_to:
                        raise SyntaxError
                except:
                    return translate('error_certified_signatures_invalid_dates',
                                     mapping={'row_number': row_number},
                                     domain='PloneMeeting',
                                     context=portal.REQUEST)
            # now check that 2 signatures having same number does not have same period
            # indeed 2 signatures with same number and period is nonsense, the first will still be used
            signHash = "{0}__{1}__{2}".format(signatureNumber, date_from, date_to)
            if signHash in signHashes:
                return translate('error_certified_signatures_duplicated_entries',
                                 mapping={'row_number': row_number},
                                 domain='PloneMeeting',
                                 context=portal.REQUEST)
            signHashes.append(signHash)


# Helper class for validating workflow interfaces ------------------------------
WRONG_INTERFACE = 'You must specify here interface "%s" or a subclass of it.'
NO_ADAPTER_FOUND = 'No adapter was found that provides "%s" for "%s".'


class WorkflowInterfacesValidator:
    '''Checks that declared interfaces exist and that adapters were defined for it.'''

    implements(IValidator)

    def __init__(self, baseInterface, baseWorkflowInterface):
        self.baseInterface = baseInterface
        self.baseWorkflowInterface = baseWorkflowInterface

    def _getPackageName(self, klass):
        '''Returns the full package name if p_klass.'''
        return '%s.%s' % (klass.__module__, klass.__name__)

    def __call__(self, value, *args, **kwargs):
        # Get the interface corresponding to the name specified in p_value.
        theInterface = None
        try:
            theInterface = getInterface(value)
        except Exception, e:
            return str(e)
        # Check that this interface is self.baseWorkflowInterface or
        # a subclass of it.
        if not issubclass(theInterface, self.baseWorkflowInterface):
            return WRONG_INTERFACE % (self._getPackageName(
                                      self.baseWorkflowInterface))
        # Check that there exits an adapter that provides theInterface for
        # self.baseInterface.
        sm = getGlobalSiteManager()
        adapter = sm.adapters.lookup1(self.baseInterface, theInterface)
        if not adapter:
            return NO_ADAPTER_FOUND % (self._getPackageName(theInterface),
                                       self._getPackageName(self.baseInterface))
