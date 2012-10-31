## Python Script "removeGivenObject.py"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=obj
##title=Deletes an object

parent = obj.aq_inner.aq_parent
parent.manage_delObjects([obj.getId(),])
