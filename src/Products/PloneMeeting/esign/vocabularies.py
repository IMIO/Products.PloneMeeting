# -*- coding: utf-8 -*-
#
# File: vocabularies.py
#

from Products.PloneMeeting.vocabularies import BaseHeldPositionsVocabulary


class PMSignersVocabulary(BaseHeldPositionsVocabulary):
    """Override of the imio.esign.signers vocabulary, signers to order in the
       imio.esign settings: every active held_position having the "signer" usage,
       term value is the held_position UID."""

    def __call__(self, context):
        return super(PMSignersVocabulary, self).__call__(
            context,
            usage='signer',
            include_usages=False,
            include_defaults=False,
            include_signature_number=False)


PMSignersVocabularyFactory = PMSignersVocabulary()
