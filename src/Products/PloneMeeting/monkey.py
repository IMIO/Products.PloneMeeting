
from Acquisition import aq_base
from collective.documentviewer.settings import Settings
from collective.documentviewer.views import PDFFiles
from collective.documentviewer.views import PDFTraverseBlobFile
from imio.annex.content.annex import Annex
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.content import uuidsToObjects
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.querystring import queryparser
from plone.memoize import ram
from Products.Archetypes.BaseObject import BaseObject
from Products.CMFPlone.CatalogTool import CatalogTool
from Products.PloneMeeting import logger
from Products.PloneMeeting.content.advice import MeetingAdvice
from Products.PortalTransforms.cache import Cache
from zExceptions import NotFound

import os


def _patched_equal(context, row):
    """Monkeypatch _equal so we never pass None as values or it breaks as
       None can not be indexed.
    """
    row_values = row.values
    if row_values is None:
        row_values = []
    return {row.index: {'query': row_values, }}


queryparser.__pm_old_equal = queryparser._equal
queryparser._equal = _patched_equal
logger.info("Monkey patching plone.app.querystring.queryparser (_equal)")
_equal = _patched_equal


def userAndGroupsAwarePortalTransformsCacheKey():
    """Monkeypatch Products.PortalTransforms.Cache._genCacheKey
       to generate a cache key that is aware of current user and it's groups.
    """

    def _genCacheKey(self, identifier, *args):
        # XXX begin changes by PM, do the cache key user and groups aware
        from plone import api
        from plone.api.exc import InvalidParameterError
        try:
            # while creating a new Plone Site, portal_plonemeeting is not available
            tool = api.portal.get_tool('portal_plonemeeting')
        except InvalidParameterError:
            return Cache.__pm_old_genCacheKey(self, identifier, *args)
        # XXX end of changes by PM
        key = identifier
        for arg in args:
            key = '%s_%s' % (key, arg)
        key = key.replace('/', '_')
        key = key.replace('+', '_')
        key = key.replace('-', '_')
        key = key.replace(' ', '_')
        # XXX begin changes by PM, do the cache key user and groups aware
        user = api.user.get_current()
        user_id = user.getId()
        tool = api.portal.get_tool('portal_plonemeeting')
        groups = tool.get_plone_groups_for_user()
        key = '%s_%s_%s' % (key, user_id, '_'.join(groups))
        # XXX end of changes by PM
        if hasattr(aq_base(self.context), 'absolute_url'):
            return key, self.context.absolute_url()
        return key

    Cache.__pm_old_genCacheKey = Cache._genCacheKey
    Cache._genCacheKey = _genCacheKey
    logger.info("Monkey patching Products.PortalTransforms.cache (_genCacheKey)")


userAndGroupsAwarePortalTransformsCacheKey()


BaseObject.__old_pm_validate = BaseObject.validate


def validate(self, REQUEST=None, errors=None, data=None, metadata=None):
    """Monkeypatch to log errors because sometimes, when errors occur in multiple
       or on disabled fields, it is not visible into the UI."""
    errors = self.__old_pm_validate(REQUEST, errors, data, metadata)
    if errors and api.user.get_current().has_role('Manager'):
        logger.info(errors)
    return errors


BaseObject.validate = validate
logger.info("Monkey patching Products.Archetypes.BaseObject.BaseObject (validate)")


def _listAllowedRolesAndUsers_cachekey(method, self, user):
    '''cachekey method for self._listAllowedRolesAndUsers.'''
    date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting.get_plone_groups_for_user')
    try:
        tool = api.portal.get_tool('portal_plonemeeting')
        users_groups = tool._users_groups_value()
    except InvalidParameterError:
        users_groups = None
    return date, users_groups, user.getId()


@ram.cache(_listAllowedRolesAndUsers_cachekey)
def _listAllowedRolesAndUsers(self, user):
    """Monkeypatch to use ToolPloneMeeting.get_plone_groups_for_user instead getGroups.
       Moreover store this in the REQUEST."""

    # Makes sure the list includes the user's groups.
    result = user.getRoles()
    if 'Anonymous' in result:
        # The anonymous user has no further roles
        return ['Anonymous']
    result = list(result)
    # XXX change, replaced getGroups by tool.get_plone_groups_for_user
    # if hasattr(aq_base(user), 'getGroups'):
    #     groups = ['user:%s' % x for x in user.getGroups()]
    try:
        tool = api.portal.get_tool('portal_plonemeeting')
        groups = tool.get_plone_groups_for_user()
    except InvalidParameterError:
        groups = user.getGroups()
    if groups:
        groups = ['user:%s' % x for x in groups]
        result = result + groups
    # Order the arguments from small to large sets
    result.insert(0, 'user:%s' % user.getId())
    result.append('Anonymous')
    return result

CatalogTool._listAllowedRolesAndUsers = _listAllowedRolesAndUsers
logger.info("Monkey patching Products.CMFPlone.CatalogTool.CatalogTool (_listAllowedRolesAndUsers)")


def _getCatalogTool(self):
    """Temporary moneypatch so annex are not indexed in portal_catalog."""
    return None

Annex._getCatalogTool = _getCatalogTool
logger.info("Monkey patching imio.annex.content.annex.Annex (_getCatalogTool)")
MeetingAdvice._getCatalogTool = _getCatalogTool
logger.info("Monkey patching Products.PloneMeeting.content.advice.MeetingAdvice (_getCatalogTool)")


def publishTraverse(self, request, name):
    if len(self.previous) > 2:
        raise NotFound

    if len(name) == 1:
        if len(self.previous) == 0:
            previous = [name]
        else:
            previous = self.previous
            previous.append(name)

        self.context.path = os.path.join(self.context.path, name)
        files = PDFFiles(self.context, request, previous)
        files.__parent__ = self
        return files.__of__(self)

    if len(self.previous) == 2 and (self.previous[0] != name[0] or
       self.previous[1] != name[1:2]):
        # make sure the first two were a sub-set of the uid
        raise NotFound

#        uidcat = getToolByName(self.site, 'uid_catalog')
#        brains = uidcat(UID=name)
#        Dexterity items are not indexed in uid_catalog

    # XXX begin changes by PloneMeeting
#        cat = getToolByName(self.site, 'portal_catalog')
#        brains = cat.unrestrictedSearchResults(UID=name)
#        if len(brains) == 0:
#            raise NotFound

#        fileobj = brains[0].getObject()
#        getObject raise Unauthorized because we are Anonymous in the traverser
#        fileobj = brains[0]._unrestrictedGetObject()

    objs = uuidsToObjects(uuids=[name], check_contained_uids=True, unrestricted=True)
    if len(objs) == 0:
        raise NotFound
    fileobj = objs[0]
    # XXX end changes by PloneMeeting

    settings = Settings(fileobj)
    if settings.storage_type == 'Blob':
        fi = PDFTraverseBlobFile(fileobj, settings, request)
        fi.__parent__ = self
        return fi.__of__(self)
    else:
        # so permission checks for file object are applied
        # to file resource
        self.__roles__ = tuple(fileobj.__roles__) + ()
        if settings.obfuscated_filepath:
            # check if this thing isn't published...
            self.context.path = os.path.join(self.context.path, name)
            name = settings.obfuscate_secret

        fi = super(PDFFiles, self).publishTraverse(request, name)
        return fi

PDFFiles.publishTraverse = publishTraverse
logger.info("Monkey patching collective.documentviewer.views.PDFFiles (publishTraverse)")
