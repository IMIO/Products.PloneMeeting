# -*- coding: utf-8 -*-
#
# File: utils.py
#

from imio.esign.adapters import ISignable
from imio.esign.utils import add_files_to_session
from imio.zamqp.pm.utils import next_scan_id_pm
from plone import api
from plone.rfc822.interfaces import IPrimaryFieldInfo
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.views import _get_contact_from_position_type
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import reindex_object
from zope.i18n import translate


def get_item_esign_signatories(obj, listify=False, signature_numbers=['1', '2'], **kwargs):
    """Helper to get "item" signatories respecting the esign expected format."""
    return obj.getCertifiedSignatures(listify=listify, signature_numbers=signature_numbers, *kwargs)


def get_meeting_esign_signatories(obj, signature_numbers=['1', '2'], **kwargs):
    """Helper to get "meeting" signatories respecting the esign expected format."""
    # use meeting.get_signatories that keeps order
    signers = obj.get_signatories(the_objects=True)
    # sort and keep given p_signature_numbers
    sorted_signers = [signer[0] for signer in sorted(signers.items(), key=lambda x:int(x[1]))
                      if not signature_numbers or signer[1] in signature_numbers]
    return get_esign_signatories(sorted_signers, signature_numbers=signature_numbers)


def get_advice_esign_signatories(obj, userid, signature_numbers=['1', '2'], position_types=[], **kwargs):
    """Helper to get "advice" signatories respecting the esign expected format."""
    person, hp = _get_contact_from_position_type(obj, userid, position_types=position_types)
    return get_esign_signatories([hp], signature_numbers=signature_numbers)


def get_cfg_esign_signatories(cfg, signature_numbers=['1', '2'], **kwargs):
    """Helper to get "meeting" signatories respecting the esign expected format."""
    return cfg.getCertifiedSignatures(computed=True, signature_numbers=signature_numbers, **kwargs)


def get_esign_signatories(hps, signature_numbers=['1', '2']):
    """Helper that will format given p_hps to the required esign signatories format."""
    res = {}
    signature_numbers = signature_numbers or [str(num) for num in range(1, len(hps) + 1)]
    for signature_number in signature_numbers:
        # check in case we have less hps than asked signature_numbers
        index = signature_numbers.index(signature_number)
        if len(hps) <= index:
            break
        hp = hps[index]
        res[signature_number] = {}
        res[signature_number]['held_position'] = hp
        res[signature_number]['name'] = hp.get_person_title(include_person_title=False)
        res[signature_number]['shortname'] = hp.get_person_short_title(abbreviate_firstname=True)
        res[signature_number]['function'] = hp.get_prefix_for_gender_and_number(include_value=True)
        res[signature_number]['shortfunction'] = hp.get_label()
    return res


def is_pdf(annex):
    """ """
    file_field_name = IPrimaryFieldInfo(annex).fieldname
    file_obj = getattr(annex, file_field_name)
    return file_obj.contentType == 'application/pdf'


def _add_annexes_to_sign_session(obj, annexes, cfg, signers, seal=None, check_is_pdf=True, show_msg=False):
    """ """
    if check_is_pdf:
        correct_annexes = []
        for annex in annexes:
            if not is_pdf(annex):
                api.portal.show_message(
                    translate('annex_not_pdf_error',
                              domain="PloneMeeting",
                              mapping={'annex_url': annex.absolute_url()}),
                    type="warning",
                    request=obj.REQUEST)
            else:
                correct_annexes.append(annex)
        annexes = correct_annexes

    # add a scan_id to each annex if not already the case
    for annex in annexes:
        if not annex.scan_id:
            annex.scan_id = next_scan_id_pm()
        # reindex scan_id and metadata
        reindex_object(annex, idxs=['scan_id'], update_metadata=1)

    # signers must be passed as a list of data with userid, email, name, label
    signers = [
        (signer['userid'], signer['email'], signer['name'], signer['function'])
        for signer in signers]
    files_uids = [annex.UID() for annex in annexes]
    title = _(u"[iA.Délib] %s - Session {sign_id}" % safe_unicode(
        cfg.Title(include_config_group=True)))
    discriminators = ISignable(obj).get_discriminators(annex)
    watchers = ISignable(obj).get_watchers()
    create_session_custom_data = {'cfg_id': cfg.getId()}
    session_id, session = add_files_to_session(
        signers,
        files_uids,
        seal=seal,
        title=title,
        discriminators=discriminators,
        watchers=watchers,
        create_session_custom_data=create_session_custom_data)
    for annex in annexes:
        api.portal.show_message(
            translate('annex_added_to_session',
                      domain="PloneMeeting",
                      mapping={'annex_title': annex.Title()}),
            request=obj.REQUEST)
    return session_id, session
