## Script (Python) "create_meetingconfig_folder"
##title=Calls the portal_plonemeeting.createMeetingConfigFolder()
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=meetingConfigId, userId

from Products.CMFCore.utils import getToolByName

portal = getToolByName(container, 'portal_url').getPortalObject()
portal.portal_plonemeeting.createMeetingConfigFolder(meetingConfigId, userId)
