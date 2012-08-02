## Python Script "object_goto.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=objectId,idType
##title=Goto the view page for the object whose id is given in p_objectId

# Get the object to go to
if idType == 'uid':
    # Search the object in the uid catalog
    obj = context.uid_catalog(UID=objectId)[0].getObject()
elif idType == 'number':
    # The object is an item whose number is given in objectId
    meeting = context.uid_catalog(UID=context.REQUEST.get('meetingUid'))[0].getObject()
    obj = meeting.getItemByNumber(int(objectId))
objectUrl = obj.absolute_url()
return context.REQUEST.RESPONSE.redirect(objectUrl)
