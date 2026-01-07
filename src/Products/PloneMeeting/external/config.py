# -*- coding: utf-8 -*-
import os


# attribute name on the portal to store keycloak auth token
AUTH_INFOS_ATTR = "keycloak_auth_infos"

# keycloak auth token configuration
VISION_API_URL = os.getenv('VISION_API_URL')
VISION_AUTH_URL = os.getenv('VISION_AUTH_URL')
VISION_CLIENT_ID = os.getenv('VISION_CLIENT_ID')
VISION_CLIENT_SECRET = os.getenv('VISION_CLIENT_SECRET')
VISION_AUTH_USERNAME = os.getenv('VISION_AUTH_USERNAME')
VISION_AUTH_PASSWORD = os.getenv('VISION_AUTH_PASSWORD')
AUTH_CURL_COMMAND = "curl --location '%s' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Cookie: KEYCLOAK_LOCALE=fr' \
--data-urlencode 'client_id=%s' \
--data-urlencode 'client_secret=%s' \
--data-urlencode 'username=%s' \
--data-urlencode 'password=%s' \
--data-urlencode 'grant_type=password'" % (
    VISION_AUTH_URL,
    VISION_CLIENT_ID,
    VISION_CLIENT_SECRET,
    VISION_AUTH_USERNAME,
    VISION_AUTH_PASSWORD)
REFRESH_AUTH_CURL_COMMAND = "curl --location '%s' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Cookie: KEYCLOAK_LOCALE=fr' \
--data-urlencode 'client_id=%s' \
--data-urlencode 'client_secret=%s' \
--data-urlencode 'grant_type=refresh_token' \
--data-urlencode 'refresh_token={0}'" % (
    VISION_AUTH_URL,
    VISION_CLIENT_ID,
    VISION_CLIENT_SECRET)
VISION_MUNICIPALITY_ID = os.getenv('VISION_MUNICIPALITY_ID', '')

# api configuration
API_URL = '{0}/municipalities/{1}/%s?delib_user=%s%s'.format(
    VISION_API_URL, VISION_MUNICIPALITY_ID)
