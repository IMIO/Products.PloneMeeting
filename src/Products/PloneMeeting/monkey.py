from plone.app.blob import migrations
from Products.contentmigration.migrator import BaseInlineMigrator as InlineMigrator
from Products.Archetypes.interfaces import ISchema
from plone.app.blob.interfaces import IBlobField


# MonkeyPatch method to use .Schema() instead of .schema.  See below...
def makeMigrator(context, portal_type, meta_type=None):
    """ generate a migrator for the given at-based portal type """
    if meta_type is None:
        meta_type = portal_type

    class BlobMigrator(InlineMigrator):
        src_portal_type = portal_type
        src_meta_type = meta_type
        dst_portal_type = portal_type
        dst_meta_type = meta_type
        fields = []

        def getFields(self, obj):
            if not self.fields:
                # get the blob fields to migrate from the first object
                for field in ISchema(obj).fields():
                    if IBlobField.providedBy(field):
                        self.fields.append(field.getName())
            return self.fields

        @property
        def fields_map(self):
            fields = self.getFields(None)
            return dict([(name, None) for name in fields])

        def migrate_data(self):
            fields = self.getFields(self.obj)
            for name in fields:
                #XXX changed for PloneMeeting
                #use .Schema() instead of .schema
                #oldfield = self.obj.schema[name]
                oldfield = self.obj.Schema()[name]
                if hasattr(oldfield, 'removeScales'):
                    # clean up old image scales
                    oldfield.removeScales(self.obj)
                value = oldfield.get(self.obj)
                field = self.obj.getField(name)
                field.getMutator(self.obj)(value)

        def last_migrate_reindex(self):
            # prevent update of modification date during reindexing without
            # copying code from `CatalogMultiplex` (which should go anyway)
            od = self.obj.__dict__
            assert 'notifyModified' not in od
            od['notifyModified'] = lambda *args: None
            self.obj.reindexObject()
            del od['notifyModified']

    return BlobMigrator

migrations.makeMigrator = makeMigrator


from Products.Archetypes import BaseObject
from zope import event
from Products.Archetypes.event import ObjectInitializedEvent
from Products.Archetypes.event import ObjectEditedEvent


# MonkeyPatch BaseObject.processForm to call unmarkCreationFlag after renaming object
def processForm(self, data=1, metadata=0, REQUEST=None, values=None):
    """Processes the schema looking for data in the form.
    """
    is_new_object = self.checkCreationFlag()
    self._processForm(data=data, metadata=metadata,
                      REQUEST=REQUEST, values=values)

    if self._at_rename_after_creation and is_new_object:
        self._renameAfterCreation(check_auto_id=True)

    # XXX changed for PloneMeeting
    # self.unmarkCreationFlag() is called after "if self._at_rename..." here above
    # See https://github.com/plone/Products.Archetypes/pull/19
    self.unmarkCreationFlag()

    # Post create/edit hooks
    if is_new_object:
        event.notify(ObjectInitializedEvent(self))
        self.at_post_create_script()
    else:
        event.notify(ObjectEditedEvent(self))
        self.at_post_edit_script()

BaseObject.processForm = processForm
