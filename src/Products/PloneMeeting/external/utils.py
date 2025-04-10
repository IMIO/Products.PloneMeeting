# -*- coding: utf-8 -*-

from appy.gen import No
from datetime import datetime
from datetime import timedelta
from Products.PloneMeeting import logger
from Products.PloneMeeting.external.config import API_URL
from Products.PloneMeeting.external.config import API_USERNAME
from Products.PloneMeeting.external.config import AUTH_CURL_COMMAND
from Products.PloneMeeting.external.config import AUTH_INFOS_ATTR
from plone import api
from zope.globalrequest import getRequest

import httplib2
import json
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
        result = subprocess.check_output(
            AUTH_CURL_COMMAND, shell=True)
        result = json.loads(result)
        auth_infos['access_token'] = result['access_token']
        # store that expires_in is 60 seconds before real expires_in
        # so we may probably execute one last request
        auth_infos['expires_in'] = datetime.now() + timedelta(seconds=result['expires_in'] - 60)
        setattr(portal, AUTH_INFOS_ATTR, auth_infos)
    logger.info(auth_infos['access_token'])
    return auth_infos['access_token']


def send_json_request(
        endpoint,
        extra_parameters={},
        extra_headers={},
        method='GET',
        body='',
        return_as_raw=False):
    """Send a json request and returns decoded response."""
    token = get_auth_token()
    headers = {
        'Accept': 'application/json',
        'Cache-Control': 'no-store',
        'Pragma': 'no-cache',
        'X-Belga-Context': 'API',
        'expires': 'Mon, 26 Jul 1997 05:00:00 GMT',
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': "Bearer %s" % token,
    }
    headers.update(extra_headers)
    # prepare url to call
    if extra_parameters:
        extra_parameters = "&" + urllib.urlencode(extra_parameters)
    url = API_URL % (endpoint, API_USERNAME, extra_parameters or "")
    target = urlparse(url)
    h = httplib2.Http()
    logger.info("Executing JSON call '%s'" % target.geturl())
    start = datetime.now()
    response, content = h.request(
        target.geturl(),
        method,
        body,
        headers)
    logger.info(datetime.now() - start)
    if response.status in [404, 500]:
        api.portal.show_message(content, request=getRequest())
        content = No("Error status: %d (%s)" % (response.status, content))
    if not return_as_raw and content:
        return json.loads(content)
    else:
        return content
