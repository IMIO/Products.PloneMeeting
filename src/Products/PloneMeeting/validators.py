# -*- coding: utf-8 -*-

from collective.contact.plonegroup.browser.settings import IContactPlonegroupConfig
from collective.contact.plonegroup.config import get_registry_functions
from collective.contact.plonegroup.utils import get_all_suffixes
from collective.contact.plonegroup.utils import get_organizations
from collective.contact.plonegroup.utils import get_plone_group_id
from datetime import date
from DateTime import DateTime
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.indexes import REAL_ORG_UID_PATTERN
from Products.PloneMeeting.utils import get_item_validation_wf_suffixes
from Products.PloneMeeting.utils import getInterface
from Products.validation.interfaces.IValidator import IValidator
from z3c.form import validator
from zope.component import getGlobalSiteManager
from zope.component import provideAdapter
from zope.component.hooks import getSite
from zope.i18n import translate
from zope.interface import implements
from zope.interface import Invalid


__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


def _validate_certified_signatures(value):
    '''Validate the certified signatures format, check that :
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
        # for now, key may be signatureNumber (MeetingConfig) or signature_number (organization)
        signatureNumber = int(signature.get('signatureNumber', signature.get('signature_number')))
        if signatureNumber < lastSignatureNumber:
            return translate('error_certified_signatures_order',
                             domain='PloneMeeting',
                             context=portal.REQUEST)
        lastSignatureNumber = signatureNumber
        # if a date_from is defined, a date_to is required and vice versa
        # as this work as AT and DX validator, we make sure we have string date
        # because it is the case for AT but for DX, we have datetime.date objects
        date_from = signature['date_from']
        date_to = signature['date_to']
        date_from = isinstance(date_from, date) and date_from.strftime('%Y/%m/%d') or date_from
        date_to = isinstance(date_to, date) and date_to.strftime('%Y/%m/%d') or date_to
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
            except Exception:
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


class DXCertifiedSignaturesValidator(validator.SimpleFieldValidator):
    """z3c.form validator class for certified signatures format.
    """

    def validate(self, value):
        """
        """
        error = _validate_certified_signatures(value)
        if error:
            raise Invalid(error)


class ATCertifiedSignaturesValidator:
    ''' '''
    implements(IValidator)

    def __init__(self, name, title='', description=''):
        self.name = name
        self.title = title
        self.description = description

    def __call__(self, value, *args, **kwargs):
        """ """
        return _validate_certified_signatures(value)


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
        # Check that it exits an adapter that provides theInterface for
        # self.baseInterface.
        sm = getGlobalSiteManager()
        adapter = sm.adapters.lookup1(self.baseInterface, theInterface)
        if not adapter:
            return NO_ADAPTER_FOUND % (self._getPackageName(theInterface),
                                       self._getPackageName(self.baseInterface))


# Complete validation of collective.contact.plonegroup settings "functions"
class PloneGroupSettingsFunctionsValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        # check that if a suffix is removed, it is not used in MeetingConfig or MeetingItems
        stored_suffixes = get_all_suffixes(only_enabled=True)
        # get removed suffixes...
        saved_suffixes = [func['fct_id'] for func in value]
        saved_enabled_suffixes = [func['fct_id'] for func in value if func['enabled']]
        removed_suffixes = list(set(stored_suffixes) - set(saved_enabled_suffixes))
        really_removed_suffixes = list(set(stored_suffixes) - set(saved_suffixes))
        org_uids = get_organizations(only_selected=False, the_objects=False)
        removed_plonegroups = [
            get_plone_group_id(org_uid, removed_suffix)
            for org_uid in org_uids
            for removed_suffix in removed_suffixes]
        # ... and new defined fct_orgs as it will remove some suffixed groups
        stored_functions = get_registry_functions()
        old_functions = {dic['fct_id']: {'fct_title': dic['fct_title'],
                                         'fct_orgs': dic['fct_orgs'],
                                         'enabled': dic['enabled']}
                         for dic in stored_functions}
        new_functions = {dic['fct_id']: {'fct_title': dic['fct_title'],
                                         'fct_orgs': dic['fct_orgs'],
                                         'enabled': dic['enabled']}
                         for dic in value}
        for new_function, new_function_infos in new_functions.items():
            if new_function_infos['fct_orgs'] and \
               old_functions[new_function]['fct_orgs'] != new_function_infos['fct_orgs']:
                # check that Plone group is empty for not selected fct_orgs
                for org_uid in org_uids:
                    if org_uid in new_function_infos['fct_orgs']:
                        continue
                    removed_plonegroups.append(get_plone_group_id(org_uid, new_function))
            elif new_function_infos['enabled'] is False:
                # check that Plone groups are all empty
                for org_uid in org_uids:
                    removed_plonegroups.append(get_plone_group_id(org_uid, new_function))

        # check that plonegroups and suffixes not used in MeetingConfigs
        removed_plonegroups = set(removed_plonegroups)
        tool = api.portal.get_tool('portal_plonemeeting')
        # advisers
        advisers_removed_plonegroups = [
            REAL_ORG_UID_PATTERN.format(removed_plonegroup_id.split('_')[0])
            for removed_plonegroup_id in removed_plonegroups
            if removed_plonegroup_id.endswith('_advisers')]
        for cfg in tool.objectValues('MeetingConfig'):
            msg = _("can_not_delete_plone_group_meetingconfig",
                    mapping={'cfg_title': safe_unicode(cfg.Title(include_config_group=True))})
            # copyGroups
            if removed_plonegroups.intersection(cfg.getSelectableCopyGroups()):
                raise Invalid(msg)
            # advisers (selectableAdvisers/selectableAdviserUsers)
            if set(advisers_removed_plonegroups).intersection(cfg.getSelectableAdvisers()) or \
               set(advisers_removed_plonegroups).intersection(cfg.getSelectableAdviserUsers()):
                raise Invalid(msg)
            # suffixes, values are like 'suffix_proposing_group_level1reviewers'
            composed_values_attributes = ['itemAnnexConfidentialVisibleFor',
                                          'adviceAnnexConfidentialVisibleFor',
                                          'meetingAnnexConfidentialVisibleFor',
                                          'itemInternalNotesEditableBy']
            for composed_values_attr in composed_values_attributes:
                values = cfg.getField(composed_values_attr).getAccessor(cfg)()
                values = [v for v in values
                          for r in removed_suffixes if r in v]
                if values:
                    raise Invalid(msg)
            # itemWFValidationLevels, may be disabled if validation level also disabled
            # but not removed
            item_enabled_val_suffixes = get_item_validation_wf_suffixes(cfg)
            if set(really_removed_suffixes).intersection(item_enabled_val_suffixes):
                raise Invalid(msg)
            all_item_val_suffixes = get_item_validation_wf_suffixes(cfg, only_enabled=False)
            if set(removed_suffixes).intersection(all_item_val_suffixes):
                raise Invalid(msg)
        # check that plone_group not used in MeetingItems
        # need to be performant or may kill the instance when several items exist
        if removed_plonegroups:
            catalog = api.portal.get_tool('portal_catalog')
            # copy_groups
            brains = catalog.unrestrictedSearchResults(
                meta_type="MeetingItem", getCopyGroups=tuple(removed_plonegroups))
            if not brains:
                brains = catalog.unrestrictedSearchResults(
                    meta_type="MeetingItem", indexAdvisers=tuple(advisers_removed_plonegroups))
            for brain in brains:
                item = brain.getObject()
                if item.isDefinedInTool():
                    msgid = "can_not_delete_plone_group_config_meetingitem"
                else:
                    msgid = "can_not_delete_plone_group_meetingitem"
                msg = _(msgid, mapping={'item_url': item.absolute_url()})
                raise Invalid(msg)


validator.WidgetValidatorDiscriminators(
    PloneGroupSettingsFunctionsValidator, field=IContactPlonegroupConfig['functions'])
provideAdapter(PloneGroupSettingsFunctionsValidator)


# Complete validation of collective.contact.plonegroup settings "organizations"
class PloneGroupSettingsOrganizationsValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        selected_org_uids = get_organizations(only_selected=True, the_objects=False)
        removed_org_uids = set(selected_org_uids).difference(value)
        tool = api.portal.get_tool('portal_plonemeeting')
        for cfg in tool.objectValues('MeetingConfig'):
            # usingGroups
            if removed_org_uids.intersection(cfg.getUsingGroups()):
                msg = _("can_not_unselect_plone_group_meetingconfig",
                        mapping={'cfg_title': safe_unicode(cfg.Title(include_config_group=True))})
                raise Invalid(msg)

        # check that removed orgs are not used as groups_in_charge of an organization
        orgs = get_organizations(only_selected=False, the_objects=True)
        for org in orgs:
            if removed_org_uids.intersection(org.groups_in_charge):
                msgid = "can_not_unselect_plone_group_org"
                msg = _(msgid, mapping={'org_url': org.absolute_url()})
                raise Invalid(msg)


validator.WidgetValidatorDiscriminators(
    PloneGroupSettingsOrganizationsValidator, field=IContactPlonegroupConfig['organizations'])
provideAdapter(PloneGroupSettingsOrganizationsValidator)
