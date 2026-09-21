# -*- coding: utf-8 -*-

from AccessControl import Unauthorized
from imio.helpers.cache import get_current_user_id
from imio.helpers.ws import send_json_request
from plone import api
from Products.PloneMeeting.external.config import VISION_URL_PATTERN
from zope.globalrequest import getRequest


def send_vision_json_request(
        endpoint,
        extra_parameters={},
        extra_headers={},
        method='GET',
        data={},
        url_pattern=VISION_URL_PATTERN,
        return_as_raw=False,
        show_message=False):
    """Manage url parameter and user_id."""
    request = getRequest()
    # make a Zope Manager able to pass an arbitrary external_user_id for testing
    user_id = request.get('external_user_id')
    if user_id:
        tool = api.portal.get_tool('portal_plonemeeting')
        if not tool.isManager(realManagers=True):
            raise Unauthorized
    else:
        user_id = get_current_user_id(request)
    url = VISION_URL_PATTERN.format(endpoint, user_id)
    return send_json_request(
        url=url,
        extra_parameters=extra_parameters,
        extra_headers=extra_headers,
        method=method,
        data=data,
        return_as_raw=return_as_raw,
        show_message=show_message)
