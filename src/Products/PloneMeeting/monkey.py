
from Acquisition import aq_base
from imio.helpers.cache import get_cachekey_volatile
from plone import api
from plone.api.exc import InvalidParameterError
from plone.app.querystring import queryparser
from plone.memoize import ram
from Products.Archetypes.BaseObject import BaseObject
from Products.Archetypes.Field import Field
from Products.CMFPlone.CatalogTool import CatalogTool
from Products.PloneMeeting import logger
from Products.PortalTransforms.cache import Cache
from Products.PortalTransforms.transforms import safe_html
from Products.PortalTransforms.transforms.safe_html import CSS_COMMENT
from Products.PortalTransforms.transforms.safe_html import decode_htmlentities
from types import StringType
from z3c.form.widget import SequenceWidget
from z3c.form import interfaces


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
