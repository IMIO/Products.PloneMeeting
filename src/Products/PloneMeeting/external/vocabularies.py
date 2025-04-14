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
            # concatenate element's project, parent and name for term title
            res = []
            project_name = info['infos'].get('project', {}).get('name')
            if project_name:
                res.append("<span class='discreet'>%s</span>" % project_name)
            parent_name = info['infos']['parent'].get('name')
            if parent_name:
                res.append("<span class='discreet'>%s</span>" % parent_name)
            res.append(info['name'])
            title = u" / ".join(res)
            terms.append(SimpleTerm(info['id'], info['id'], title))
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
