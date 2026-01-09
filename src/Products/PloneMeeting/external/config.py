# -*- coding: utf-8 -*-
import os


# attribute name on the portal to store keycloak auth token
AUTH_INFOS_ATTR = "keycloak_auth_infos"

# keycloak auth token configuration
SSO_APPS_URL = os.getenv('SSO_APPS_URL')
SSO_APPS_CLIENT_ID = os.getenv('SSO_APPS_CLIENT_ID')
SSO_APPS_CLIENT_SECRET = os.getenv('SSO_APPS_CLIENT_SECRET')
SSO_APPS_USER_USERNAME = os.getenv('SSO_APPS_USER_USERNAME')
SSO_APPS_USER_PASSWORD = os.getenv('SSO_APPS_USER_PASSWORD')
AUTH_CURL_COMMAND = "curl --location '%s' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Cookie: KEYCLOAK_LOCALE=fr' \
--data-urlencode 'client_id=%s' \
--data-urlencode 'client_secret=%s' \
--data-urlencode 'username=%s' \
--data-urlencode 'password=%s' \
--data-urlencode 'grant_type=password'" % (
    SSO_APPS_URL,
    SSO_APPS_CLIENT_ID,
    SSO_APPS_CLIENT_SECRET,
    SSO_APPS_USER_USERNAME,
    SSO_APPS_USER_PASSWORD)
REFRESH_AUTH_CURL_COMMAND = "curl --location '%s' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Cookie: KEYCLOAK_LOCALE=fr' \
--data-urlencode 'client_id=%s' \
--data-urlencode 'client_secret=%s' \
--data-urlencode 'grant_type=refresh_token' \
--data-urlencode 'refresh_token={0}'" % (
    SSO_APPS_URL,
    SSO_APPS_CLIENT_ID,
    SSO_APPS_CLIENT_SECRET)

MUNICIPALITY_ID = SSO_APPS_USER_USERNAME.split('_')[1] if \
    (SSO_APPS_USER_USERNAME and '_' in SSO_APPS_USER_USERNAME) else ''

# api configuration
VISION_API_URL = os.getenv('VISION_API_URL')
VISION_URL = '{0}municipalities/{1}/%s?delib_user=%s%s'.format(
    VISION_API_URL, MUNICIPALITY_ID)
