# -*- coding: utf-8 -*-

AUTH_INFOS_ATTR = "keycloak_auth_infos"

AUTH_URL = 'https://keycloak-apps.cloud.imio-test.be/realms/vision/protocol/openid-connect/token'
AUTH_CLIENT_ID = 'vision'
AUTH_CLIENT_SECRET = '71dFZaMv96cJYCx@HANr77NyQ0Lz0I%i'
AUTH_USERNAME = 'demo-vision'
AUTH_PASSWORD = 'ztm,M=+3yrL{^6VkTGV;x&(T'
AUTH_CURL_COMMAND = "curl --location '%s' \
--header 'Content-Type: application/x-www-form-urlencoded' \
--header 'Cookie: KEYCLOAK_LOCALE=fr' \
--data-urlencode 'client_id=%s' \
--data-urlencode 'client_secret=%s' \
--data-urlencode 'username=%s' \
--data-urlencode 'password=%s' \
--data-urlencode 'grant_type=password'" % (
    AUTH_URL, AUTH_CLIENT_ID, AUTH_CLIENT_SECRET, AUTH_USERNAME, AUTH_PASSWORD)

API_URL = 'https://api-staging.imio.be/imio/vision/v1/municipalities/demo/%s?delib_user=%s%s'
API_USERNAME = 'dgen'
API_DELIB_UID = '93acfdd74c8342f180c4f0a02e6a0c61'
