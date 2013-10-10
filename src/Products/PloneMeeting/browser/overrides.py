from plone.app.layout.viewlets.content import ContentHistoryView, DocumentBylineViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet
from plone.memoize.instance import memoize

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName


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
        return True


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
        if value:
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
