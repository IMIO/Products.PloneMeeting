from zope.i18n import translate
from zope.publisher.browser import BrowserView


TEMPLATE = """\
var plonemeeting_delete_meeting_confirm_message = "%(plonemeeting_delete_meeting_confirm_message)s";
var sure_to_remove_selected_items = "%(sure_to_remove_selected_items)s";
var sure_to_present_selected_items = "%(sure_to_present_selected_items)s";
var sure_to_cancel_edit = "%(sure_to_cancel_edit)s";
var are_you_sure = "%(are_you_sure)s";
var sure_to_take_over = "%(sure_to_take_over)s";
var wait_msg = "%(wait_msg)s";
var reinit_delay_confirm_message = "%(reinit_delay_confirm_message)s";
"""


class JSVariables(BrowserView):

    def __call__(self, *args, **kwargs):
        response = self.request.response
        response.setHeader('content-type', 'text/javascript;;charset=utf-8')

        plonemeeting_delete_meeting_confirm_message = translate('plonemeeting_delete_meeting_confirm_message',
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
        sure_to_take_over = translate('sure_to_take_over',
                                      domain='PloneMeeting',
                                      context=self.request)
        wait_msg = translate('wait_msg',
                             domain='PloneMeeting',
                             context=self.request)
        reinit_delay_confirm_message = translate('reinit_delay_confirm_message',
                                                 domain='PloneMeeting',
                                                 context=self.request)

        return TEMPLATE % dict(
            plonemeeting_delete_meeting_confirm_message=plonemeeting_delete_meeting_confirm_message,
            sure_to_remove_selected_items=sure_to_remove_selected_items,
            sure_to_present_selected_items=sure_to_present_selected_items,
            sure_to_cancel_edit=sure_to_cancel_edit,
            are_you_sure=are_you_sure,
            sure_to_take_over=sure_to_take_over,
            wait_msg=wait_msg,
            reinit_delay_confirm_message=reinit_delay_confirm_message,
        )
