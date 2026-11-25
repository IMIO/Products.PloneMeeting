# -*- coding: utf-8 -*-

from Acquisition import aq_base
from BTrees.IIBTree import IIBucket
from cPickle import dumps
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.pyutils.utils import safe_encode
from plone import api
from plone.app.querystring import queryparser
from plone.memoize import ram
from Products.Archetypes.BaseObject import BaseObject
from Products.Archetypes.Field import Field
from Products.Archetypes.Field import TextField
from Products.CMFCore.TypesTool import TypeInformation
from Products.PloneMeeting import logger
from Products.PloneMeeting.config import ANONYMIZED_TEXT_INDEXES
from Products.PloneMeeting.config import TOOL_ID
from Products.PloneMeeting.utils import anonymized_text_query
from Products.PloneMeeting.utils import get_anonymized_indexing_css_classes
from Products.PloneMeeting.utils import has_underscore_term
from Products.PloneMeeting.utils import may_see_anonymized_text
from Products.PloneMeeting.utils import prefix_anonymized_words
from Products.PlonePAS.tools.membership import MembershipTool
from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PortalTransforms.cache import Cache
from Products.PortalTransforms.TransformEngine import TransformTool
from Products.PortalTransforms.transforms import safe_html
from Products.PortalTransforms.transforms.safe_html import CSS_COMMENT
from Products.PortalTransforms.transforms.safe_html import decode_htmlentities
from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex
from time import time
from types import StringType
from z3c.form import interfaces
from z3c.form.widget import SequenceWidget
from zope.component.hooks import getSite
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


def _queried_values(request, index_id):
    """Values catalog query p_request is restricted to for p_index_id,
       None when not restricted (not queried, "not" or "range" query)."""
    record = parseIndexRequest(request, index_id, ('query', 'not', 'range'))
    if not record.keys or record.get('not') or record.get('range'):
        return None
    return set(record.keys)


def _queried_cfg_ids(request):
    """Ids of the MeetingConfigs catalog query p_request is restricted to,
       using the "getConfigId" index or the "portal_type" index (items and
       meetings portal_types of a MeetingConfig), None for a global query."""
    site = getSite()
    tool = site is not None and getattr(site, TOOL_ID, None) or None
    if tool is None:
        return None
    cfg_ids = _queried_values(request, 'getConfigId')
    portal_types = _queried_values(request, 'portal_type')
    if portal_types is not None:
        # only items of a MeetingConfig may contain anonymized content,
        # other portal_types (not related to a MeetingConfig) are ignored
        type_cfg_ids = set(
            [cfg.getId() for cfg in tool.objectValues('MeetingConfig')
             if portal_types.intersection(
                cfg.getItemTypeName(configType='all') + [cfg.getMeetingTypeName()])])
        # both indexes restrict the query
        cfg_ids = type_cfg_ids if cfg_ids is None else cfg_ids.intersection(type_cfg_ids)
    return cfg_ids


ZCTextIndex.__pm_old_apply_index = ZCTextIndex._apply_index


def _apply_index(self, request):
    """Monkeypatch so content anonymized for some power observers
       (see MeetingConfig.cssTransforms) is only found by users that
       may see it, words of this content are indexed prefixed by
       ANONYMIZED_TEXT_PREFIX that begins with "__":
       - a query containing a term beginning with "_" returns nothing for anybody;
       - the query of a user that may see anonymized content is completed so
         every word also matches the anonymized version of this word.
       Every text query is managed whatever the way it is done
       (dashboards, Plone search, REST API, ...), when the query is restricted
       to some MeetingConfigs, only these MeetingConfigs are taken into account."""
    if self.id in ANONYMIZED_TEXT_INDEXES:
        record = parseIndexRequest(request, self.id, self.query_options)
        if record.keys:
            query = ' '.join(record.keys)
            lexicon = self.getLexicon()
            if has_underscore_term(query, lexicon):
                return IIBucket(), (self.id,)
            if may_see_anonymized_text(_queried_cfg_ids(request)):
                request = {self.id: anonymized_text_query(query, lexicon)}
    return self.__pm_old_apply_index(request)


ZCTextIndex._apply_index = _apply_index
logger.info("Monkey patching Products.ZCTextIndex.ZCTextIndex.ZCTextIndex (_apply_index)")


HTML_MIMETYPES = ('text/html', 'text/x-html-safe')
TransformTool.__pm_old_convertTo = TransformTool.convertTo


def convertTo(self, target_mimetype, orig, data=None, object=None,
              usedby=None, context=None, **kwargs):
    # Monkeypatch so while an element is indexed (see utils.anonymized_text_indexing),
    # words of content anonymized for some power observers are prefixed when HTML
    # is converted to text/plain.
    # The transforms cache is not used (neither read nor stored) so a plain
    # version cached before is not indexed and the prefixed version is never
    # returned outside indexing.
    # No docstring so it is not publishable, like the original convertTo.
    css_classes = get_anonymized_indexing_css_classes()
    if css_classes and orig and target_mimetype == 'text/plain' and \
       kwargs.get('mimetype') in HTML_MIMETYPES:
        is_bytes = isinstance(orig, bytes)
        if any(safe_encode(css_class) in safe_encode(orig) for css_class in css_classes):
            orig = prefix_anonymized_words(orig, css_classes)
            orig = safe_encode(orig) if is_bytes else orig
        object = None
    return self.__pm_old_convertTo(target_mimetype, orig, data=data, object=object,
                                   usedby=usedby, context=context, **kwargs)


TransformTool.convertTo = convertTo
logger.info("Monkey patching Products.PortalTransforms.TransformEngine.TransformTool (convertTo)")
