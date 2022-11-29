# -*- coding: utf-8 -*-

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from collective.contact.plonegroup.utils import get_organization
from dexterity.localrolesfield.field import LocalRoleField
from imio.history.interfaces import IImioHistory
from imio.history.utils import getLastAction
from imio.history.utils import getLastWFAction
from imio.prettylink.interfaces import IPrettyLink
from plone import api
from plone.app.textfield import RichText
from plone.dexterity.content import Container
from plone.dexterity.schema import DexteritySchemaPolicy
from plone.directives import form
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IDXMeetingContent
from Products.PloneMeeting.utils import findMeetingAdvicePortalType
from Products.PloneMeeting.utils import getWorkflowAdapter
from Products.PloneMeeting.utils import get_event_field_data
from Products.PloneMeeting.utils import historize_object_data
from Products.PloneMeeting.utils import isModifiedSinceLastVersion
from Products.PloneMeeting.widgets.pm_richtext import PMRichTextFieldWidget
from z3c.form.browser.radio import RadioFieldWidget
from zope import schema
from zope.component import getAdapter
from zope.i18n import translate
from zope.interface import implements
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


class IMeetingAdvice(IDXMeetingContent):
    """
        MeetingAdvice schema
    """

    advice_group = LocalRoleField(
        title=_(u'title_advice_group'),
        description=_(u"Choose a group."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_group_vocabulary',
        required=True,
    )
    advice_type = schema.Choice(
        title=_(u'title_advice_type'),
        description=_(u"Choose an advice type."),
        vocabulary=u'Products.PloneMeeting.content.advice.advice_type_vocabulary',
        required=True,
    )
    form.widget('advice_hide_during_redaction', RadioFieldWidget)
    advice_hide_during_redaction = schema.Bool(
        title=_(u'title_advice_hide_during_redaction'),
        description=_("If you do not want the advice to be shown immediately after redaction, you can check this "
                      "box.  This will let you or other member of your group work on the advice before showing it.  "
                      "Note that if you lose access to the advice (for example if the item state evolve), "
                      "the advice will be considered 'Not given, was under edition'.  A manager will be able "
                      "to publish it nevertheless."),
        required=False,
    )
    form.widget('advice_comment', PMRichTextFieldWidget)
    advice_comment = RichText(
        title=_(u"title_advice_comment"),
        description=_("Enter the official comment."),
        required=False,
        allowed_mime_types=(u"text/html", )
    )
    form.widget('advice_observations', PMRichTextFieldWidget)
    advice_observations = RichText(
        title=_(u"title_advice_observations"),
        description=_("Enter optionnal observations if necessary."),
        required=False,
        allowed_mime_types=(u"text/html", )
    )
    advice_reference = schema.TextLine(
        title=_(u"title_advice_reference"),
        description=_("Enter a reference for this advice if necessary."),
        required=False,
    )
    form.mode(advice_row_id='hidden')
    advice_row_id = schema.TextLine(
        title=_(u"title_advice_row_id"),
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
    hidden = cfg and published.ti.id in cfg.getDefaultAdviceHiddenDuringRedaction() or False
    if hidden:
        api.portal.show_message(_("advice_hide_during_redaction_set_auto_to_true"),
                                request=data.context.REQUEST)
    return hidden


class MeetingAdvice(Container):
    """ """

    implements(IMeetingAdvice)
    # avoid inherited roles from the item or the item editor may edit the advice...
    __ac_local_roles_block__ = True

    security = ClassSecurityInfo()

    def getPrettyLink(self, **kwargs):
        """Return the IPrettyLink version of the title."""
        adapted = IPrettyLink(self)
        adapted.showContentIcon = True
        for k, v in kwargs.items():
            setattr(adapted, k, v)
        return adapted.getLink()

    def Title(self):
        '''
          This will construct the title of the advice, moreover, it checks for access
          to a confidential advice.
        '''
        # check that current user is not accessing to an advice that is confidential
        # to him but for which he knows the url to access to...
        parent = self.getParentNode()
        # in some case with plone.restapi summary serialize,
        # the parent is not found because self does not have acquisition
        if not parent:
            return ""
        if self.advice_group in parent.adviceIndex and parent.adviceIndex[self.advice_group]['isConfidential']:
            tool = api.portal.get_tool('portal_plonemeeting')
            cfg = tool.getMeetingConfig(self)
            is_confidential_power_observer = tool.isPowerObserverForCfg(
                cfg, cfg.getAdviceConfidentialFor())
            if not parent._adviceIsViewableForCurrentUser(
               cfg, is_confidential_power_observer, parent.adviceIndex[self.advice_group]):
                raise Unauthorized

        # we can not return a translated msg using _ so translate it
        return translate("Advice given on item ${item_title}",
                         mapping={'item_title': '"%s"' % unicode(parent.Title(), 'utf-8')},
                         domain="PloneMeeting",
                         default='Advice given on item "%s"' % parent.Title(),
                         context=self.REQUEST)

    def title_or_id(self):
        """ """
        return self.Title()

    def query_state(self):
        '''In what state am I ?'''
        wfTool = api.portal.get_tool('portal_workflow')
        return wfTool.getInfoFor(self, 'review_state')

    security.declarePublic('wfConditions')

    def wfConditions(self):
        '''Returns the adapter that implements the interface that proposes
           methods for use as conditions in the workflow associated with this
           item.'''
        return getWorkflowAdapter(self, conditions=True)

    security.declarePublic('wfActions')

    def wfActions(self):
        '''Returns the adapter that implements the interface that proposes
           methods for use as actions in the workflow associated with this
           item.'''
        return getWorkflowAdapter(self, conditions=False)

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

    def get_advice_given_on(self):
        '''Return the date the advice was given on.
           Returns the smallest date between modified() and last event 'giveAdvice'.
           This manages case when advice is edited after it is given, for example
           when a MeetingManager corrects a typo, the advice_given_on date will be
           the 'giveAdvice' date.'''
        lastEvent = getLastWFAction(self, 'giveAdvice')
        modified = self.modified()
        if not lastEvent:
            return modified
        else:
            return min(lastEvent['time'], modified)

    def historize_if_relevant(self, comment):
        """Historize if self was never historized or
           if it was modified since last version."""
        # only historize advice if it was modified since last historization
        # and if it is not 'asked_again', indeed we do not historize an advice
        # that is 'asked_again' of it's predecessor would be an advice 'asked_again' too...
        if self.advice_type != 'asked_again' and isModifiedSinceLastVersion(self):
            historize_object_data(self, comment=comment)

    # def attribute_is_used_cachekey(method, self, name):
    #     '''cachekey method for self.attribute_is_used.'''
    #     return "{0}.{1}".format(self.portal_type, name)

    security.declarePublic('attribute_is_used')

    #  @ram.cache(attribute_is_used_cachekey)
    def attribute_is_used(self, name):
        '''Necessary for utils._addManagedPermissions for advice for now
           any attribute is used ?'''
        return True

    def getIndexesRelatedTo(self, related_to='annex', check_deferred=True):
        '''See doc in interfaces.py.'''
        idxs = ['SearchableText']
        return idxs

    security.declarePublic('adapted')

    def adapted(self):
        '''Make adapted method available on advice, but actually no adapter
           can be defined, just return self.'''
        return self

    def get_previous_advice_type(self):
        """ """
        adapter = getAdapter(self, IImioHistory, 'advice_given')
        last_event = getLastAction(adapter)
        prev_advice_type = None
        if last_event:
            prev_advice_type = get_event_field_data(
                last_event["advice_data"], "advice_type")
        return prev_advice_type


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
        advicePortalTypeIds = tool.getAdvicePortalTypeIds()

        # take into account groups for wich user can add an advice
        # while adding an advice, the context is his parent, aka a MeetingItem
        alterable_advice_org_uids = []
        if context.meta_type == 'MeetingItem':
            alterable_advice_org_uids = context.getAdvicesGroupsInfosForUser(compute_to_edit=False)[0]
        # take into account groups for which user can edit an advice
        elif context.portal_type in advicePortalTypeIds:
            alterable_advice_org_uids = context.getAdvicesGroupsInfosForUser(compute_to_add=False)[1]
            # make sure advice_group selected on advice is in the vocabulary
            if context.advice_group not in alterable_advice_org_uids:
                alterable_advice_org_uids.append(context.advice_group)

        # manage case where we have several meetingadvice portal_types
        # depending on current portal_type, clean up selectable orgs
        itemObj = context.meta_type == 'MeetingItem' and context or context.getParentNode()
        current_portal_type = findMeetingAdvicePortalType(context)
        alterable_advice_org_uids = [
            org_uid for org_uid in alterable_advice_org_uids
            if (itemObj.adapted()._advicePortalTypeForAdviser(org_uid) == current_portal_type or
                (context.portal_type in advicePortalTypeIds and org_uid == context.advice_group))]

        # create vocabulary
        for alterable_advice_org_uid in alterable_advice_org_uids:
            org = get_organization(alterable_advice_org_uid)
            terms.append(SimpleTerm(alterable_advice_org_uid,
                                    alterable_advice_org_uid,
                                    org.get_full_title()))
        return SimpleVocabulary(terms)


class AdviceTypeVocabulary(object):
    implements(IVocabularyFactory)

    def __call__(self, context):
        """ """
        terms = []
        tool = api.portal.get_tool('portal_plonemeeting')
        cfg = tool.getMeetingConfig(context)
        advicePortalTypeIds = tool.getAdvicePortalTypeIds()

        # manage when portal_type accessed from the Dexterity types configuration
        if cfg:
            usedAdviceTypes = list(cfg.getUsedAdviceTypes())

            # now wipeout usedAdviceTypes depending on current meetingadvice portal_type
            itemObj = context.meta_type == 'MeetingItem' and context or context.getParentNode()
            current_portal_type = findMeetingAdvicePortalType(context)
            usedAdviceTypes = [
                usedAdviceType for usedAdviceType in usedAdviceTypes
                if usedAdviceType in itemObj.adapted()._adviceTypesForAdviser(current_portal_type)]

            # make sure if an adviceType was used for context and it is no more available, it
            # appears in the vocabulary and is so useable...
            if context.portal_type in advicePortalTypeIds and \
               context.advice_type not in usedAdviceTypes:
                usedAdviceTypes.append(context.advice_type)
            for advice_id, advice_title in cfg.listAdviceTypes(include_asked_again=True).items():
                if advice_id in usedAdviceTypes:
                    terms.append(SimpleTerm(advice_id, advice_id, advice_title))
        return SimpleVocabulary(terms)
