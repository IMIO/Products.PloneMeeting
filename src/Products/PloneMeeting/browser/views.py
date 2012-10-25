from plone.app.layout.viewlets.content import ContentHistoryView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

class PloneMeetingContentHistoryView(ContentHistoryView):

    index = ViewPageTemplateFile("templates/content_history.pt")
