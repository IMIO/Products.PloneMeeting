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

migrations.makeMigrator=makeMigrator

from Products.ZCTextIndex.ZCTextIndex import ZCTextIndex
from Products.PluginIndexes.common import safe_callable

# MonkeyPatch method to avoid bug discribed here https://dev.plone.org/ticket/13310 until a new Products.ZCTextIndex is released...
def index_object(self, documentId, obj, threshold=None):
    """Wrapper for  index_doc()  handling indexing of multiple attributes.

    Enter the document with the specified documentId in the index
    under the terms extracted from the indexed text attributes,
    each of which should yield either a string or a list of
    strings (Unicode or otherwise) to be passed to index_doc().
    """
    # XXX We currently ignore subtransaction threshold

    # needed for backward compatibility
    try: fields = self._indexed_attrs
    except: fields  = [ self._fieldname ]

    all_texts = []
    for attr in fields:
        text = getattr(obj, attr, None)
        if text is None:
            continue
        if safe_callable(text):
            text = text()
        if text is None:
            continue
        if text:
            if isinstance(text, (list, tuple, )):
                all_texts.extend(text)
            else:
                all_texts.append(text)

    # Check that we're sending only strings
    all_texts = filter(lambda text: isinstance(text, basestring), \
                       all_texts)

    return self.index.index_doc(documentId, all_texts)

ZCTextIndex.index_object=index_object