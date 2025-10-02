# -*- coding: utf-8 -*-

from appy.gen import No
from datetime import datetime
from datetime import timedelta
from imio.helpers.cache import get_current_user_id
from imio.helpers.security import fplog
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting import logger
from Products.PloneMeeting.external.config import API_URL
from Products.PloneMeeting.external.config import AUTH_CURL_COMMAND
from Products.PloneMeeting.external.config import AUTH_INFOS_ATTR
from zope.globalrequest import getRequest

import json
import requests
import subprocess
import urllib


try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


def get_auth_token():
    """ """
    portal = api.portal.get()
    auth_infos = getattr(portal, AUTH_INFOS_ATTR, {})
    if not auth_infos or auth_infos['expires_in'] < datetime.now():
        logger.info('Getting authentication token')
        start = datetime.now()
        result = subprocess.check_output(
            AUTH_CURL_COMMAND, shell=True)
        logger.info(datetime.now() - start)
        result = json.loads(result)
        if 'access_token' in result:
            auth_infos['access_token'] = result['access_token']
            # store that expires_in is 60 seconds before real expires_in
            # so we may probably execute one last request
            auth_infos['expires_in'] = datetime.now() + timedelta(seconds=result['expires_in'] - 60)
            setattr(portal, AUTH_INFOS_ATTR, auth_infos)
    # logger.info(auth_infos['access_token'])
    return auth_infos.get('access_token') or result

def send_json_request(
        endpoint,
        extra_parameters={},
        extra_headers={},
        method='GET',
        data={},
        return_as_raw=False,
        show_message=False):
    """Send a json request and returns decoded response."""
    token = get_auth_token()
    if 'error' in token:
        return No("Error getting token: %s (%s)" % (token['error'], token.get('error_description', '')))
    headers = {
        'Accept': 'application/json',
        'Cache-Control': 'no-store',
        'Pragma': 'no-cache',
        'expires': 'Mon, 26 Jul 1997 05:00:00 GMT',
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': "Bearer %s" % token,
    }
    headers.update(extra_headers)
    # prepare url to call, manage extra_parameters
    if extra_parameters:
        extra_parameters = "&" + urllib.urlencode(extra_parameters)
    request = getRequest()
    url = API_URL % (endpoint, get_current_user_id(request), extra_parameters or "")
    target = urlparse(url)
    url = target.geturl()
    # manage cache per request for 'GET'
    content = None
    extras = 'method={0} url={1}'.format(method, url)
    if method == 'GET':
        cachekey_id = "send_json_request_cachekey"
        cache = getattr(request, cachekey_id, {})
        cachekey = "%s__%s" % (url, method)
        content = cache.get(cachekey, None)
        if content is not None:
            fplog('cached_json_call', extras=extras)
    if content is None:
        fplog('execute_json_call', extras=extras)
        start = datetime.now()
        me = {
            "GET": requests.get,
            "POST": requests.post,
            "DELETE": requests.delete}.get(method)
        response = me(url, headers=headers, json=data)
        content = response.content
        logger.info(datetime.now() - start)
        if response.status_code >= 300:
            logger.warn(content)
            if show_message:
                api.portal.show_message(safe_unicode(content), request=getRequest())
            content = No("Error status: %d (%s)" % (response.status_code, content))
            content.status_code = response.status_code
        # manage cache per request for 'GET'
        if method == 'GET':
            cache[cachekey] = content
            setattr(request, cachekey_id, cache)
    if not return_as_raw and content:
        return json.loads(content)
    else:
        return content
