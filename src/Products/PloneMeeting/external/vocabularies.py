# -*- coding: utf-8 -*-

from Products.PloneMeeting.external.utils import send_json_request
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class VisionProjectsVocabulary(object):

    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        terms = []
        content = send_json_request("projects")
        if content:
            for info in content:
                terms.append(SimpleTerm(info['id'], info['id'], info['name']))
        return SimpleVocabulary(terms)

VisionProjectsVocabularyFactory = VisionProjectsVocabulary()
