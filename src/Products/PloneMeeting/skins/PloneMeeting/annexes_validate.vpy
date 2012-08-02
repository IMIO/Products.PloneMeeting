## Validator Python Script "annexes_validate.vpy"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=annex_type, annex_title, annex_file
##title=Validates a form for uploading an annex
##
from Products.CMFPlone import MessageFactory as _

if not annex_type.strip():
    state.setError('annexType', _('PloneMeeting')('type_required', default='Please specify an annex type.'))

if not annex_title.strip():
    state.setError('annexTitle', _('PloneMeeting')('title_required', default='Please specify a title.'))

if not annex_file:
    state.setError('annexFile', _('PloneMeeting')('file_required', default='Please select a file.'))

if state.getErrors():
    return state.set(status='failure', portal_status_message='Please correct the indicated errors.')
else:
    return state
