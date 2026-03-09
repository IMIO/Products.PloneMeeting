# -*- coding: utf-8 -*-
#
# File: adapters.py
#

from collective.behavior.talcondition.utils import _evaluateExpression
from imio.helpers.content import uuidToObject
from plone import api
from Products.PloneMeeting.browser.batchactions import get_pod_template_infos
from Products.PloneMeeting.browser.batchactions import pod_template_default
from Products.PloneMeeting.config import ESIGNWATCHERS_GROUP_SUFFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx


class PMSignersAdapter(object):
    """Adapter to get signers of a given element (item, meeting or advice)."""

    def __init__(self, context):
        self.context = context
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def _get_template_infos(self):
        """ """
        template, template_uid = None, None
        template_uid = self.context.REQUEST.form.get('template_uid') or \
            self.context.REQUEST.form.get('form.widgets.template_uid')
        if template_uid is not None:
            template = uuidToObject(template_uid)
        else:
            # try with pod_template
            pod_template_value = self.context.REQUEST.form.get('pod_template') or \
                self.context.REQUEST.form.get('form.widgets.pod_template') or \
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
                raise Exception, "Could not get template_uid!"
        else:
            template, template_uid = pod_template, pod_template.UID()
        return _base_extra_expr_ctx(
            self.context,
            {'template': template,
             'template_uid': template_uid})

    def get_raw_signers(self, pod_template=None):
        """ """
        # will return a dict of signers infos with
        # key: 'signature_number'
        # value: 'held_position', 'function', 'name'
        extra_expr_ctx = self._get_base_extra_expr_ctx(pod_template=pod_template)
        signer_infos = _evaluateExpression(
            self.context,
            expression=extra_expr_ctx['template'].esign_signers_expr or '',
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=False,
            raise_on_error=True) or {}
        return signer_infos

    def get_signers(self, pod_template=None):
        """Return the list of signers for the element.
           We use configuration field MeetingConfig.eSignSignersTALExpr."""
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
                raise ValueError(
                    u"No held position for signer number \"{0}\" ({1})!".format(
                        signature_number,
                        u" - ".join(
                            (signer_info['name'], signer_info['function']))))
            person = signer_info["held_position"].get_person()
            userid = person.userid
            if userid is None:
                raise ValueError("No userid for person at {0}!".format(
                    person.absolute_url()))
            # can not have several same userid
            if userid in userids:
                raise ValueError(
                    "Same userid for signers \"{0}\" and \"{1}\"!".format(
                    userids[userid].absolute_url(), person.absolute_url()))
            user = api.user.get(userid)
            if user is None:
                raise ValueError(
                    "Could not find a user with userid \"{0}\" defined on "
                    "person at {1}!".format(
                        userid, person.absolute_url()
                ))
            email = user.getProperty("email")
            if not email:
                raise ValueError(
                    "User \"{0}\" does not have an email address!".format(
                        user.getId()))
            email = email.strip()
            # can not have several same email
            if email in emails:
                raise ValueError("Same email address for users \"{0}\" and \"{1}\"!".format(
                    emails[email].getId(), user.getId()))

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

    def get_discriminators(self, annex):
        """
        Discriminate based on MeetingConfig.eSignDiscriminatorsTALExpr.
        """
        extra_expr_ctx = self._get_base_extra_expr_ctx()
        extra_expr_ctx.update({'obj': self.context, 'annex': annex, })
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
