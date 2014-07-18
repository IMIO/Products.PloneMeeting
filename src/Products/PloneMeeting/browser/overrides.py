from plone.app.controlpanel.overview import OverviewControlPanel
from plone.app.layout.viewlets.content import ContentHistoryView, DocumentBylineViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.memoize.view import memoize
from plone.memoize.view import memoize_contextless

from imio.actionspanel.browser.views import ActionsPanelView
from imio.actionspanel.browser.views import DeleteGivenUidView

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName
from Products.CMFCore.permissions import ModifyPortalContent
from Products.PloneMeeting.utils import getCurrentMeetingObject


class PloneMeetingContentHistoryView(ContentHistoryView):
    '''
      Overrides the ContentHistoryView template to use our own.
      We want to display the content_history as a table.
    '''
    index = ViewPageTemplateFile("templates/content_history.pt")

    def getTransitionTitle(self, transitionName):
        """
          Given a p_transitionName, return the defined title in portal_workflow
          as it is what is really displayed in the template.
        """
        currentWF = self._getCurrentContextWorkflow()
        if hasattr(currentWF.transitions, transitionName):
            return currentWF.transitions[transitionName].title
        else:
            return transitionName

    @memoize
    def _getCurrentContextWorkflow(self):
        """
          Return currently used workflow.
        """
        wfTool = getToolByName(self.context, 'portal_workflow')
        return wfTool.getWorkflowsFor(self.context)[0]


class PloneMeetingGlobalSectionsViewlet(GlobalSectionsViewlet):
    '''
      Overrides the selectedTabs method so the right MeetingConfig tab
      is selected when a user is on the item of another user
      (in this case, the url of the tab does not correspond to the current url).
      See #4856
    '''

    def selectedTabs(self, default_tab='index_html', portal_tabs=()):
        plone_url = getToolByName(self.context, 'portal_url')()
        plone_url_len = len(plone_url)
        request = self.request
        valid_actions = []

        url = request['URL']
        path = url[plone_url_len:]

        #XXX change by PM
        mc = self.context.portal_plonemeeting.getMeetingConfig(self.context)
        #XXX end of change by PM

        for action in portal_tabs:
            if not action['url'].startswith(plone_url):
                # In this case the action url is an external link. Then, we
                # avoid issues (bad portal_tab selection) continuing with next
                # action.
                continue
            action_path = action['url'][plone_url_len:]
            if not action_path.startswith('/'):
                action_path = '/' + action_path
            if path.startswith(action_path + '/'):
                # Make a list of the action ids, along with the path length
                # for choosing the longest (most relevant) path.
                valid_actions.append((len(action_path), action['id']))

            #XXX change by PM
            if mc:
                if "/mymeetings/%s" % mc.getId() in action_path:
                    return {'portal': action['id'], }
            #XXX end of change by PM

        # Sort by path length, the longest matching path wins
        valid_actions.sort()
        if valid_actions:
            return {'portal': valid_actions[-1][1]}

        return {'portal': default_tab}


class PloneMeetingDocumentBylineViewlet(DocumentBylineViewlet):
    '''
      Overrides the DocumentBylineViewlet to hide it for some layouts.
    '''

    index = ViewPageTemplateFile("templates/document_byline.pt")

    def show(self):
        oldShow = super(PloneMeetingDocumentBylineViewlet, self).show()
        if not oldShow:
            return False
        else:
            # add our own conditions
            # the documentByLine should be hidden on some layouts
            currentLayout = self.context.getLayout()
            if currentLayout in ['meetingfolder_redirect_view', ]:
                return False
        return True

    def show_history(self):
        """
          Originally, the history is shown to people having the
          'CMFEditions: Access previous versions' permission, here
          we want everybody than can acces the item to see the history...
        """
        # show the history on the meetingadvice only on the advanced management view
        if self.context.portal_type == 'meetingadvice' and 'ajax_load' in self.request:
            return False
        return True

    def highlight_history_link(self):
        """
          If a comment was added to last event of the object history,
          we highlight the link (set a css class on it) so user eye is drawn to it.
        """
        # use method historyLastEventHasComments from imio.actionspanel that does the job
        actions_panel = self.context.restrictedTraverse('@@actions_panel')
        return actions_panel.historyLastEventHasComments()


class PloneMeetingOverviewControlPanel(OverviewControlPanel):
    '''
      Override the Overview control panel to add informations about
      PloneMeeting version at the bottom of @@overview-controlpanel.
    '''
    def version_overview(self):
        versions = super(PloneMeetingOverviewControlPanel, self).version_overview()
        pm_version = self.context.portal_setup.getProfileInfo('profile-Products.PloneMeeting:default')['version']
        versions.insert(0, 'PloneMeeting %s' % pm_version)
        return versions


