# encoding: utf-8

from ftw.labels.interfaces import ILabelJar
from imio.helpers.cache import get_cachekey_volatile
from plone import api
from plone.memoize import ram
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class FTWLabelsVocabulary(object):
    """
        Vocabulary that lists available ftw.labels
        labels for the current MeetingConfig.
    """
    implements(IVocabularyFactory)

    def __call___cachekey(method, self, context, classifiers=False):
        '''cachekey method for self.__call__.'''
        date = get_cachekey_volatile('Products.PloneMeeting.vocabularies.ftwlabelsvocabulary')
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        return date, cfg, classifiers

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        res = []

        labels = ILabelJar(cfg).list()
        for label in labels:
            res.append(
                SimpleTerm(label['label_id'], label['label_id'], label['title']))

        return SimpleVocabulary(res)

FTWLabelsVocabularyFactory = FTWLabelsVocabulary()
