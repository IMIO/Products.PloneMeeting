# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from persistent.list import PersistentList
from zope.interface import implements, Interface
from zope import schema
from zope.i18n import translate
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from z3c.form.browser.radio import RadioFieldWidget

from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form

from plone import api
from Products.PloneMeeting import PMMessageFactory as _
from Products.PloneMeeting.utils import findMeetingAdvicePortalType
from Products.PloneMeeting.utils import getHistory
from Products.PloneMeeting.utils import getLastEvent
from Products.PloneMeeting.utils import isModifiedSinceLastVersion


class IMeetingAdvice(Interface):
    """
        MeetingAdvice schema
    """
    advice_group = schema.Choice(
        title=_(u'Group'),
        description=_(u"Choose a group."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_group_vocabulary',
        required=True,
    )
    advice_type = schema.Choice(
        title=_(u'Advice type'),
        description=_(u"Choose an advice type."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_type_vocabulary',
        required=True,
    )
    form.widget('advice_hide_during_redaction', RadioFieldWidget)
    advice_hide_during_redaction = schema.Bool(
        title=_(u'Hide advice during redaction'),
        description=_("If you do not want the advice to be shown immediately after redaction, you can check this "
                      "box.  This will let you or other member of your group work on the advice before showing it.  "
                      "Note that if you lose access to the advice (for example if the item state evolve), "
                      "the advice will be considered 'Not given, was under edition'.  A manager will be able "
                      "to publish it nevertheless."),
        required=False,
    )
    advice_comment = RichText(
        title=_(u"Advice official comment"),
        description=_("Enter the official comment."),
        required=False,
        default_mime_type='text/html',
        output_mime_type='text/html',
        allowed_mime_types=('text/html',),
    )
    advice_observations = RichText(
        title=_(u"Advice observations"),
        description=_("Enter optionnal observations if necessary."),
        required=False,
        default_mime_type='text/html',
        output_mime_type='text/html',
        allowed_mime_types=('text/html',),
    )
    advice_reference = schema.TextLine(
        title=_(u"Advice reference"),
        description=_("Enter a reference for this advice if necessary."),
        required=False,
    )
    form.mode(advice_row_id='hidden')
    advice_row_id = schema.TextLine(
        title=_(u"Advice row id"),
        description=_("Linked advice row id, this is managed programmatically."),
        required=False,
    )


@form.default_value(field=IMeetingAdvice['advice_type'])
def advice_typeDefaultValue(data):
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    # manage when portal_type accessed from the Dexterity types configuration
    return cfg and cfg.getDefaultAdviceType() or ''


@form.default_value(field=IMeetingAdvice['advice_hide_during_redaction'])
def advice_hide_during_redactionDefaultValue(data):
    published = data.context.REQUEST.get('PUBLISHED')
    if not published:
        return False
    tool = api.portal.get_tool('portal_plonemeeting')
    cfg = tool.getMeetingConfig(data.context)
    # manage when portal_type accessed from the Dexterity types configuration
    return cfg and cfg.getDefaultAdviceHiddenDuringRedaction() or False


class MeetingAdvice(Container):
    """ """

    implements(IMeetingAdvice)

    def Title(self):
        '''
          This will construct the title of the advice, moreover, it checks for access
          to a confidential advice.
        '''
        # check that current user is not accessing to an advice that is confidential
        # to him but for which he knows the url to access to...
        parent = self.getParentNode()
        if self.advice_group in parent.adviceIndex and parent.adviceIndex[self.advice_group]['isConfidential']:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            isPowerObserver = tool.isPowerObserverForCfg(cfg)
            isRestrictedPowerObserver = tool.isPowerObserverForCfg(cfg, isRestricted=True)
            if not parent._adviceIsViewableForCurrentUser(cfg,
                                                          isPowerObserver,
                                                          isRestrictedPowerObserver,
                                                          parent.adviceIndex[self.advice_group]):
                raise Unauthorized

        # we can not return a translated msg using _ so translate it
        return translate("Advice given on item ${item_title}",
                         mapping={'item_title': '"%s"' % unicode(self.getParentNode().Title(), 'utf-8')},
                         domain="PloneMeeting",
                         default='Advice given on item "%s"' % self.getParentNode().Title(),
                         context=self.REQUEST)

    def title_or_id(self):
        """ """
        return self.Title()

    def queryState(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    def numberOfAnnexes(self):
        '''Return the number of viewable annexes.'''
        catalog = api.portal.get_tool('portal_catalog')
        return len(catalog(Type='MeetingFile', path='/'.join(self.getPhysicalPath())))

    def _updateAdviceRowId(self):
        '''Make sure advice_row_id is correct.'''
        # the row_id is stored in parent (item) adviceIndex
        item = self.getParentNode()

        # if a powerAdviser is adding an advice, the advice_group is not
        # in the item.adviceIndex, so if not found, check that
        if self.advice_group in item.adviceIndex:
            adviceInfo = item.adviceIndex[self.advice_group]
            row_id = adviceInfo['row_id']
        else:
            # check if it is actually a power adviser adding a not asked advice
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(item)
            if self.advice_group in cfg.getPowerAdvisersGroups():
                row_id = ''
            else:
                raise KeyError('Not able to find a value to set for advice row_id!')
        self.advice_row_id = row_id

    def getHistory(self, *args, **kwargs):
        '''See doc in utils.py.'''
        return getHistory(self, *args, **kwargs)

    def get_advice_given_on(self):
        '''Return the date the advice was given on.
           Returns older date between modified() and last event 'giveAdvice'.'''
        lastEvent = getLastEvent(self, 'giveAdvice')
        if not lastEvent:
            return self.modified()
        else:
            modified = self.modified()
            if lastEvent['time'] < modified:
                return lastEvent['time']
            else:
                return modified

    def versionate_if_relevant(self, comment):
        """Versionate if self was never versioned or
           if it was modified since last version."""
        # only historize advice if it was modified since last historization
        if isModifiedSinceLastVersion(self):
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            # create the historized_item_data before versioning, then removes it after
            # it will still exist on the versioned object
            self.historized_item_data = PersistentList()
            item = self.getParentNode()
            if cfg.getHistorizeItemDataWhenAdviceIsGiven():
                # compute 'historized_item_data', save every active RichText fields
                usedItemAttrs = cfg.getUsedItemAttributes()
                self.historized_item_data.append({'field_name': 'title',
                                                  'field_content': item.Title()})
                for field in item.Schema().fields():
                    fieldName = field.getName()
                    if field.widget.getName() == 'RichWidget' and \
                       (fieldName in usedItemAttrs or not field.optional):
                        self.historized_item_data.append({'field_name': fieldName,
                                                          'field_content': field.get(item)})
            pr = api.portal.get_tool('portal_repository')
            pr.save(obj=self, comment=comment)
            delattr(self, 'historized_item_data')


class MeetingAdviceSchemaPolicy(DexteritySchemaPolicy):
    """ """

    def bases(self, schemaName, tree):
        return (IMeetingAdvice, )


class AdviceGroupVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """"""
        terms = []
        tool = api.portal.get_tool('portal_plonemeeting')

        # take into account groups for wich user can add an advice
        # while adding an advice, the context is his parent, aka a MeetingItem
        alterable_advices_groups = []
        if context.meta_type == 'MeetingItem':
            alterable_advices_groups = [groupId for groupId, groupTitle in context.getAdvicesGroupsInfosForUser()[0]]
        # take into account groups for which user can edit an advice
        elif context.portal_type.startswith('meetingadvice'):
            alterable_advices_groups = [groupId for groupId, groupTitle in context.getAdvicesGroupsInfosForUser()[1]]
            # make sure advice_group selected on advice is in the vocabulary
            if not context.advice_group in alterable_advices_groups:
                alterable_advices_groups.append(context.advice_group)

        # manage case where we have several meetingadvice portal_types
        # depending on current portal_type, clean up selectable groups
        itemObj = context.meta_type == 'MeetingItem' and context or context.getParentNode()
        current_portal_type = findMeetingAdvicePortalType(context)
        alterable_advices_groups = [
            groupId for groupId in alterable_advices_groups
            if (itemObj.adapted()._advicePortalTypeForAdviser(groupId) == current_portal_type or
                (context.portal_type.startswith('meetingadvice') and groupId == context.advice_group))]

        # create vocabulary
        for alterable_advices_group in alterable_advices_groups:
            terms.append(SimpleTerm(alterable_advices_group,
                                    alterable_advices_group,
                                    getattr(tool, alterable_advices_group).Title()))
        return SimpleVocabulary(terms)


class AdviceTypeVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        terms = []
        cfg = context.portal_plonemeeting.getMeetingConfig(context)
        # manage when portal_type accessed from the Dexterity types configuration
        if cfg:
            usedAdviceTypes = list(cfg.getUsedAdviceTypes())

            # now wipeout usedAdviceTypes depending on current meetingadvice portal_type
            itemObj = context.meta_type == 'MeetingItem' and context or context.getParentNode()
            current_portal_type = findMeetingAdvicePortalType(context)
            usedAdviceTypes = [usedAdviceType for usedAdviceType in usedAdviceTypes
                               if usedAdviceType in itemObj.adapted()._adviceTypesForAdviser(current_portal_type)]

            # remove the 'asked_again' value, it can only be used if it is the current context.advice_type
            # and it will be added here under if necessary
            if 'asked_again' in usedAdviceTypes:
                usedAdviceTypes.remove('asked_again', )
            # make sure if an adviceType was used for context and it is no more available, it
            # appears in the vocabulary and is so useable...
            if context.portal_type == 'meetingadvice' and not context.advice_type in usedAdviceTypes:
                usedAdviceTypes.append(context.advice_type)
            for advice_id, advice_title in cfg.listAdviceTypes().items():
                if advice_id in usedAdviceTypes:
                    terms.append(SimpleTerm(advice_id, advice_id, advice_title))

        return SimpleVocabulary(terms)
