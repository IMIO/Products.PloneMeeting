# encoding: utf-8

from ftw.labels.interfaces import ILabelJar
from imio.helpers import EMPTY_STRING
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.cache import get_current_user_id
from plone import api
from plone.memoize import ram
from Products.PloneMeeting.ftw_labels.utils import filter_access_global_labels
from Products.PloneMeeting.utils import get_context_with_request
from zope.i18n import translate
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

    def __call__(self, context, include_personal_labels=True):
        res = []
        context = get_context_with_request(context)

        tool = api.portal.get_tool('portal_plonemeeting')
        try:
            # in some case, like Plone Site creation, context is the Zope app...
            cfg = tool.getMeetingConfig(context)
        except Exception:
            return SimpleVocabulary(res)

        if cfg and 'labels' in cfg.getUsedItemAttributes():
            labels = ILabelJar(cfg).list()
            for label in labels:
                if label['by_user']:
                    if include_personal_labels is False:
                        continue
                    title = '{0} ({1}) (*)'.format(label['title'], label['label_id'])
                else:
                    title = '{0} ({1})'.format(label['title'], label['label_id'])
                res.append(SimpleTerm(
                    label['label_id'],
                    label['label_id'],
                    title))

        return SimpleVocabulary(res)


FTWLabelsVocabularyFactory = FTWLabelsVocabulary()


class ConfigFTWLabelsVocabulary(FTWLabelsVocabulary):
    """
        Vocabulary used for MeetingConfig.labelsConfig
    """
    def __call__(self, context):
        res = super(ConfigFTWLabelsVocabulary, self).__call__(
            context, include_personal_labels=False)
        res._terms.insert(
            0,
            SimpleTerm("*",
                       "*",
                       '{0} (*)'.format(
                        translate('default_for_all_labels',
                                  domain='PloneMeeting',
                                  context=context.REQUEST).encode('utf-8'))))
        return res


ConfigFTWLabelsVocabularyFactory = ConfigFTWLabelsVocabulary()


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
        # personal labels include current user id, more over global labels
        # are not viewable by everybody
        return date, cfg.getId(), cfg.modified(), get_current_user_id(context.REQUEST)

    @ram.cache(__call___cachekey)
    def __call__(self, context):
        context = get_context_with_request(context)
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        member_id = get_current_user_id(context.REQUEST)

        res = []
        # ftw.labels will index "_" when no label selected
        res.append(
            SimpleTerm(EMPTY_STRING,
                       EMPTY_STRING,
                       translate('(None)',
                                 domain='PloneMeeting',
                                 context=context.REQUEST)))

        # only keep labels the user can view
        labels = filter_access_global_labels(ILabelJar(cfg))
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
