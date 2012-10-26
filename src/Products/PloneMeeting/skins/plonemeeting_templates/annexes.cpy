## Controller Python Script "annexes.cpy"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind state=state
##bind subpath=traverse_subpath
##parameters=annex_type, annex_title, annex_file, decisionRelated
##title=Creates a new annex and appends it to the current item

from DateTime import DateTime
rq = context.REQUEST

# Get current meeting config
meetingConfig = container.portal_plonemeeting.getMeetingConfig(context)
meetingFileType = getattr(meetingConfig.meetingfiletypes, annex_type)

# Try to create, within the item (which is folderish), an object whose id
# is derived from the fileName of the file to upload. If this id already exists
# or is blacklisted (for more info about it see
# MeetingItem.at_post_create_script), we prepend a number to it.
i = 0
idMayBeUsed = False
idCandidate = annex_file.filename

# IE bug workaround: the filename in IE returns the full file path...
# We split the '\' and keep the last part...
idCandidate = idCandidate.split('\\')[-1]

# Split leading underscore(s); else, Plone argues that you do not have the
# rights to create the annex
idCandidate = idCandidate.lstrip('_')

# Normalize idCandidate
idCandidate = context.plone_utils.normalizeString(idCandidate)

while not idMayBeUsed:
    i += 1
    if not context.isValidAnnexId(idCandidate):
        # We need to find another name (prepend a number)
        elems = idCandidate.rsplit('.', 1)
        baseName = elems[0]
        if len(elems) == 1:
            ext = ''
        else:
            ext = '.%s' % elems[1]
        idCandidate = '%s%d%s' % (baseName, i, ext)
    else:
        # Ok idCandidate is good!
        idMayBeUsed = True

context.addAnnex(idCandidate, annex_type, annex_title, annex_file,
                 decisionRelated, meetingFileType)

state.set(status='success', portal_status_message="Changes made.")
rq.set('annex_type', None)
rq.set('annex_title', None)
return state
