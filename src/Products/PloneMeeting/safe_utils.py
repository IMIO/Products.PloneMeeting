# -*- coding: utf-8 -*-
# flake8: noqa

from collections import OrderedDict
from datetime import datetime
from DateTime import DateTime
from imio.helpers.cache import get_current_user_id
from imio.helpers.cache import get_plone_groups_for_user
from imio.helpers.cache import invalidate_cachekey_volatile_for
from imio.helpers.content import get_user_fullname
from imio.helpers.date import formatDate
from imio.helpers.date import wordizeDate
from imio.helpers.workflow import update_role_mappings_for
from imio.helpers.xhtml import unescape_html
from imio.history.utils import getLastWFAction
from Products.CPUtils.Extensions.utils import fileSize
from Products.CPUtils.Extensions.utils import tobytes
from Products.PloneMeeting.browser.meeting import get_default_attendees
from Products.PloneMeeting.browser.meeting import get_default_signatories
from Products.PloneMeeting.browser.meeting import get_default_voters
from Products.PloneMeeting.browser.views import is_all_count
from Products.PloneMeeting.browser.views import print_votes
from Products.PloneMeeting.ftw_labels.utils import get_labels
from Products.PloneMeeting.utils import cleanMemoize
from Products.PloneMeeting.utils import cropHTML
from Products.PloneMeeting.utils import down_or_up_wf
from Products.PloneMeeting.utils import escape
from Products.PloneMeeting.utils import field_is_empty
from Products.PloneMeeting.utils import fieldIsEmpty
from Products.PloneMeeting.utils import get_annexes
from Products.PloneMeeting.utils import get_attendee_short_title
from Products.PloneMeeting.utils import get_gn_position_name
from Products.PloneMeeting.utils import get_internal_number
from Products.PloneMeeting.utils import get_next_meeting
from Products.PloneMeeting.utils import get_prefixed_gn_position_name
from Products.PloneMeeting.utils import get_public_url
from Products.PloneMeeting.utils import get_referer_obj
from Products.PloneMeeting.utils import getAdvicePortalTypeIds
from Products.PloneMeeting.utils import getCurrentMeetingObject
from Products.PloneMeeting.utils import is_transition_before_date
from Products.PloneMeeting.utils import isPowerObserverForCfg
from Products.PloneMeeting.utils import listifySignatures
from Products.PloneMeeting.utils import normalize
from Products.PloneMeeting.utils import normalize_id
from Products.PloneMeeting.utils import number_word
from Products.PloneMeeting.utils import org_id_to_uid
from Products.PloneMeeting.utils import reindex_object
from Products.PloneMeeting.utils import set_dx_value
from Products.PloneMeeting.utils import set_internal_number
from Products.PloneMeeting.utils import toHTMLStrikedContent
from Products.PloneMeeting.utils import uncapitalize
