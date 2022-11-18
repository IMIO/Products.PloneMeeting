# -*- coding: utf-8 -*-

from collective.ckeditor.browser.ckeditorview import CKeditorView


class PMCKeditorView(CKeditorView):
    """ """

    def getCK_plone_config(self):
        """XXX temporary fix to have a correct URL when @@cke-upload-image is called."""
        res = super(PMCKeditorView, self).getCK_plone_config()
        # include context absolute_url when calling @@cke-upload-image so it works
        # when editing an advice from a faceted dashboard
        if "/@@cke-upload-image" not in res:
            res = res.replace(
                "@@cke-upload-image",
                "%s/@@cke-upload-image" % self.context.absolute_url())
        return res
