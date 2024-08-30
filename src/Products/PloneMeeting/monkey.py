# -*- coding: utf-8 -*-

from Acquisition import aq_base
from cPickle import dumps
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from plone import api
from plone.app.querystring import queryparser
from plone.memoize import ram
from Products.Archetypes.BaseObject import BaseObject
from Products.Archetypes.Field import Field
from Products.Archetypes.Field import TextField
from Products.CMFCore.TypesTool import TypeInformation
from Products.PloneMeeting import logger
from Products.PlonePAS.tools.membership import MembershipTool
from Products.PortalTransforms.cache import Cache
from Products.PortalTransforms.transforms import safe_html
from Products.PortalTransforms.transforms.safe_html import CSS_COMMENT
from Products.PortalTransforms.transforms.safe_html import decode_htmlentities
from time import time
from types import StringType
from z3c.form import interfaces
from z3c.form.widget import SequenceWidget
from zope.i18nmessageid import Message
from zope.ramcache.ram import Storage


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
            api.portal.get_tool('portal_plonemeeting')
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
        groups = get_plone_groups_for_user()
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


TextField.__old_pm__process_input = TextField._process_input


def _process_input(self, value, file=None, default=None,
                   mimetype=None, instance=None, **kwargs):
    """Initialize new field correctly with text/html content_type."""
    file, mimetype, filename = self.__old_pm__process_input(
        value=value, file=file, default=default, mimetype=mimetype, instance=instance, **kwargs)
    # this case if when a new field is initialized on an existing element
    if not instance.checkCreationFlag() and kwargs.get('_initializing_') and 'schema' in kwargs:
        field_name = kwargs['field'] if isinstance(kwargs['field'], str) else \
            kwargs['field'].__name__
        logger.info("Initializing new field \"{0}\" on existing element at {1}".format(
            field_name, '/'.join(instance.getPhysicalPath())))
        default_content_type = kwargs['schema'][field_name].default_content_type
        if default_content_type:
            file.setContentType(instance, default_content_type)
    return file, mimetype, filename


TextField._process_input = _process_input
logger.info("Monkey patching Products.Archetypes.Field.TextField (_process_input)")


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


def Title(self):
    """Same code as dexterity's fti (DexterityFTI) for AT fti."""
    if self.title and self.i18n_domain:
        try:
            return Message(self.title.decode('utf8'), self.i18n_domain)
        except UnicodeDecodeError:
            return Message(self.title.decode('latin-1'), self.i18n_domain)
    else:
        return self.title or self.getId()


TypeInformation.__old_Title = TypeInformation.Title
TypeInformation.Title = Title
