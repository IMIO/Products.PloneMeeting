# -*- coding: utf-8 -*-

from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.interfaces import IRedirect
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from zope import schema
from zope.interface import Interface


class ILinkWithVision(Interface):

    projects = schema.List(
        title=u"Projects",
        description=u"",
        required=True,
        value_type=schema.Choice(
          vocabulary=u'Products.PloneMeeting.external.vocabularies.visionprojects'),
    )


class LinkWithVisionForm(form.Form):

    fields = field.Fields(ILinkWithVision)
    fields['projects'].widgetFactory = CheckBoxFieldWidget

    ignoreContext = True  # don't use context to get widget data

    label = _(u"Link with iA.Vision")
    description = u''
    _finishedSent = False

    def update(self):
        """ """
        super(LinkWithVisionForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    @button.buttonAndHandler(_('Link'), name='link_with_vision')
    def handleLinkWithVision(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        self.projects = self.request.form.get('form.widgets.projects')
        # do link with iA.Vision
        self._doLinkWithVision()

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self._finishedSent = True

    def render(self):
        if self._finishedSent:
            IRedirect(self.request).redirect(self.context.absolute_url())
            return ""
        return super(LinkWithVisionForm, self).render()

    def _doLinkWithVision(self):
        """ """
        pass
