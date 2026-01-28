# -*- coding: utf-8 -*-
#
# File: adapters.py
#

from collective.behavior.talcondition.utils import _evaluateExpression
from plone import api
from Products.PloneMeeting.config import MEETINGMANAGERS_GROUP_SUFFIX
from Products.PloneMeeting.utils import _base_extra_expr_ctx


class ItemSignersAdapter(object):
    """Adapter to get signers of a given item."""

    def __init__(self, context):
        self.context = context
        self.tool = api.portal.get_tool('portal_plonemeeting')
        self.cfg = self.tool.getMeetingConfig(self.context)

    def get_raw_signers(self):
        """ """
        extra_expr_ctx = _base_extra_expr_ctx(
            self.context, {'item': self.context, })
        # will return a dict of signers infos with
        # key: 'signature_number'
        # value: 'held_position', 'function', 'name' and 'userid'
        signer_infos = _evaluateExpression(
            self.context,
            expression=self.cfg.getItemESignSignersTALExpr(),
            roles_bypassing_expression=[],
            extra_expr_ctx=extra_expr_ctx,
            empty_expr_is_true=False,
            raise_on_error=True) or {}
        return signer_infos

    def get_signers(self):
        """Return the list of signers for the item.
           We use configuration field MeetingConfig.itemESignSignersTALExpr."""
        signer_infos = self.get_raw_signers()
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
                    "No held position for signer number {0} ({1})!".format(
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
                    "Same userid for several signers at {0} and {1}!".format(
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
                    "User \"{0}\"does not have an email address!".format(
                        user.getId()))
            email = email.strip()
            # can not have several same email
            if email in emails:
                raise ValueError("Same e-mail for several users at {0} and {1}!".format(
                    emails[email].getId(), user.getId()))

            # save infos to manage duplicates of userid and email
            userids[userid] = person
            emails[email] = user

            # everything OK or raise_error=False, proceed
            data = {
                "held_position": signer_info["held_position"],
                "name": signer_info["name"],
                "function": signer_info["function"],
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
        mmanagers_group_id = "{0}_{1}".format(
            self.cfg.getId(), MEETINGMANAGERS_GROUP_SUFFIX)
        watcher_users = api.user.get_users(groupname=mmanagers_group_id)
        watcher_emails = [
            user.getProperty("email").strip() for user in watcher_users]
        # manage duplicates
        return list(set(watcher_emails))
