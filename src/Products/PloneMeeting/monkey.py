
from Acquisition import aq_base
from imio.annex.content.annex import Annex
from imio.helpers.cache import get_cachekey_volatile
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.querystring import queryparser
from plone.memoize import ram
from Products.Archetypes.BaseObject import BaseObject
from Products.CMFPlone.CatalogTool import CatalogTool
from Products.PloneMeeting import logger
from Products.PloneMeeting.content.advice import MeetingAdvice
from Products.PortalTransforms.cache import Cache


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
