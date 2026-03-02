# -*- coding: utf-8 -*-
#
# File: utils.py
#

from Products.PloneMeeting.browser.views import _get_contact_from_position_type


def get_item_esign_signatories(obj, listify=False, signature_numbers=[], **kwargs):
    """Helper to get "item" signatories respecting the esign expected format."""
    return obj.getCertifiedSignatures(listify=listify, signature_numbers=signature_numbers, *kwargs)


def get_meeting_esign_signatories(obj, signature_numbers=[], **kwargs):
    """Helper to get "meeting" signatories respecting the esign expected format."""
    signers = obj._get_contacts('signer', the_objects=True)
    return get_esign_signatories(signers, signature_numbers=signature_numbers)


def get_advice_esign_signatories(obj, userid, signature_numbers=[], position_types=[], hp=None, **kwargs):
    """Helper to get "advice" signatories respecting the esign expected format."""
    person, hp = _get_contact_from_position_type(obj, userid, position_types=position_types)
    return get_esign_signatories([hp], signature_numbers=signature_numbers)


def get_esign_signatories(hps, signature_numbers=[]):
    """Helper that will format given p_hps to the required esign signatories format."""
    res = {}
    signature_numbers = signature_numbers or [str(num) for num in range(1, len(hps) + 1)]
    for hp in hps:
        signature_number = signature_numbers[hps.index(hp)]
        res[signature_number] = {}
        res[signature_number]['held_position'] = hp
        res[signature_number]['name'] = hp.get_person_title(include_person_title=False)
        res[signature_number]['shortname'] = hp.get_person_short_title(abbreviate_firstname=True)
        res[signature_number]['function'] = hp.get_prefix_for_gender_and_number(include_value=True)
    return res
