# -*- coding: utf-8 -*-

from natsort import humansorted
from operator import attrgetter
from Products.PloneMeeting.external.utils import send_json_request
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class BaseVisionVocabulary(object):

    implements(IVocabularyFactory)

    def __call__(self, context, endpoint):
        """ """
        terms = []
        for info in send_json_request(endpoint):
            terms.append(SimpleTerm(info['id'], info['id'], info['name']))
        terms = humansorted(terms, key=attrgetter('title'))
        return SimpleVocabulary(terms)


class VisionProjectsVocabulary(BaseVisionVocabulary):

    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        return super(VisionProjectsVocabulary, self).__call__(context, endpoint="projects")


VisionProjectsVocabularyFactory = VisionProjectsVocabulary()


class VisionTasksVocabulary(BaseVisionVocabulary):

    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        return super(VisionTasksVocabulary, self).__call__(context, endpoint="tasks")


VisionTasksVocabularyFactory = VisionTasksVocabulary()