class BaseActionsPanelView(ActionsPanelView):
    """
      Base mechanism for managing displayed actions.
      As we display several elements in dashboards (list of items for example),
      we memoize_contextless some methods that will always return the same result to
      avoid recomputing them uselessly.
    """
    def __init__(self, context, request):
        super(BaseActionsPanelView, self).__init__(context, request)
        self.IGNORABLE_ACTIONS = ('copy', 'cut', 'paste')
        self.IGNORABLE_HISTORY_COMMENTS = self.IGNORABLE_HISTORY_COMMENTS + \
            ('create_meeting_item_from_template_comments',
             'create_from_predecessor_comments',
             'Duplicate and keep link_comments',
             'Duplicate_comments')

    def mayEdit(self):
        """
          We override mayEdit to avoid the icon to be displayed for MeetingFiles.
        """
        return self.member.has_permission(ModifyPortalContent, self.context) and \
            self.useIcons and not \
            self.context.meta_type == 'MeetingFile'

    @memoize_contextless
    def _transitionsToConfirm(self):
        """
          Return the list of transitions the user will have to confirm, aka
          the user will be able to enter a comment for.
          This is relevant for Meeting and MeetingItem.
        """
        toConfirm = []
        tool = getToolByName(self, 'portal_plonemeeting')
        cfg = tool.getMeetingConfig(self.context)
        if cfg:
            toConfirm = cfg.getTransitionsToConfirm()
        return toConfirm

    def _redirectToViewableUrl(self):
        """
          Return the url the user must be redirected to.
          This is relevant for Meeting and MeetingItem.
        """
        http_referer = self.request['HTTP_REFERER']
        if http_referer.startswith(self.context.absolute_url()):
            # we were on the item, redirect to user home page
            mc = self.context.portal_plonemeeting.getMeetingConfig(self.context)
            app = self.context.portal_plonemeeting.getPloneMeetingFolder(mc.id)
            redirectToUrl = app.restrictedTraverse('@@meetingfolder_redirect_view').getFolderRedirectUrl()
        else:
            redirectToUrl = http_referer
        return redirectToUrl

    @memoize_contextless
    def _goToReferer(self):
        """
          Override _goToReferer to take some specific PloneMeeting case into account.
        """
        tool = getToolByName(self.context, 'portal_plonemeeting')
        return tool.goToReferer()


class MeetingItemActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on an item.
    """
    def __init__(self, context, request):
        super(MeetingItemActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ('renderTransitions',
                                   'renderArrows',
                                   'renderOwnDelete',
                                   'renderEdit',
                                   'renderActions',
                                   'renderHistory', )

    def renderArrows(self):
        """
        """
        showArrows = self.kwargs.get('showArrows', False)
        if showArrows and self.mayChangeOrder():
            self.totalNbOfItems = self.kwargs['totalNbOfItems']
            return ViewPageTemplateFile("templates/actions_panel_arrows.pt")(self)
        return ''

    def showHistoryForContext(self):
        """
          History on items is shown without condition.
        """
        return True

    @memoize_contextless
    def mayChangeOrder(self):
        """
          Check if current user can change elements order in case arrows are shown.
        """
        meeting = getCurrentMeetingObject(self.context)
        return meeting.wfConditions().mayChangeItemsOrder()


class MeetingActionsPanelView(BaseActionsPanelView):
    """
      Specific actions displayed on a meeting.
    """
    def __init__(self, context, request):
        super(MeetingActionsPanelView, self).__init__(context, request)
        self.SECTIONS_TO_RENDER = ['renderTransitions',
                                   'renderOwnDelete',
                                   'renderDeleteWholeMeeting',
                                   'renderEdit',
                                   'renderActions', ]

    def renderDeleteWholeMeeting(self):
        """
          Special action on the meeting available to Managers that let delete
          a whole meeting with linked items.
        """
        if self.member.has_role('Manager'):
            return ViewPageTemplateFile("templates/actions_panel_deletewholemeeting.pt")(self)


# to be removed in Products.Archetypes 1.9.5+...
# we override it with current Github master as some translations does not work anymore???
from zope.interface import implements
from Products.Five import BrowserView
from Products.Archetypes.interfaces.utils import IUtils
from zope.i18n import translate


class Utils(BrowserView):
    implements(IUtils)

    def translate(self, vocab, value, widget=None):
        """Translate an input value from a vocabulary.

        - vocab is a vocabulary, for example a DisplayList or IntDisplayList

        - 'value' is meant as 'input value' and should have been
          called 'key', really, because we will lookup this key in the
          vocabulary, which should give us a value as answer.  When no
          such value is known, we take the original input value.  This
          gets translated.

        - By passing a widget with a i18n_domain attribute, we use
          that as the translation domain.  The default is 'plone'.

        Supported input values are at least: string, integer, list and
        tuple.  When there are multiple values, we iterate over them.
        """
        domain = 'plone'
        # Make sure value is an iterable.  There are really too many
        # iterable and non-iterable types (and half-iterable like
        # strings, which we definitely do not want to iterate over) so
        # we check the __iter__ attribute:
        if not hasattr(value, '__iter__'):
            value = [value]
        if widget:
            custom_domain = getattr(widget, 'i18n_domain', None)
            if custom_domain:
                domain = custom_domain

        def _(value):
            return translate(value,
                             domain=domain,
                             context=self.request)
        nvalues = []
        for v in value:
            if not v:
                continue
            original = v
            if isinstance(v, unicode):
                v = v.encode('utf-8')
            # Get the value with key v from the vocabulary,
            # falling back to the original input value.
            vocab_value = vocab.getValue(v, original)
            if not isinstance(vocab_value, basestring):
                # May be an integer.
                vocab_value = str(vocab_value)
            elif not isinstance(vocab_value, unicode):
                # avoid UnicodeDecodeError if value contains special chars
                vocab_value = unicode(vocab_value, 'utf-8')
            # translate explicitly
            vocab_value = _(vocab_value)
            nvalues.append(vocab_value)
        value = ', '.join(nvalues)
        return value


class PMDeleteGivenUidView(DeleteGivenUidView):
    '''Redefine the _computeBackURL.'''

    def _computeBackURL(self):
        '''Compute exact back url because as the parent as a view that does
           a redirection also, we loose portal_messages...  So here, we compute the
           url the view of the parent would redirect to...
        '''
        mc = self.context.portal_plonemeeting.getMeetingConfig(self.context)
        # if we are outside PloneMeeting, then use default DeleteGivenUidView behaviour
        if not mc:
            return super(PMDeleteGivenUidView, self)._computeBackURL()
        app = self.context.portal_plonemeeting.getPloneMeetingFolder(mc.id)
        return app.restrictedTraverse('@@meetingfolder_redirect_view').getFolderRedirectUrl()
