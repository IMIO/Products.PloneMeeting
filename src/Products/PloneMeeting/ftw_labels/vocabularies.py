# encoding: utf-8

from zope.interface import implements
from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from plone import api
from ftw.labels.interfaces import ILabelJar


class FTWLabelsVocabulary(object):
    """
        Vocabulary that lists available ftw.labels
        labels for the current MeetingConfig.
    """
    implements(IVocabularyFactory)

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
