## Python Script "meeting_folder_view"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=app
##title=Redirect to the correct default application view
##
tool = context.portal_plonemeeting
default_view = tool.getMeetingConfig(app).getUserParam('meetingAppDefaultView')

if default_view.startswith('folder_'):
    #a folder view will be used
    #as this kind of view is identified adding a 'folder_' at the beginning, we retrieve the
    #real view method removing the first 7 characters
    return (app.absolute_url() + '/%s') % default_view[7:]
else:
    #a topic has been selected in the meetingConfig as the default view
    #as this kind of view is identified adding a 'topic_' at the beginning, we retrieve the
    #real view method removing the first 6 characters
    return (app.absolute_url() + '/plonemeeting_topic_view?search=%s' % default_view[6:])
