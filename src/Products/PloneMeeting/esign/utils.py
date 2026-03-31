# -*- coding: utf-8 -*-
#
# File: utils.py
#

from imio.esign.adapters import ISignable
from imio.esign.utils import add_files_to_session
from imio.esign.utils import get_file_info
from imio.esign.utils import get_sessions_for
from imio.helpers.utils import is_pdf
from imio.zamqp.pm.utils import next_scan_id_pm
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.browser.views import get_contact_from_position_type
from Products.PloneMeeting.config import ESIGNWATCHERS_GROUP_SUFFIX
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.utils import reindex_object
from zope.i18n import translate


def get_item_esign_signatories(obj, listify=False, signature_numbers=['1', '2'], certified=True, **kwargs):
    """Helper to get "item" signatories respecting the esign expected format."""
    if certified:
        # certified signatures
        return obj.getCertifiedSignatures(listify=listify, signature_numbers=signature_numbers, *kwargs)
    else:
        # item meeting signatures
        signers = obj.get_item_signatories(the_objects=True)
        # sort and keep given p_signature_numbers
        sorted_signers = [signer[0] for signer in sorted(signers.items(), key=lambda x: int(x[1]))
                          if not signature_numbers or signer[1] in signature_numbers]
        return get_esign_signatories(sorted_signers, signature_numbers=signature_numbers)


def get_meeting_esign_signatories(obj, signature_numbers=['1', '2'], **kwargs):
    """Helper to get "meeting" signatories respecting the esign expected format."""
    # use meeting.get_signatories that keeps order
    signers = obj.get_signatories(the_objects=True)
    # sort and keep given p_signature_numbers
    sorted_signers = [signer[0] for signer in sorted(signers.items(), key=lambda x: int(x[1]))
                      if not signature_numbers or signer[1] in signature_numbers]
    return get_esign_signatories(sorted_signers, signature_numbers=signature_numbers)


def get_advice_esign_signatories(obj, userid, signature_numbers=['1', '2'], position_types=[], **kwargs):
    """Helper to get "advice" signatories respecting the esign expected format."""
    hp = get_contact_from_position_type(obj, userid, position_types=position_types)
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


def esign_access_groups():
    """Return groups of the user giving access to sessions.
       MeetingManagers and eSign watchers have access."""
    tool = api.portal.get_tool('portal_plonemeeting')
    return tool.get_filtered_plone_groups_for_user(
        suffixes=[MEETINGMANAGERS_GROUP_SUFFIX, ESIGNWATCHERS_GROUP_SUFFIX])


def _add_annexes_to_sign_session(obj, annexes, cfg, pod_template, signers, seal=None, check_is_pdf=True, show_msg=False):
    """ """
    context_uid = obj.UID()
    # check that file is PDF and that annex is not already in a esign session not in state "finalized"
    correct_annexes = []
    for annex in annexes:
        if check_is_pdf and not is_pdf(annex):
            api.portal.show_message(
                translate(
                    'annex_not_pdf_error',
                    domain="PloneMeeting",
                    mapping={'annex_title': safe_unicode(annex.Title())},
                    default="Annex \"${annex_title}\" must be PDF to be added to a session!",
                    context=obj.REQUEST),
                type="warning",
                request=obj.REQUEST)
            continue
        already_in_draft_session = False
        annex_uid = annex.UID()
        for session_id, session in get_sessions_for(context_uid).items():
            if session['state'] != "finalized" and \
               get_file_info(session_id, annex_uid):
                api.portal.show_message(
                    translate(
                        'annex_already_in_not_finalized_session_error',
                        domain="PloneMeeting",
                        mapping={'annex_title': safe_unicode(annex.Title()),
                                 'session_id': session_id},
                        default="Annex \"${annex_title}\" is already in session \"${session_id}\" that is not finalized!",
                        context=obj.REQUEST),
                    type="warning",
                    request=obj.REQUEST)
                already_in_draft_session = True
                break
        if not already_in_draft_session:
            correct_annexes.append(annex)
    annexes = correct_annexes

    if not annexes:
        return

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
    discriminators = ISignable(obj).get_discriminators(annex, pod_template)
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
            translate(
                'annex_added_to_session',
                domain="PloneMeeting",
                mapping={'annex_title': safe_unicode(annex.Title()),
                         'session_id': session_id},
                default="Annex \"${annex_title}\" was added to session \"${session_id}\".",
                context=obj.REQUEST),
            request=obj.REQUEST)
    return session_id, session
