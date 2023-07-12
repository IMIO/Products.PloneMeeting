# encoding: utf-8

from ftw.labels.interfaces import ILabelJar
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_current_user_id
from plone import api
from plone.memoize import ram
from Products.PloneMeeting.utils import get_context_with_request
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class FTWLabelsVocabulary(object):
    """
        Vocabulary that lists available ftw.labels
        labels for the current MeetingConfig.
        Used for DashboardCollection query.
    """
    implements(IVocabularyFactory)

    def __call__(self, context):
        res = []
        context = get_context_with_request(context)

        tool = api.portal.get_tool('portal_plonemeeting')
        try:
            # in some case, like Plone Site creation, context is the Zope app...
            cfg = tool.getMeetingConfig(context)
        except Exception:
            return SimpleVocabulary(res)

        if cfg and cfg.getEnableLabels():
            labels = ILabelJar(cfg).list()
            for label in labels:
                if label['by_user']:
                    title = '{0} (*)'.format(label['title'])
                else:
                    title = label['title']
                res.append(SimpleTerm(
                    label['label_id'],
                    label['label_id'],
                    title))

        return SimpleVocabulary(res)


FTWLabelsVocabularyFactory = FTWLabelsVocabulary()


class FTWLabelsForFacetedFilterVocabulary(object):
    """
        Vocabulary that lists available ftw.labels
        labels for the current MeetingConfig.
        Use in faceted navigation, is current user aware.
    """
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile(
            'Products.PloneMeeting.vocabularies.ftwlabelsforfacetedfiltervocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        # personal labels include current user id
        return date, cfg.getId(), cfg.modified(), get_current_user_id(context.REQUEST)

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        context = get_context_with_request(context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        member_id = get_current_user_id(context.REQUEST)

        res = []
        labels = ILabelJar(cfg).list()
        for label in labels:
            if label['by_user']:
                res.append(SimpleTerm(
                    '{0}:{1}'.format(member_id, label['label_id']),
                    '{0}:{1}'.format(member_id, label['label_id']),
                    '{0} (*)'.format(label['title'])))
            else:
                res.append(SimpleTerm(
                    label['label_id'],
                    label['label_id'],
                    label['title']))
        return SimpleVocabulary(res)


FTWLabelsForFacetedFilterVocabularyFactory = FTWLabelsForFacetedFilterVocabulary()
