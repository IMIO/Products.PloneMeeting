# -*- coding: utf-8 -*-
#
# File: utils.py
#


def get_item_esign_signatories(obj, listify=False, signature_numbers=[], **kwargs):
    """Helper to get "item" signatories respecting the esign expected format."""
    return obj.getCertifiedSignatures(listify=listify, signature_numbers=signature_numbers, *kwargs)


def get_meeting_esign_signatories(obj, signature_numbers=[], **kwargs):
    """Helper to get "meeting" signatories respecting the esign expected format."""
    res = {}
    signatories = obj.get_signatories(the_objects=True, by_signature_number=True, **kwargs)
    for signature_number, hp in signatories.items():
        if signature_numbers and signature_number not in signature_numbers:
            continue
        res[signature_number] = {}
        res[signature_number]['held_position'] = hp
        res[signature_number]['name'] = hp.get_person_title(include_person_title=False)
        res[signature_number]['shortname'] = hp.get_person_short_title(abbreviate_firstname=True)
        res[signature_number]['function'] = hp.get_prefix_for_gender_and_number(include_value=True)
    return res

def get_advice_esign_signatories(obj, signature_numbers=[], **kwargs):
    """Helper to get "advice" signatories respecting the esign expected format."""
    return
