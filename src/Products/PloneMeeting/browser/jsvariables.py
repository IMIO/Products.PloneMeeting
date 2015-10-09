from zope.publisher.browser import BrowserView
from zope.i18n import translate

TEMPLATE = """\
var plonemeeting_delete_meeting_confirm_message = "%(plonemeeting_delete_meeting_confirm_message)s";
var no_selected_items = "%(no_selected_items)s";
var sure_to_remove_selected_items = "%(sure_to_remove_selected_items)s";
var sure_to_present_selected_items = "%(sure_to_present_selected_items)s";
var sure_to_cancel_edit = "%(sure_to_cancel_edit)s";
var are_you_sure = "%(are_you_sure)s";
"""


class JSVariables(BrowserView):

    def __call__(self, *args, **kwargs):
        response = self.request.response
        response.setHeader('content-type', 'text/javascript;;charset=utf-8')

        plonemeeting_delete_meeting_confirm_message = translate('plonemeeting_delete_meeting_confirm_message',
                                                                domain='PloneMeeting',
                                                                context=self.request)
        no_selected_items = translate('no_selected_items',
                                      domain='PloneMeeting',
                                      context=self.request)
        sure_to_remove_selected_items = translate('sure_to_remove_selected_items',
                                                  domain='PloneMeeting',
                                                  context=self.request)
        sure_to_present_selected_items = translate('sure_to_present_selected_items',
                                                   domain='PloneMeeting',
                                                   context=self.request)
        sure_to_cancel_edit = translate('sure_to_cancel_edit',
                                        domain='PloneMeeting',
                                        context=self.request)
        are_you_sure = translate('are_you_sure',
                                 domain='PloneMeeting',
                                 context=self.request)

        return TEMPLATE % dict(
            plonemeeting_delete_meeting_confirm_message=plonemeeting_delete_meeting_confirm_message,
            no_selected_items=no_selected_items,
            sure_to_remove_selected_items=sure_to_remove_selected_items,
            sure_to_present_selected_items=sure_to_present_selected_items,
            sure_to_cancel_edit=sure_to_cancel_edit,
            are_you_sure=are_you_sure,
        )
