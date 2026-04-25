# -*- coding: utf-8 -*-

from plone import api
from plone.dexterity.browser.view import DefaultView
from Products.PloneMeeting.config import TOOL_FOLDER_POD_TEMPLATES


PANE_NAMES = (
    'default',
    'data',
    'assembly_and_signatures',
    'workflow',
    'gui',
    'mail',
    'advices',
    'committees',
    'votes',
    'doc',
)


class MeetingConfigView(DefaultView):
    """Default DX view for MeetingConfig — tabbed pane layout.

    Replaces the legacy AT skin-layer template
    skins/plonemeeting_templates/meetingconfig_view.pt.
    """

    pane_names = PANE_NAMES

    def updateFieldsFromSchemata(self):
        super(MeetingConfigView, self).updateFieldsFromSchemata()
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.context
        self.is_manager = self.tool.isManager(self.cfg)
        self.is_real_manager = self.tool.isManager(realManagers=True)
        self.page_name = self.request.get('pageName') or 'default'

    def default_pane_widgets(self):
        """Widgets declared on the schema with no fieldset."""
        return [widget for widget in self.widgets.values() if widget.mode != 'hidden']

    def group_widgets(self, pane_name):
        """Widgets for a named fieldset, in schema order."""
        for group in self.groups:
            if group.__name__ == pane_name:
                return [widget for widget in group.widgets.values() if widget.mode != 'hidden']
        return []

    def widget(self, name):
        """Look up a widget by unqualified field name."""
        key = 'form.widgets.' + name
        if key in self.w:
            return self.w[key]
        return None

    @property
    def podtemplates_folder(self):
        return getattr(self.cfg, TOOL_FOLDER_POD_TEMPLATES, None)

    def style_templates(self):
        folder = self.podtemplates_folder
        if folder is None:
            return []
        return folder.getFolderContents(
            contentFilter={'portal_type': ('StyleTemplate',)},
            full_objects=True,
        )

    def document_templates(self):
        folder = self.podtemplates_folder
        if folder is None:
            return []
        return folder.getFolderContents(
            contentFilter={'portal_type': ('ConfigurablePODTemplate', 'DashboardPODTemplate')},
            full_objects=True,
        )

    def show_details(self):
        return bool(self.request.get('show_details'))

    def show_annexes_types(self):
        return bool(self.request.get('show_annexes_types'))

    def wf_id(self, kind):
        """Return 'cfg-id__wf-id' for 'item' or 'meeting'."""
        if kind == 'item':
            workflow_id = self.cfg.getItemWorkflow()
        else:
            workflow_id = self.cfg.getMeetingWorkflow()
        return '{0}__{1}'.format(self.cfg.getId(), workflow_id)
