## Python Script "getCategoriesFolder.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=fieldName, fieldRealName, at_url
##title=Redirects the reference browser popup to the correct folder containing the relevant MeetingCategory objets
##

rq = context.REQUEST
item = context.restrictedTraverse(rq.get('at_url'))
meetingConfig = item.portal_plonemeeting.getMeetingConfig(item)
redirectUrl = '%s/referencebrowser_popup?%s' % \
    (meetingConfig.classifiers.absolute_url(), rq.get('QUERY_STRING'))
rq.RESPONSE.redirect(redirectUrl)
