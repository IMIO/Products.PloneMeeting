from zope.component import getMultiAdapter
from plone.memoize.instance import memoize

from plone.app.layout.navigation.navtree import buildFolderTree
from plone.app.layout.navigation.navtree import NavtreeStrategyBase

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName


class ItemTemplateView(BrowserView):
    '''
      This manage the overlay popup displayed when a user want to select an item template to create a new item.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        self.portal = portal_state.portal()
        self.tool = self.getPloneMeetingTool()
        self.meetingConfig = self.getCurrentMeetingConfig()
        self.request.set('disable_border', 1)

    def __call__(self):
        # check that the user can actually create an item from a template
        if not self.getItemTemplates():
            self.request.RESPONSE.redirect(self.context.absolute_url())
        form = self.request.form
        templateUID = form.get('templateUID', None)
        cancelled = form.get('form.buttons.cancel', False)
        if templateUID:
            newItem = self.createItemFromTemplate(templateUID)
            if not newItem:
                self.request.RESPONSE.redirect(self.context.absolute_url())
            else:
                self.request.RESPONSE.redirect(newItem.absolute_url() + '/edit')
        elif cancelled:
            # the only way to enter here is the popup overlay not to be shown
            # because while using the popup overlay, the jQ function take care of hidding it
            # while the Cancel button is hit
            self.request.response.redirect(form.get('form.HTTP_REFERER'))
        else:
            # compute and store templates tree so it can be used in several places
            # this is not done in the __init__ because the user is "Anonymous" in the __init__
            # and as we filter on "templateUsingGroup", we need a valid user...
            self.templatesTree = self.getTemplatesTree()
            return self.index()

    def createItemFromTemplate(self, templateUID):
        '''The user wants to create an item from a item template that lies in
           this meeting configuration. Item id is in the request.'''
        catalog = getToolByName(self.context, 'portal_catalog')
        templateItem = catalog(UID=templateUID, isDefinedInTool=True)[0].getObject()
        # Create the new item by duplicating the template item
        membershipTool = getToolByName(self.context, 'portal_membership')
        member = membershipTool.getAuthenticatedMember()
        newItem = templateItem.clone(newOwnerId=member.id,
                                     cloneEventAction='create_meeting_item_from_template',
                                     destFolder=self.context)
        return newItem

    @memoize
    def getItemTemplates(self):
        '''Gets the list of template items from the config.'''
        cfg = self.getCurrentMeetingConfig()
        res = []
        if cfg:
            templates = cfg.getItems(recurring=False)
            if templates:
                #check if the current user can use the template
                tool = self.getPloneMeetingTool()
                membershipTool = getToolByName(self.portal, 'portal_membership')
                member = membershipTool.getAuthenticatedMember()
                memberGroups = tool.getGroupsForUser(member.getId(), suffix="creators")
                memberGroupIds = [group.id for group in memberGroups]
                for template in templates:
                    templateRestrictedGroups = template.getTemplateUsingGroups()
                    if not templateRestrictedGroups or \
                       set(memberGroupIds).intersection(templateRestrictedGroups):
                        res.append(template)
        return res

    @memoize
    def getPloneMeetingTool(self):
        '''Returns the tool.'''
        return getToolByName(self.portal, 'portal_plonemeeting')

    @memoize
    def getCurrentMeetingConfig(self):
        '''Returns the current meetingConfig.'''
        tool = self.tool
        res = tool.getMeetingConfig(self.context)
        return res

    def getTemplatesTree(self):
        '''Create the structure of elements used to display the item templates tree to the item creators.
           We only want to show folders and items the current creator may use, so we do that in 2 steps :
           - a first catalog query that will find every items the creator may use,
             when found, we save the differents paths to these items so we will be able to
             not take into account folder that could exist in the configuration but that would
             be empty because no items into it;
           - when the query is build with list of paths to consider, we use buildFolderTree
             that will build a 'tree' dict with elements and children.'''
        query = {}
        # first query the catalog to see wich items the current user may select
        itemTemplatesPath = '/'.join(self.getCurrentMeetingConfig().itemtemplates.getPhysicalPath())
        query['path'] = {'query': itemTemplatesPath}
        query['isDefinedInTool'] = True
        # templateUsingGroups, it is an index present on every elements (items and folders)
        # of the MeetingConfig.itemtemplates, items with none selected has '__nothing_selected__'
        # folders in the itemtemplates folder have '__folder_in_itemtemplates__' and items
        # with selected values have the id of the relevant MeetingGroups
        membershipTool = getToolByName(self.context, 'portal_membership')
        member = membershipTool.getAuthenticatedMember()
        memberGroups = [group.getId() for group in self.getPloneMeetingTool().getGroupsForUser(member.getId(), suffix="creators")]
        query['templateUsingGroups'] = ('__nothing_selected__', '__folder_in_itemtemplates__', ) + tuple(memberGroups)
        query['meta_type'] = 'MeetingItem'
        itemTemplates = self.context.portal_catalog(**query)
        # we need to keep the itemTemplatesPath
        folderPathsToKeep = [itemTemplatesPath, ]
        # now compute folder paths so only these paths will be passed to buildFolderTree
        # and this method will not consider any other folders
        for itemTemplate in itemTemplates:
            folderPath = '/'.join(itemTemplate.getPath().split('/')[0:-1])
            if not folderPath in folderPathsToKeep:
                folderPathsToKeep.append(folderPath)
        # first query was to find items, but now, we want to query items and folders...
        query.pop('meta_type')
        query['path'] = {'query': folderPathsToKeep, 'depth': 1}
        # define a strategy so rootPath is managed ourself or folderTree
        # fails to compute it because query['path']['query'] is a list here...
        strategy = NavtreeStrategyBase()
        strategy.rootPath = itemTemplatesPath
        folderTree = buildFolderTree(self.context, None, query, strategy)
        # the single left problem is the fact that we could have empty folders
        # because we look in the itemTemplatesPath and it returns 'directly contained items' and
        # folders, we can not do anything else using a catalog query...
        # so check children of the root level, if it is an empty folder, we remove it...
        childrenToKeep = []
        for child in folderTree['children']:
            if child['item'].portal_type == 'Folder' and not child['children']:
                continue
            childrenToKeep.append(child)
        folderTree['children'] = childrenToKeep
        return folderTree

    def displayShowHideAllLinks(self):
        '''Used on the template, display links "Show all / Hide all" making
           it possible to 'expand' or 'collapse' the entire tree, this is only relevant
           if at least one folder to expand/collapse...
        '''
        displayShowHideAllLinks = False
        for elt in self.templatesTree['children']:
            if elt['item'].portal_type == 'Folder':
                displayShowHideAllLinks = True
                break
        return displayShowHideAllLinks

    def createTemplatesTree(self):
        # if only one folder at root, we expand it by default
        atMostOneElementAtRoot = len(self.templatesTree['children']) < 2
        return self.recurse(children=self.templatesTree.get('children', []),
                            expandRootLevel=atMostOneElementAtRoot)

    recurse = ViewPageTemplateFile('templates/itemtemplates_tree_recurse.pt')
