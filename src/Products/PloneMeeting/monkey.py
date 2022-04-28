
from Acquisition import aq_base
from cPickle import dumps
from imio.helpers.cache import get_cachekey_volatile
from imio.helpers.security import fplog
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.querystring import queryparser
from plone.memoize import ram
from plone.restapi.deserializer import boolean_value
from plone.restapi.services import Service
from plonemeeting.restapi import logger as pmrestapi_logger
from Products.Archetypes.BaseObject import BaseObject
from Products.Archetypes.Field import Field
from Products.CMFPlone.CatalogTool import CatalogTool
from Products.PloneMeeting import logger
from Products.PloneMeeting.utils import get_current_user_id
from Products.PlonePAS.tools.membership import MembershipTool
from Products.PortalTransforms.cache import Cache
from Products.PortalTransforms.transforms import safe_html
from Products.PortalTransforms.transforms.safe_html import CSS_COMMENT
from Products.PortalTransforms.transforms.safe_html import decode_htmlentities
from time import time
from types import StringType
from z3c.form import interfaces
from z3c.form.widget import SequenceWidget
from zope.ramcache.ram import Storage

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
        user_id = get_current_user_id()
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
    date = get_cachekey_volatile('Products.PloneMeeting.ToolPloneMeeting._users_groups_value')
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


def hasScript(s):
    """Override to keep data:image elements, turned 'data:' to 'data:text'
    """
    s = decode_htmlentities(s)
    s = s.replace('\x00', '')
    s = CSS_COMMENT.sub('', s)
    s = ''.join(s.split()).lower()
    for t in ('script:', 'expression:', 'expression(', 'data:text'):
        if t in s:
            return True
    return False


safe_html.hasScript = hasScript
logger.info("Monkey patching Products.PortalTransforms.transforms.safe_html (hasScript)")


Field.__old_pm_validate_content_types = Field.validate_content_types


def validate_content_types(self, instance, value, errors):
    """Avoid wrong validation error when html value is detected as text/plain,
       this may occur when having a image data:base64 (when using imagerotate)."""
    error = Field.__old_pm_validate_content_types(self, instance, value, errors)
    if error and "text/plain" in error:
        if isinstance(value, StringType) and \
           value.startswith('<p>'):
            errors.pop(self.getName())
            error = None
    return error


Field.validate_content_types = validate_content_types
logger.info("Monkey patching Products.Archetypes.Field.Field (validate_content_types)")


def extract(self, default=interfaces.NO_VALUE):
    """See z3c.form.interfaces.IWidget."""

    if (self.name not in self.request and
            self.name + '-empty-marker' in self.request):
        return []
    value = self.request.get(self.name, default)
    if value != default:
        if not isinstance(value, (tuple, list)):
            value = (value,)
        # do some kind of validation, at least only use existing values
        for token in value:
            # XXX begin do not encode to utf-8 for MasterSelectWidget
            # as we use unicode values or validation fails with "field required"
            if isinstance(token, unicode) and not self.__class__.__name__ == 'MasterSelectWidget':
                token = token.encode('utf-8')
            # XXX end
            if token == self.noValueToken:
                continue
            try:
                self.terms.getTermByToken(token)
            except LookupError:
                return default
    return value


SequenceWidget.extract = extract
logger.info("Monkey patching z3c.form.widget.SequenceWidget (extract)")


def getMemberInfo_cachekey(method, self, memberId=None):
    '''cachekey method for self.getMemberInfo.
       Cache is invalidated by plone.app.controlpanel upon any control panel changes.'''
    return memberId


MembershipTool.__old_pm_getMemberInfo = MembershipTool.getMemberInfo


@ram.cache(getMemberInfo_cachekey)
def getMemberInfo(self, memberId=None):
    """Monkeypatched to add caching."""
    return self.__old_pm_getMemberInfo(memberId)


MembershipTool.getMemberInfo = getMemberInfo
logger.info("Monkey patching Products.PlonePAS.tools.membership.MembershipTool (getMemberInfo)")


# plonemeeting.restapi, need to monkeypatch here because order of packages
# monkey patching in plonemeeting.restapi does not seem to work...

Service.__old_pm_render = Service.render


def render(self):
    """Monkeypatched to add fplog."""
    query_string = self.request.get('QUERY_STRING')
    extras = 'name={0} url={1}{2}'.format(
        self.__name__,
        self.request.get('ACTUAL_URL'),
        query_string and " query_string={0}".format(query_string) or '')
    fplog("restapi_call", extras=extras)

    res = self.__old_pm_render()
    # debug may be enabled by passing debug=true as parameter to the restapi call
    # or when setting the RESTAPI_DEBUG environment variable
    if boolean_value(self.request.form.get('debug', False)) or \
       boolean_value(os.environ.get('RESTAPI_DEBUG', False)):
        fplog("restapi_call_debug", extras="\n" + res)
    return res


Service.render = render
pmrestapi_logger.info("Monkey patching plone.restapi.services.RestService (render)")


Storage.__old_pm_getEntry = Storage.getEntry


def getEntry(self, ob, key):
    if self.lastCleanup <= time() - self.cleanupInterval:
        self.cleanup()

    try:
        data = self._data[ob][key]
    except KeyError:
        if ob not in self._misses:
            self._misses[ob] = 0
        self._misses[ob] += 1
        raise
    else:
        data[2] += 1                    # increment access count
        # XXX begin change by PM, update timestamp
        timestamp = time()
        data[1] = timestamp
        # XXX end change by PM

        return data[0]


Storage.getEntry = getEntry
logger.info("Monkey patching zope.ramcache.ram.Storage (getEntry)")


Storage.__old_pm_getStatistics = Storage.getStatistics


def getStatistics(self):
    objects = self._data.keys()
    objects.sort()
    result = []

    for ob in objects:
        size = len(dumps(self._data[ob]))
        hits = sum(entry[2] for entry in self._data[ob].itervalues())
        from DateTime import DateTime
        older_date = min(entry[1] for entry in self._data[ob].itervalues())
        result.append({'path': ob,
                       'hits': hits,
                       'misses': self._misses.get(ob, 0),
                       'size': size,
                       'entries': len(self._data[ob]),
                       'older_date': older_date and DateTime(older_date)})
    return tuple(result)


Storage.getStatistics = getStatistics
logger.info("Monkey patching zope.ramcache.ram.Storage (getStatistics)")
