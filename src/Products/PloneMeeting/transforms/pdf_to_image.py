# -*- coding: utf-8 -*-
#
# File: Meeting.py
#
# Copyright (c) 2013 by PloneGov
# Generator: ArchGenXML Version 2.7
#            http://plone.org/products/archgenxml
#
# GNU General Public License (GPL)
#

__author__ = """Gaetan DELANNAY <gaetan.delannay@geezteem.com>, Gauthier BASTIEN
<g.bastien@imio.be>, Stephan GEULETTE <s.geulette@imio.be>"""
__docformat__ = 'plaintext'


from Products.PortalTransforms.interfaces import ITransform
from zope.interface import implements
from Products.PortalTransforms.libtransforms.commandtransform import (
    commandtransform, popentransform)
import os


class text_to_image(commandtransform):
    implements(ITransform)

    __name__ = "text_to_image"
    inputs = ('text/html',)
    output = 'text/plain'

    binaryName = "lynx"
    binaryArgs = "-dump"

    def __init__(self):
        commandtransform.__init__(self, binary=self.binaryName)

    def convert(self, data, cache, **kwargs):
        kwargs['filename'] = 'unknown.html'
        tmpdir, fullname = self.initialize_tmpdir(data, **kwargs)
        outname = "%s/%s.txt" % (tmpdir, orig_name)
        self.invokeCommand(tmpdir, fullname, outname)
        text = self.astext(outname)
        self.cleanDir(tmpdir)
        cache.setData(text)
        return cache

    def invokeCommand(self, tmpdir, inputname, outname):
        os.system('cd "%s" && %s %s "%s" 1>"%s" 2>/dev/null' % \
               (tmpdir, self.binary, self.binaryArgs, inputname, outname))

    def astext(self, outname):
        txtfile = open("%s" % (outname), 'r')
        txt = txtfile.read()
        txtfile.close()
        return txt


def register():
    return lynx_dump()
