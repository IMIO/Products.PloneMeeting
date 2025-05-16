# -*- coding: utf-8 -*-

from collective.contact.plonegroup.utils import get_plone_group_id
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.content import uuidToObject
from plone import api
from plone.app.layout.navigation.navtree import buildFolderTree
from plone.app.layout.navigation.navtree import NavtreeStrategyBase
from plone.memoize import ram
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PloneMeeting.config import TOOL_FOLDER_ITEM_TEMPLATES
from zope.i18n import translate


class ItemTemplateView(BrowserView):
    '''
      This manage the overlay popup displayed when a user want to select an item template to create a new item.
    '''
    def __init__(self, context, request):
        super(BrowserView, self).__init__(context, request)
        self.context = context
        self.request = request
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)
        self.request.set('disable_border', 1)

    def __call__(self):
        """ """
        form = self.request.form
        templateUID = form.get('templateUID', None)
        cancelled = form.get('form.buttons.cancel', False)
        if templateUID:
            newItem = self.createItemFromTemplate(templateUID)
            newItemUrl = newItem.absolute_url() + '/edit'
            # remove title if we are adding an item using default item template
            default_template = self.cfg.get_default_item_template()
            if default_template and templateUID == default_template.UID():
                newItemUrl += '?title='
            return self.request.RESPONSE.redirect(newItemUrl)
        elif cancelled:
            # the only way to enter here is the popup overlay not to be shown
            # because while using the popup overlay, the jQ function take care
            # of hidding it while the Cancel button is hit
            return self.request.RESPONSE.redirect(form.get('form.HTTP_REFERER'))
        else:
            # compute and store templates tree so it can be used in several places
            # this is not done in the __init__ because the user is "Anonymous" in the __init__
            # and as we filter on "templateUsingGroup", we need a valid user...
            self.renderedTemplatesTree = self._patch_html_content(self._createTemplatesTree())
            return self.index()

    def _template_path_and_title(self, templateItem):
        """Return title of p_templateItem including name of
           subfolders until 'itemtemplates' folder."""
        titles = [templateItem.Title()]
        parent = templateItem.aq_parent
        while parent.getId() != TOOL_FOLDER_ITEM_TEMPLATES:
            titles.insert(0, parent.Title())
            parent = parent.aq_parent
        return ' / '.join(titles)

    def createItemFromTemplate(self, templateUID):
        '''The user wants to create an item from a item template that lies in
           this meeting configuration. Item id is in the request.'''
        templateItem = uuidToObject(templateUID, unrestricted=True)
        # Create the new item by duplicating the template item
        member_id = get_current_user_id()
        template_path_and_title = safe_unicode(self._template_path_and_title(templateItem))
        cloneEventActionLabel = translate(
            'create_meeting_item_from_template_label_comments',
            domain='imio.history',
            mapping={'template_path_and_title': template_path_and_title, },
            context=self.request)
        # if a proposingGroup is defined on itemTemplate and current user is creator
        # for this proposingGroup, we keep it
        keepProposingGroup = False
        proposingGroup = templateItem.getProposingGroup()
        if get_plone_group_id(proposingGroup, 'creators') in get_plone_groups_for_user():
            keepProposingGroup = True
        newItem = templateItem.clone(newOwnerId=member_id,
                                     cloneEventAction='create_meeting_item_from_template',
                                     cloneEventActionLabel=cloneEventActionLabel,
                                     destFolder=self.context,
                                     newPortalType=self.cfg.getItemTypeName(),
                                     keepProposingGroup=keepProposingGroup,
                                     keep_ftw_labels=True)
        # set _at_creation_flag to True so if user cancel first edit, it will be removed
        newItem._at_creation_flag = True
        return newItem

    def _getTemplatesTree(self):
        '''Create the structure of elements used to display the item templates tree to the item creators.
           We only want to show folders and items the current creator may use, so we do that in 2 steps :
           - a first catalog query that will find every items the creator may use,
             when found, we save the differents paths to these items so we will be able to
             not take into account folder that could exist in the configuration but that would
             be empty because no items into it;
           - when the query is build with list of paths to consider, we use buildFolderTree
             that will build a 'tree' dict with elements and children.'''
        # first query the catalog to see wich items the current user may select
        itemTemplatesPath = '/'.join(self.cfg.itemtemplates.getPhysicalPath())
        itemTemplates = self.cfg.getItemTemplates(as_brains=True, onlyActive=True, filtered=True)
        # we need to keep the itemTemplatesPath
        folderPathsToKeep = [itemTemplatesPath, ]
        # now compute folder paths so only these paths will be passed to buildFolderTree
        # and this method will not consider any other folders
        for itemTemplate in itemTemplates:
            folderPath = '/'.join(itemTemplate.getPath().split('/')[0:-1])
            # keep every folders of folderPath in case the itemtemplate is in a sub/sub/sub/...folder
            while folderPath not in folderPathsToKeep:
                folderPathsToKeep.append(folderPath)
                folderPath = '/'.join(folderPath.split('/')[0:-1])
        query = self.cfg._itemTemplatesQuery(onlyActive=True, filtered=True)
        # we want to query every Folders too
        query['portal_type'] = (query['portal_type'], 'Folder')
        query['path'] = {'query': folderPathsToKeep, 'depth': 1}
        # define a strategy so rootPath is managed ourself or folderTree
        # fails to compute it because query['path']['query'] is a list here...
        strategy = NavtreeStrategyBase()
        strategy.rootPath = itemTemplatesPath
        # remove useless query parameters
        strategy.supplimentQuery.pop('is_default_page', None)
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
        return self.renderedTemplatesTree.count('class="folder"')

    def _createTemplatesTree_cachekey(method, self):
        '''cachekey method for self._createTemplatesTree.'''
        return repr(self.cfg), self.cfg.modified(), get_plone_groups_for_user()

    @ram.cache(_createTemplatesTree_cachekey)
    def _createTemplatesTree(self):
        # if only one folder at root, we expand it by default
        templatesTree = self._getTemplatesTree()
        atMostOneElementAtRoot = len(templatesTree['children']) < 2
        return self.recurse(children=templatesTree.get('children', []),
                            expandRootLevel=atMostOneElementAtRoot).strip()

    def _patch_html_content(self, html_content):
        """To be able to use caching, we need to
           change [baseUrl] after __call__ is rendered."""
        html_content = html_content.replace("[baseUrl]", self.context.absolute_url())
        return html_content

    recurse = ViewPageTemplateFile('templates/itemtemplates_tree_recurse.pt')
