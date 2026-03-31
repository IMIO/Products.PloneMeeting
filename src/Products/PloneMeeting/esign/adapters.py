# -*- coding: utf-8 -*-
#
# File: adapters.py
#

from collective.behavior.talcondition.utils import _evaluateExpression
from imio.esign.adapters import FilesBelongingToAGivenSession
from imio.helpers.content import uuidToObject
from plone import api
from Products.CMFPlone.utils import safe_unicode
from Products.PloneMeeting.adapters import CompoundCriterionBaseAdapter
from Products.PloneMeeting.browser.batchactions import get_pod_template_infos
from Products.PloneMeeting.browser.batchactions import pod_template_default
from Products.PloneMeeting.config import ESIGNWATCHERS_GROUP_SUFFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx
from zope.i18n import translate


class PMSignersAdapter(object):
    """Adapter to get signers of a given element (item, meeting or advice)."""

    def __init__(self, context):
        self.context = context
        self.request = context.REQUEST
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def _get_template_infos(self):
        """ """
        template, template_uid = None, None
        template_uid = self.request.form.get('template_uid') or \
            self.request.form.get('form.widgets.template_uid')
        if template_uid is not None:
            template = uuidToObject(template_uid)
        else:
            # try with pod_template
            pod_template_value = self.request.form.get('pod_template') or \
                self.request.form.get('form.widgets.pod_template') or \
                pod_template_default(self.context)
            if pod_template_value:
                template, output_format = get_pod_template_infos(pod_template_value, self.cfg)
                template_uid = template.UID()
        return template, template_uid

    def _get_base_extra_expr_ctx(self, pod_template=None):
        """Add "template_uid" to the context"""
        if pod_template is None:
            template, template_uid = self._get_template_infos()
            if not template or not template_uid:
                raise Exception("Could not get template_uid!")
        else:
            template, template_uid = pod_template, pod_template.UID()
        return _base_extra_expr_ctx(
            self.context,
            {'pod_template': template,
             'pod_template_uid': template_uid})

    def get_raw_signers(self, pod_template=None):
        """ """
        # will return a dict of signers infos with
        # key: 'signature_number'
        # value: 'held_position', 'function', 'name'
        extra_expr_ctx = self._get_base_extra_expr_ctx(pod_template=pod_template)
        signer_infos = _evaluateExpression(
            self.context,
            expression=extra_expr_ctx['pod_template'].esign_signers_expr or '',
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=False,
            raise_on_error=True) or {}
        return signer_infos

    def get_signers(self, pod_template=None):
        """Return the list of signers for the element.
           We use configuration field PODTemplate.esign_signers_expr."""
        signer_infos = self.get_raw_signers(pod_template=pod_template)
        # now we have to return a list of ordered signers
        # with 'userid', 'email', 'fullname' and 'position' all as text
        res = []
        # can not have several same userid or email
        userids = {}
        emails = {}
        for signature_number, signer_info in sorted(signer_infos.items()):
            userid = email = ''
            # a held_position to get a userid is mandatory
            if not signer_info["held_position"]:
                msg = translate(
                    msgid=u"No held position for signer number \"${signature_number}\" (${signer})!",
                    domain="PloneMeeting",
                    mapping={
                        'signature_number': signature_number,
                        'signer': u"{0} - {1}".format(
                           safe_unicode(signer_info['name']),
                           safe_unicode(signer_info['function']))},
                    context=self.request)
                raise ValueError(msg)
            person = signer_info["held_position"].get_person()
            userid = person.userid
            if userid is None:
                msg = translate(
                    msgid=u"No userid for person at \"${person_url}\"!",
                    domain="PloneMeeting",
                    mapping={'person_url': person.absolute_url()},
                    context=self.request)
                raise ValueError(msg)
            # can not have several same userid
            if userid in userids:
                msg = translate(
                    msgid=u"Same userid for signers \"${person1_url}\" and \"${person2_url}\"!",
                    domain="PloneMeeting",
                    mapping={'person1_url': userids[userid].absolute_url(),
                             'person2_url': person.absolute_url()},
                    context=self.request)
                raise ValueError(msg)
            user = api.user.get(userid)
            if user is None:
                msg = translate(
                    msgid=u"Could not find a user with userid \"${userid}\" defined on person at \"${person_url}\"!",
                    domain="PloneMeeting",
                    mapping={'userid': userid,
                             'person_url': person.absolute_url()},
                    context=self.request)
                raise ValueError(msg)
            email = user.getProperty("email")
            if not email:
                msg = translate(
                    msgid=u"User \"${userid}\" does not have an email address!",
                    domain="PloneMeeting",
                    mapping={'userid': userid},
                    context=self.request)
                raise ValueError(msg)
            email = email.strip()
            # can not have several same email
            if email in emails:
                msg = translate(
                    msgid=u"Same email address for users \"${userid1}\" and \"${userid2}\"!",
                    domain="PloneMeeting",
                    mapping={'userid1': emails[email].getId(),
                             'userid2': userid},
                    context=self.request)
                raise ValueError(msg)

            # save infos to manage duplicates of userid and email
            userids[userid] = person
            emails[email] = user

            # everything OK or raise_error=False, proceed
            data = {
                "signature_number": signature_number,
                "held_position": signer_info["held_position"],
                "name": signer_info["name"],
                "function": signer_info["shortfunction"],
                "userid": userid,
                "email": email,
            }
            res.append(data)
        if not res:
            msg = translate(
                msgid=u"Could not get any signers, please check configuration!",
                domain="PloneMeeting",
                context=self.request)
            raise ValueError(msg)
        return res

    def get_files_uids(self):
        """List of file uids.

        :return: list of uid of files
        """
        # must get here already converted file in pdf format...
        return []
        # for sub_content in self.context.values():
        #     if sub_content.portal_type in ("dmsommainfile", "dmsappendixfile"):
        #         yield sub_content.UID()

    def get_watchers(self):
        """
        MeetingManagers are watchers.
        """
        groupname = "{0}_{1}".format(
            self.cfg.getId(), ESIGNWATCHERS_GROUP_SUFFIX)
        watcher_users = api.user.get_users(groupname=groupname)
        watcher_emails = [
            user.getProperty("email").strip() for user in watcher_users]
        # manage duplicates
        return list(set(watcher_emails))

    def get_discriminators(self, annex, pod_template=None):
        """
        Discriminate based on MeetingConfig.eSignDiscriminatorsTALExpr.
        """
        extra_expr_ctx = self._get_base_extra_expr_ctx(pod_template=pod_template)
        extra_expr_ctx.update(
            {'obj': self.context,
             'annex': annex})
        # will return a list of strings
        discriminators = _evaluateExpression(
            self.context,
            expression=self.cfg.getESignDiscriminatorsTALExpr(),
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=False,
            raise_on_error=True) or []
        return u" - ".join(discriminators)

    def get_create_session_custom_data(self):
        """
        Store cfg_id in dict so we can use it in various places
        and we can have a per MeetingConfig behavior.
        """
        return {'cfg_id': self.cfg.getId()}


class ItemsBelongingToAGivenSession(CompoundCriterionBaseAdapter, FilesBelongingToAGivenSession):
    """ """

    @property
    def query_session_files(self):
        query = super(ItemsBelongingToAGivenSession, self).query_session_files
        query['portal_type'] = {'query': self.cfg.getItemTypeName()}
        return query

    query = query_session_files


class MeetingsBelongingToAGivenSession(CompoundCriterionBaseAdapter, FilesBelongingToAGivenSession):
    """ """

    @property
    def query_session_files(self):
        query = super(MeetingsBelongingToAGivenSession, self).query_session_files
        query['portal_type'] = {'query': self.cfg.getMeetingTypeName()}
        return query

    query = query_session_files
