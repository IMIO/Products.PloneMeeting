## Python Script "getTopicsFolder.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=fieldName, fieldRealName, at_url
##title=Redirects the reference browser popup to the correct folder containing the relevant Topic objets
##

rq = context.REQUEST
mConfig = context.restrictedTraverse(rq.get('at_url'))
redirectUrl = '%s/referencebrowser_popup?%s' % \
    (mConfig.absolute_url() + '/topics', rq.get('QUERY_STRING'))
rq.RESPONSE.redirect(redirectUrl)