from plone.app.layout.viewlets.content import ContentHistoryView, DocumentBylineViewlet
from plone.app.layout.viewlets.common import GlobalSectionsViewlet

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.CMFCore.utils import getToolByName

class PloneMeetingContentHistoryView(ContentHistoryView):
    '''
      Overrides the ContentHistoryView template to use our own.
      We want to display the content_history as a table.
    '''

    index = ViewPageTemplateFile("templates/content_history.pt")

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
                    return {'portal': action['id'],}
            #XXX end of change by PM

        # Sort by path length, the longest matching path wins
        valid_actions.sort()
        if valid_actions:
            return {'portal' : valid_actions[-1][1]}

        return {'portal' : default_tab}

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
            if currentLayout in ['meetingfolder_redirect_view',]:
                return False
        return True