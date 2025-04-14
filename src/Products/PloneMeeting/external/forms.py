# -*- coding: utf-8 -*-

from plone import api
from Products.PloneMeeting.config import PMMessageFactory as _
from Products.PloneMeeting.external.config import API_DELIB_UID
from Products.PloneMeeting.external.utils import send_json_request
from Products.PloneMeeting.interfaces import IRedirect
from Products.PloneMeeting.widgets.pm_checkbox import PMCheckBoxFieldWidget
from z3c.form import button
from z3c.form import field
from z3c.form import form
from zope import schema
from zope.interface import Interface

import json


def projects_default():
    """ """
    content = send_json_request(
        "delib-links", extra_parameters={"delib_uid": API_DELIB_UID})
    return [elt['target']['id'] for elt in content
            if elt['target']['type'] == "project"]


def tasks_default():
    """ """
    content = send_json_request(
        "delib-links", extra_parameters={"delib_uid": API_DELIB_UID})
    return [elt['target']['id'] for elt in content
            if elt['target']['type'] == "task"]


class ILinkWithVision(Interface):

    projects = schema.List(
        title=_(u"Projects"),
        description=u"",
        required=True,
        defaultFactory=projects_default,
        value_type=schema.Choice(
          vocabulary=u'Products.PloneMeeting.external.vocabularies.visionprojects'),
    )

    tasks = schema.List(
        title=_(u"Tasks"),
        description=u"",
        required=True,
        defaultFactory=tasks_default,
        value_type=schema.Choice(
          vocabulary=u'Products.PloneMeeting.external.vocabularies.visiontasks'),
    )


class LinkWithVisionForm(form.Form):

    fields = field.Fields(ILinkWithVision)
    fields['projects'].widgetFactory = PMCheckBoxFieldWidget
    fields['tasks'].widgetFactory = PMCheckBoxFieldWidget

    ignoreContext = True  # don't use context to get widget data

    label = _(u"Link with iA.Vision")
    description = _(u"Elements displayed are only elements you can access in iA.Vision.")
    _finished_sent = False

    def update(self):
        """ """
        super(LinkWithVisionForm, self).update()
        # after calling parent's update, self.actions are available
        self.actions.get('cancel').addClass('standalone')

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handle_apply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        # do link/unlink with iA.Vision
        self._do_link_unlink(data)

    @button.buttonAndHandler(_('Cancel'), name='cancel')
    def handle_cancel(self, action):
        self._finished_sent = True

    def render(self):
        if self._finished_sent:
            IRedirect(self.request).redirect(
                self.context.absolute_url() +
                "?expand-collapsible=external-infos")
            return ""
        return super(LinkWithVisionForm, self).render()

    def _do_link_unlink(self, data):
        """ """
        # get linked items and link new elements and unlink no more selected ones
        linked_content = send_json_request(
            "delib-links", extra_parameters={"delib_uid": API_DELIB_UID})
        linked_projects = [elt['target']['id'] for elt in linked_content
                           if elt['target']['type'] == "project"]
        linked_tasks = [elt['target']['id'] for elt in linked_content
                        if elt['target']['type'] == "task"]
        # link new selected elements
        for project_id in data['projects']:
            if project_id not in linked_projects:
                body = {"delib_uid": API_DELIB_UID,
                        "target": {"type": "project",
                                   "object_id": project_id}}
                res = send_json_request("delib-links", method='POST', body=json.dumps(body))
                api.portal.show_message(
                    _('Element "${element}" has been linked.',
                      mapping={'element': res[0]['target']['name']}),
                    request=self.request)
        for task_id in data['tasks']:
            if task_id not in linked_tasks:
                body = {"delib_uid": API_DELIB_UID,
                        "target": {"type": "task",
                                   "object_id": task_id}}
                res = send_json_request("delib-links", method='POST', body=json.dumps(body))
                api.portal.show_message(
                    _('Element "${element}" has been linked.',
                      mapping={'element': res[0]['target']['name']}),
                    request=self.request)
        # unlink no more selected elements
        for linked_elt in linked_content:
            if (linked_elt['target']['type'] == "project" and
                linked_elt['target']['id'] not in data['projects']) or \
               (linked_elt['target']['type'] == "task" and
                    linked_elt['target']['id'] not in data['tasks']):
                res = send_json_request("delib-links/%s" % linked_elt['id'], method='DELETE')
                api.portal.show_message(
                    _('Element "${element}" has been unlinked.',
                      mapping={'element': linked_elt['target']['name']}),
                    request=self.request,
                    type='warning')
        self._finished_sent = True
