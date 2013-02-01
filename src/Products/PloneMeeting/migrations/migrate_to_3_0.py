# ------------------------------------------------------------------------------
import logging
logger = logging.getLogger('PloneMeeting')
from Products.PloneMeeting.config import MEETING_GROUP_SUFFIXES
from Products.PloneMeeting.migrations import Migrator


# The migration class ----------------------------------------------------------
class Migrate_To_3_0(Migrator):
    def __init__(self, context):
        Migrator.__init__(self, context)

    def _configureCKeditor(self):
        '''Make sure CKeditor is the new default editor used by everyone...'''
        logger.info('Defining CKeditor as the new default editor for every users...')
        try:
            self.portal.cputils_configure_ckeditor(custom='plonemeeting')
        except AttributeError:
            raise Exception, "Could not configure CKeditor for every users, make sure Products.CPUtils is correctly "\
                                  "installed and that the cputils_configure_ckeditor method is available"

    def _updateRegistries(self):
        '''Make sure some elements are enabled and remove not found elements.'''
        # popuforms.js must be enabled in portal_javascript
        logger.info('Updating registries...')
        jstool = self.portal.portal_javascripts
        popupforms = jstool.getResource('popupforms.js')
        if popupforms:
            popupforms.setEnabled(True)
        # clean portal_javascripts
        for script in jstool.getResources():
            scriptId = script.getId()
            resourceExists = script.isExternal or self.portal.restrictedTraverse(scriptId, False) and True
            if not resourceExists:
                # we found a notFound resource, remove it
                logger.info('Removing %s from portal_javascripts' % scriptId)
                jstool.unregisterResource(scriptId)
        jstool.cookResources()
        # clean portal_css
        csstool = self.portal.portal_css
        for sheet in csstool.getResources():
            sheetId = sheet.getId()
            resourceExists = sheet.isExternal or self.portal.restrictedTraverse(sheetId, False) and True
            if not resourceExists:
                # we found a notFound resource, remove it
                logger.info('Removing %s from portal_css' % sheetId)
                csstool.unregisterResource(sheetId)
        csstool.cookResources()
        # clean portal_setup
        setuptool = self.portal.portal_setup
        for stepId in setuptool.getSortedImportSteps():
            stepMetadata = setuptool.getImportStepMetadata(stepId)
            # remove invalid steps
            if stepMetadata['invalid']:
                logger.info('Removing %s step from portal_setup' % stepId)
                setuptool._import_registry.unregisterStep(stepId)
        logger.info('Registries have been updated')

    def _patchFileSecurity(self):
        '''Plone 4 migration requires every ATFile object to be deletable by
           admin, because it converts it to a blob. From a PM point of view,
           it only concerns frozen documents.'''
        brains = self.portal.portal_catalog(meta_type='ATFile')
        if not brains: return
        logger.info('Security fix: scanning %s ATFile objects...' % len(brains))
        user = self.portal.portal_membership.getAuthenticatedMember()
        patched = 0
        for brain in brains:
            fileObject = brain.getObject()
            if user.has_permission('Delete objects', fileObject): continue
            fileObject._Delete_objects_Permission = \
                fileObject._Delete_objects_Permission + ('Manager',)
            patched += 1
        logger.info('Done (%d file(s) patched).' % patched)

    def _correctAnnexesMeetingFileTypes(self):
        '''While an item was cloned to another MeetingConfig, the annexes where copied too
           but the reference to the MeetingFileType was kept and so refering the other MeetingConfig
           where the MeetingFileTypes are stored...
           Scan every items and make sure the annex is defined in the correct MeetingConfig, aka the
           current MeetingConfig the annex is relying on.
           If an annexType does not exist in the new MeetingConfig, the default annexType (the
           first found) is used.'''
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            itemTypeName = cfg.getItemTypeName()
            brains = self.portal.portal_catalog(portal_type=itemTypeName)
            logger.info('Updating every annexes for %s %s objects...' % (len(brains), itemTypeName))
            updated = 0
            for brain in brains:
                changed = False
                item = brain.getObject()
                for annex in (item.getAnnexes() + item.getAnnexesDecision()):
                    annexUpdated = annex._updateMeetingFileType(cfg)
                    if annexUpdated:
                        changed = True
                if changed:
                    item.updateAnnexIndex()
                    updated += 1
            logger.info('Done (%d %s updated).' % (updated, itemTypeName))

    def _migrateMeetingFilesToBlobs(self):
        '''Migrate MeetingFiles to Blobs.'''
        # Call an helper method of plone.app.blob that does "inplace" migration
        # so existing 'file' are migrated to blob
        brains = self.portal.portal_catalog(meta_type='MeetingFile')
        # Some MeetingFiles to migrate?
        if not brains:
            logger.info('No MeetingFiles found.')
            return
        # Check if migration has already been launched
        aMeetingFile = brains[0].getObject()
        if aMeetingFile.getField('file').get(aMeetingFile).__module__ == 'plone.app.blob.field':
            logger.info('MeetingFiles already migrated to blobs.')
            return

        logger.info('Migrating %s MeetingFile objects...' % len(brains))
        from plone.app.blob.migrations import migrate
        migrate(self.portal, 'MeetingFile')
        # Title of the MeetingFiles are lost (???) retrieve it from annexIndex
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        for brain in brains:
            item = brain.getObject()
            annexes = item.getAnnexes() + item.getAnnexesDecision()
            if not annexes:
                continue
            title_to_uid_mapping = {}
            for annexInfo in item.annexIndex:
                title_to_uid_mapping[annexInfo['uid']] = annexInfo['Title']
            for annex in annexes:
                if not annex.Title():
                    annex.setTitle(title_to_uid_mapping[annex.UID()])
                    annex.reindexObject()
        logger.info("MeetingFiles have been migrated to Blobs.")

    def _migrateFCKTemplates(self):
        '''We do not use CPFCKTemplates anymore (as it does not work with collective.ckeditor for now),
           we use PloneMeeting own template management.'''
        def _findUsingGroups(fcktemplate):
            '''Find groups that were using the fcktemplate.  Check local_roles defined on the fcktemplate
               and on his parent.'''
            localRoles = fcktemplate.get_local_roles() + fcktemplate.getParentNode().get_local_roles()
            res = []
            for localRole in localRoles:
                for suffix in MEETING_GROUP_SUFFIXES:
                    if localRole[0].endswith('_%s' % suffix):
                        # we certainly found a Plone group linked to a PloneMeeting group
                        # get the corresponding PloneMeeting group
                        pmGroup = self.portal.portal_plonemeeting.getMeetingGroup(localRole[0])
                        if pmGroup and pmGroup.getId() not in res:
                            res.append(pmGroup.getId())
            return res

        brains = self.portal.portal_catalog(meta_type='FCKTemplate')
        logger.info('Migrating FCKTemplates to PloneMeeting item templates.  Migrating %s FCKTemplate objects...' % len(brains))
        # create the template in every active MeetingConfig as FCKTemplates where available for every MeetingConfigs...
        for cfg in self.portal.portal_plonemeeting.getActiveConfigs():
            itemTemplatesFolder = cfg.recurringitems
            itemType = cfg.getItemTypeName()
            for brain in brains:
                fcktemplate = brain.getObject()
                newId = fcktemplate.generateUniqueId()
                data = {'title': fcktemplate.Title(),
                        'decision': fcktemplate.getText(),
                        'usages': ('as_template_item',)}
                newObjId = itemTemplatesFolder.invokeFactory(itemType, newId, **data)
                newObj = getattr(itemTemplatesFolder, newObjId)
                # try to automatically specify templateUsingGroups
                usingGroups = _findUsingGroups(fcktemplate)
                newObj.setTemplateUsingGroups(usingGroups)
                newObj.processForm()
                newObj._renameAfterCreation()
                newObj.reindexObject()
        logger.info("FCKTemplates have been migrated to MeetingItems with usage 'as_template_item'.")

    def _updateAdvices(self):
        '''We use a new role to manage advices, 'MeetingPowerObserverLocal' instead of
           'MeetingObserverLocal', we need to update every advices for this to
           be taken into account.'''
        brains = self.portal.portal_catalog(meta_type='MeetingItem')
        logger.info('Updating every advices for %s MeetingItem objects...' % len(brains))
        for brain in brains:
            obj = brain.getObject()
            # Reinitialize local roles
            obj.updateLocalRoles()
            # Update security as local_roles are modified by updateAdvices
            obj.reindexObject(idxs=['allowedRolesAndUsers',])
        logger.info('MeetingItems advices have been updated.')

    def _migrateXhtmlTransformFieldsValues(self):
        '''Migrate every MeetingConfig.xhtmlTransformFields because before the value was a
           fieldName of the MeetingItem but now it is a value like "Item.myFieldName" or "Meeting.myFieldName"
           because wecan apply transformations on Meeting fields too.'''
        logger.info('Updating every cfg.XhtmlTransformFields values...')
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            namesToMigrate = [name for name in cfg.getXhtmlTransformFields() if not name in cfg.listRichTextFields()]
            if not namesToMigrate:
                continue
            res = []
            # before there was only fields about the Item
            for name in namesToMigrate:
                logger.info('Updated %s to MeetingItem.%s' % (name, name))
                res.append('MeetingItem.%s' % name)
            cfg.setXhtmlTransformFields(res)
        logger.info('Done.')

    def _findPublishedMeetings(self):
        '''Returns the list of uids of the Meetings that are in state 'published'
           corresponding to the old state added by the 'add_published_state' wfAdaptation.'''
        logger.info('Finding meetings to migrate regarding \'add_published_state\' wfAdaptation')
        wft = self.portal.portal_workflow
        uids = []
        for cfg in self.portal.portal_plonemeeting.objectValues('MeetingConfig'):
            # only consider cfg having the 'add_published_state'
            if not 'add_published_state' in cfg.getWorkflowAdaptations():
                logger.info("The 'add_published_state' wfAdaptation is not selected for the '%s' meetingConfig" % cfg.getId())
                continue
            # check also if the linked wf has not already been migrated
            wf = getattr(wft, cfg.getMeetingWorkflow(), None)
            if not wf:
                raise Exception, "The wf '%s' defined on the '%s' meetingConfig does not exist?!" \
                                 % (cfg.getMeetingWorkflow(), cfg.getId())
            if 'decisions_published' in wf.transitions:
                logger.info("The wf '%s' is already migrated (already contains the 'decisions_published' state) for the '%s' meetingConfig" % (wf.getId(), cfg.getId()))
            # if the cfg contains the wfAdaptation and the wf is not already migrated, proceed
            brains = self.portal.portal_catalog(portal_type=cfg.getMeetingTypeName(), review_state='published')
            if not brains:
                logger.info("No meeting to migrate in meetingConfig '%s'" % cfg.getId())
            else:
                # bypass guards for Manager
                wf.manager_bypass=1
                # deactivate mail notifications
                oldMailMode = cfg.getMailMode()
                cfg.setMailMode('deactivated')
                # set some value in the request that will be used by the triggerTransition method here under
                self.portal.REQUEST.set('transition', 'backToDecided')
                self.portal.REQUEST.set('comment', 'Set back to \'decided\' during migration to PM3.0 because actual state \'published\' does not exist anymore.')
                for brain in brains:
                    obj = brain.getObject()
                    uid = obj.UID()
                    uids.append(uid)
                    # use our tool to trigger transition so we can easily add a comment
                    self.portal.REQUEST.set('objectUid', uid)
                    self.portal.portal_plonemeeting.triggerTransition()
                    logger.info("Set back meeting at '%s' to 'decided' for migration purpose" % '/'.join(obj.getPhysicalPath()))
                logger.info("Meetings that were set back to 'decided' will be migrated after reinstall.")
                # back to old application state
                self.portal.REQUEST.set('transition', '')
                self.portal.REQUEST.set('comment', '')
                self.portal.REQUEST.set('objectUid', '')
                wf.manager_bypass=1
                cfg.setMailMode(oldMailMode)
        return uids

    def _migrateStatePublishedToDecisionsPublished(self, uids):
        '''Migrate meetings having passed uids to the 'decisions_publihsed' state.
           These are meetings that where in no more existing state 'published', set back to 'decided'
           that we will now set to 'decisions_published'.'''
        logger.info('Migrating given \'%d\' meeting(s) to the \'decisions_published \' state' % len(uids))
        if not uids:
            return
        wft = self.portal.portal_workflow
        tool = self.portal.portal_plonemeeting
        # set some value in the request that will be used by the triggerTransition method here under
        self.portal.REQUEST.set('transition', 'publish_decisions')
        self.portal.REQUEST.set('comment', 'Set to \'decisions_published\' during migration to PM3.0 because old state \'published\' does not exist anymore.')
        for uid in uids:
            brains = self.portal.uid_catalog(UID=uid)
            if not brains:
                raise Exception, "The meeting having uid '%s' was not found in 'uid_catalog'!" % uid
            obj = brains[0].getObject()
            cfg = tool.getMeetingConfig(obj)
            wf = getattr(wft, cfg.getMeetingWorkflow(), None)
            # bypass guards for Manager
            wf.manager_bypass=1
            # deactivate mail notifications
            oldMailMode = cfg.getMailMode()
            cfg.setMailMode('deactivated')
            self.portal.REQUEST.set('objectUid', uid)
            self.portal.portal_plonemeeting.triggerTransition()
            # back to old application state
            self.portal.REQUEST.set('transition', '')
            self.portal.REQUEST.set('comment', '')
            self.portal.REQUEST.set('objectUid', '')
            wf.manager_bypass=1
            cfg.setMailMode(oldMailMode)
        logger.info('\'%d\' meeting(s) was(were) migrated to the \'decisions_published \' state' % len(uids))


    def run(self):
        logger.info('Migrating to PloneMeeting 3.0...')
        # the Meeting 'published' state has become 'decisions_published' now, so :
        # - find Meetings in 'published' in MeetingConfigs where 'add_published_state' wfAdaptation is activbe
        # - set them back to 'decided'
        # - returns the list of modified uids
        # - reinstall
        # - set meetings (returned uids) to 'decisions_published' state
        uids = self._findPublishedMeetings()
        self.reinstall(profiles=[u'profile-Products.PloneMeeting:default',
                                 u'profile-plonetheme.imioapps:default',
                                 u'profile-plonetheme.imioapps:plonemeetingskin',])
        self._migrateStatePublishedToDecisionsPublished(uids)
        
        # now continue with other migrations
        self._configureCKeditor()
        self._updateRegistries()
        self._patchFileSecurity()
        self._correctAnnexesMeetingFileTypes()
        self._migrateMeetingFilesToBlobs()
        self._updateAdvices()
        self._migrateXhtmlTransformFieldsValues()
        self._migrateFCKTemplates()
        # refresh portal_catalog so getDate metadata is updated
        self.refreshDatabase(catalogs=True, workflows=False)
        self.finish()

# The migration function -------------------------------------------------------
def migrate(context):
    '''This migration function:

       1) Patches security of File objects;
       2) Migrate MeetingFiles to Blobs.
    '''
    Migrate_To_3_0(context).run()
# ------------------------------------------------------------------------------
