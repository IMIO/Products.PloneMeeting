# -*- coding: utf-8 -*-
#
# File: utils.py
#

from Products.PloneMeeting.browser.views import _get_contact_from_position_type


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
