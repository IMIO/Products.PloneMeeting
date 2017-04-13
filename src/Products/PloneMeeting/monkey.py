
from Acquisition import aq_base
from Products.PortalTransforms.cache import Cache
from Products.PloneMeeting import logger

from plone.app.querystring import queryparser


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
        key = identifier
        for arg in args:
            key = '%s_%s' % (key, arg)
        key = key.replace('/', '_')
        key = key.replace('+', '_')
        key = key.replace('-', '_')
        key = key.replace(' ', '_')
        # XXX begin changes by PM, do the cache key user and groups aware
        from plone import api
        user = api.user.get_current()
        user_id = user.getId()
        groups = []
        # user is not anonymous
        if user_id:
            # sometimes the user does not have getGroups, this is the case
            # while adding the 'standard' Plone Site
            groups = getattr(user, 'getGroups', list)()
        key = '%s_%s_%s' % (key, user_id, '_'.join(groups))
        # XXX end of changes by PM
        if hasattr(aq_base(self.context), 'absolute_url'):
            return key, self.context.absolute_url()
        return key

    Cache.__pm_old_genCacheKey = Cache._genCacheKey
    Cache._genCacheKey = _genCacheKey
    logger.info("Monkey patching Products.PortalTransforms.cache (_genCacheKey)")

userAndGroupsAwarePortalTransformsCacheKey()
