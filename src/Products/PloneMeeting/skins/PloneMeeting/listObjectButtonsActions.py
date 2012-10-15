## Script (Python) "listObjectButtonsActions"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=object

ignorableActions = ()

if object.meta_type  in ['Meeting', 'MeetingItem']:
    ignorableActions = ('copy', 'cut', 'paste', 'delete')
allActions = context.portal_actions.listFilteredActionsFor(object)

objectButtonActions = []
if allActions.has_key('object_buttons'):
    objectButtonActions = allActions['object_buttons']

res = []
for action in objectButtonActions:
    if not (action['id'] in ignorableActions):
        act = [action['url']]
        # We try to append the url of the icon of the action
        # look on the action itself
        if action['icon']:
            act.append(action['icon'])
        else:
            # look for an icon in portal_actionicons, this is deprecated...
            try:
                act.append(context.portal_actionicons.getActionIcon(
                    action['category'], action['id']))
            except KeyError:
                # Append nothing if no icon found
                act.append('')
        act.append(action['title'])
        act.append(action['id'])
        res.append(act)
return res
