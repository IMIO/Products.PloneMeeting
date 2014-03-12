from Products.CMFCore.exportimport.workflow import WorkflowToolXMLAdapter


def _importNode(self, node):
    """Import the object from the DOM node.
    """
    # XXX --- Begin change by PM ---
    purge = self.environ.shouldPurge()
    if node.getAttribute('purge'):
        purge = self._convertToBoolean(node.getAttribute('purge'))
    if purge:
    #if self.environ.shouldPurge():
    # XXX --- End change by PM ---
        self._purgeProperties()
        self._purgeObjects()
        self._purgeChains()

    self._initProperties(node)
    self._initObjects(node)
    self._initChains(node)

    self._logger.info('Workflow tool imported.')

WorkflowToolXMLAdapter._importNode = _importNode
