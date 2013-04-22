## Script (Python) "listFolderButtonsActions"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=

#list the acceptable folder_buttons actions
#this is used in the meetingfolder_view
#we have our own paste and delete
ignorableActions = ['cut', 'paste', 'copy', 'rename', 'delete', ]

mConfig = context.portal_plonemeeting.getMeetingConfig(context)
if not mConfig:
    return []

allActions = context.portal_actions.listFilteredActionsFor(context)

folderButtonsActions = []
if allActions.has_key('folder_buttons'):
    folderButtonsActions = allActions['folder_buttons']

if allActions.has_key('folder_buttons_plonemeeting'):
    folderButtonsActions = folderButtonsActions + \
                           allActions['folder_buttons_plonemeeting']
res = []

for action in folderButtonsActions:
    # remove ignorable actions
    if not (action['id'] in ignorableActions):
        res.append(action)
return res
