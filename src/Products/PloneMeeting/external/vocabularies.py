# -*- coding: utf-8 -*-

from natsort import humansorted
from operator import attrgetter
from Products.PloneMeeting.external.forms import projects_default
from Products.PloneMeeting.external.forms import tasks_default
from Products.PloneMeeting.external.utils import send_vision_json_request
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class BaseVisionVocabulary(object):

    implements(IVocabularyFactory)

    def __call__(self, context, endpoint, selected_values=[]):
        """ """
        terms = []
        for info in send_vision_json_request(endpoint):
            # concatenate element's project, parent and name for term title
            res = []
            # store also non HTML raw value to be able to sort it correctly
            raw_res = []
            project_name = info['infos'].get('project', {}).get('name')
            if project_name:
                res.append("<span class='discreet'>%s</span>" % project_name)
                raw_res.append(project_name)
            parent_name = info['infos']['parent'].get('name')
            if parent_name:
                res.append("<span class='discreet'>%s</span>" % parent_name)
                raw_res.append(parent_name)
            res.append(info['name'])
            raw_res.append(info['name'])
            title = u" / ".join(res)
            if info['id'] in selected_values:
                title += u' [%s]' % translate(
                    'Linked', domain="PloneMeeting", context=context.REQUEST)
            raw_title = u" / ".join(raw_res)
            term = SimpleTerm(info['id'], info['id'], title)
            term.raw_title = raw_title
            terms.append(term)
        terms = humansorted(terms, key=attrgetter('raw_title'))
        return SimpleVocabulary(terms)


class VisionProjectsVocabulary(BaseVisionVocabulary):

    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        selected_values = projects_default(context)
        return super(VisionProjectsVocabulary, self).__call__(
            context, endpoint="projects", selected_values=selected_values)


VisionProjectsVocabularyFactory = VisionProjectsVocabulary()


class VisionTasksVocabulary(BaseVisionVocabulary):

    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        selected_values = tasks_default(context)
        return super(VisionTasksVocabulary, self).__call__(
            context, endpoint="tasks", selected_values=selected_values)


VisionTasksVocabularyFactory = VisionTasksVocabulary()
