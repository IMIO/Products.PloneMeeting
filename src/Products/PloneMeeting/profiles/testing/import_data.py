# -*- coding: utf-8 -*-
#
# GNU General Public License (GPL)
#

from copy import deepcopy
from Products.PloneMeeting.config import NO_TRIGGER_WF_TRANSITION_UNTIL
from Products.PloneMeeting.profiles import AnnexTypeDescriptor
from Products.PloneMeeting.profiles import CategoryDescriptor
from Products.PloneMeeting.profiles import HeldPositionDescriptor
from Products.PloneMeeting.profiles import ItemAnnexSubTypeDescriptor
from Products.PloneMeeting.profiles import ItemAnnexTypeDescriptor
from Products.PloneMeeting.profiles import ItemTemplateDescriptor
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.profiles import OrgDescriptor
from Products.PloneMeeting.profiles import PersonDescriptor
from Products.PloneMeeting.profiles import PloneGroupDescriptor
from Products.PloneMeeting.profiles import PloneMeetingConfiguration
from Products.PloneMeeting.profiles import PodTemplateDescriptor
from Products.PloneMeeting.profiles import RecurringItemDescriptor
from Products.PloneMeeting.profiles import StyleTemplateDescriptor
from Products.PloneMeeting.profiles import UserDescriptor


# First meeting type: a fictitious PloneGov assembly ---------------------------

# Categories
deployment = CategoryDescriptor('deployment', 'Deployment topics', category_id='deployment')
maintenance = CategoryDescriptor('maintenance', 'Maintenance topics', category_id='maintenance')
development = CategoryDescriptor('development', 'Development topics', category_id='development')
events = CategoryDescriptor('events', 'Events', category_id='events')
research = CategoryDescriptor('research', 'Research topics', category_id='research')
projects = CategoryDescriptor('projects', 'Projects', category_id='projects')
# A vintage category
marketing = CategoryDescriptor('marketing', 'Marketing', category_id='marketing', enabled=False)
# usingGroups category
subproducts = CategoryDescriptor('subproducts', 'Subproducts wishes',
                                 category_id='subproducts', using_groups=('vendors',))

# Classifiers
classifier1 = CategoryDescriptor('classifier1', 'Classifier 1')
classifier2 = CategoryDescriptor('classifier2', 'Classifier 2')
classifier3 = CategoryDescriptor('classifier3', 'Classifier 3')

# Meeting categories
mcategory1 = CategoryDescriptor('mcategory1', 'Meeting category 1', category_id='MC1')
mcategory2 = CategoryDescriptor('mcategory2', 'Meeting category 2', category_id='MC2')
mcategory3 = CategoryDescriptor('mcategory3', 'Meeting category 3')

# Annex types
overheadAnalysisSubtype = ItemAnnexSubTypeDescriptor(
    'overhead-analysis-sub-annex',
    'Overhead analysis sub annex',
    other_mc_correspondences=(
        'cfg2_-_annexes_types_-_item_annexes_-_budget-analysis', ))

overheadAnalysis = ItemAnnexTypeDescriptor(
    'overhead-analysis', 'Administrative overhead analysis',
    u'overheadAnalysis.png',
    subTypes=[overheadAnalysisSubtype],
    other_mc_correspondences=(
        'cfg2_-_annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex', ))

financialAnalysisSubAnnex = ItemAnnexSubTypeDescriptor(
    'financial-analysis-sub-annex',
    'Financial analysis sub annex')

financialAnalysis = ItemAnnexTypeDescriptor(
    'financial-analysis', 'Financial analysis', u'financialAnalysis.png',
    u'Predefined title for financial analysis', subTypes=[financialAnalysisSubAnnex])

legalAnalysis = ItemAnnexTypeDescriptor(
    'legal-analysis', 'Legal analysis', u'legalAnalysis.png')

budgetAnalysisCfg2Subtype = ItemAnnexSubTypeDescriptor(
    'budget-analysis-sub-annex',
    'Budget analysis sub annex')

budgetAnalysisCfg2 = ItemAnnexTypeDescriptor(
    'budget-analysis', 'Budget analysis', u'budgetAnalysis.png',
    subTypes=[budgetAnalysisCfg2Subtype])

budgetAnalysisCfg1Subtype = ItemAnnexSubTypeDescriptor(
    'budget-analysis-sub-annex',
    'Budget analysis sub annex',
    other_mc_correspondences=(
        'cfg2_-_annexes_types_-_item_annexes_-_budget-analysis_-_budget-analysis-sub-annex', ))

budgetAnalysisCfg1 = ItemAnnexTypeDescriptor(
    'budget-analysis', 'Budget analysis', u'budgetAnalysis.png',
    subTypes=[budgetAnalysisCfg1Subtype],
    other_mc_correspondences=('cfg2_-_annexes_types_-_item_annexes_-_budget-analysis', ))

itemAnnex = ItemAnnexTypeDescriptor(
    'item-annex', 'Other annex(es)', u'itemAnnex.png')

previewAnnex = ItemAnnexTypeDescriptor(
    'preview-annex', 'Preview annex', u'itemAnnex.png', show_preview=1, only_pdf=True)

previewHideDownloadAnnex = ItemAnnexTypeDescriptor(
    'preview-hide-download-annex', 'Preview hide download annex', u'itemAnnex.png', show_preview=2)

# Item decision annex
decisionAnnex = ItemAnnexTypeDescriptor(
    'decision-annex', 'Decision annex(es)', u'decisionAnnex.png', relatedTo='item_decision')
# A vintage annex type
marketingAnalysis = ItemAnnexTypeDescriptor(
    'marketing-annex', 'Marketing annex(es)', u'legalAnalysis.png', relatedTo='item_decision',
    enabled=False)
# Advice annex types
adviceAnnex = AnnexTypeDescriptor(
    'advice-annex', 'Advice annex(es)', u'itemAnnex.png', relatedTo='advice')
adviceLegalAnalysis = AnnexTypeDescriptor(
    'advice-legal-analysis', 'Advice legal analysis', u'legalAnalysis.png', relatedTo='advice')
# Meeting annex types
meetingAnnex = AnnexTypeDescriptor(
    'meeting-annex', 'Meeting annex(es)', u'itemAnnex.png', relatedTo='meeting')

# Style Template ---------------------------------------------------------------
stylesTemplate1 = StyleTemplateDescriptor('styles1', 'Default Styles')
stylesTemplate1.odt_file = 'styles1.odt'

stylesTemplate2 = StyleTemplateDescriptor('styles2', 'Extra Styles')
stylesTemplate2.odt_file = 'styles2.odt'
# Pod templates
agendaTemplate = PodTemplateDescriptor('agendaTemplate', 'Meeting agenda')
agendaTemplate.odt_file = 'Agenda.odt'
agendaTemplate.pod_portal_types = ['Meeting']
agendaTemplate.style_template = ['styles1']

decisionsTemplate = PodTemplateDescriptor('decisionsTemplate',
                                          'Meeting decisions')
decisionsTemplate.odt_file = 'Decisions.odt'
decisionsTemplate.pod_portal_types = ['Meeting']
decisionsTemplate.tal_condition = u'python:here.adapted().is_decided()'
decisionsTemplate.roles_bypassing_talcondition = set(['Manager'])
decisionsTemplate.style_template = ['styles1']

itemTemplate = PodTemplateDescriptor('itemTemplate', 'Meeting item')
itemTemplate.is_reusable = True
itemTemplate.odt_file = 'Item.odt'
itemTemplate.pod_portal_types = ['MeetingItem']
itemTemplate.style_template = ['styles2']

allItemTemplate = PodTemplateDescriptor('allItemTemplate', 'All Meeting item')
allItemTemplate.odt_file = 'all_item.odt'
allItemTemplate.pod_portal_types = ['Meeting']
allItemTemplate.merge_templates = [{'pod_context_name': u'item', 'do_rendering': False, 'template': 'itemTemplate'}]

dashboardTemplate = PodTemplateDescriptor('dashboardTemplate', 'Dashboard summary', dashboard=True)
dashboardTemplate.odt_file = 'Dashboard.odt'
dashboardTemplate.tal_condition = u'python: context.absolute_url().endswith("/searches_items")'

# Test users and groups
siteadmin = UserDescriptor('siteadmin', ['Manager'], email="siteadmin@plonemeeting.org", fullname='Site administrator')
pmManager = UserDescriptor('pmManager', [], email="pmmanager@plonemeeting.org", fullname='M. PMManager')
pmManager2 = UserDescriptor('pmManager2', [], email="pmmanager2@plonemeeting.org", fullname='M. PMManager2')
pmCreator1 = UserDescriptor('pmCreator1', [], email="pmcreator1@plonemeeting.org", fullname='M. PMCreator One')
pmCreator1b = UserDescriptor('pmCreator1b', [], email="pmcreator1b@plonemeeting.org", fullname='M. PMCreator One bee')
pmObserver1 = UserDescriptor('pmObserver1', [], email="pmobserver1@plonemeeting.org", fullname='M. PMObserver One')
pmReviewer1 = UserDescriptor('pmReviewer1', [], email="pmreviewer1@plonemeeting.org", fullname='M. PMReviewer One')
pmReviewerLevel1 = UserDescriptor('pmReviewerLevel1', [],
                                  email="pmreviewerlevel1@plonemeeting.org", fullname='M. PMReviewer Level One')
pmCreator2 = UserDescriptor('pmCreator2', [], email="pmcreator2@plonemeeting.org", fullname='M. PMCreator Two')
pmReviewer2 = UserDescriptor('pmReviewer2', [], email="pmreviewer2@plonemeeting.org", fullname='M. PMReviewer Two')
pmReviewerLevel2 = UserDescriptor('pmReviewerLevel2', [],
                                  email="pmreviewerlevel2@plonemeeting.org", fullname='M. PMReviewer Level Two')
pmObserver2 = UserDescriptor('pmObserver2', [], email="pmobserver2@plonemeeting.org", fullname='M. PMObserver Two')
pmAdviser1 = UserDescriptor('pmAdviser1', [], email="pmadviser1@plonemeeting.org", fullname='M. PMAdviser One (Hé)')
voter1 = UserDescriptor('voter1', [], email="voter1@plonemeeting.org", fullname='M. Voter One')
voter2 = UserDescriptor('voter2', [], email="voter2@plonemeeting.org", fullname='M. Voter Two')
powerobserver1 = UserDescriptor('powerobserver1',
                                [],
                                email="powerobserver1@plonemeeting.org",
                                fullname='M. Power Observer1')
cfg1_powerobservers = PloneGroupDescriptor('cfg1_powerobservers', 'cfg1_powerobservers', [])
powerobserver1.ploneGroups = [cfg1_powerobservers]
powerobserver2 = UserDescriptor('powerobserver2',
                                [],
                                email="powerobserver2@plonemeeting.org",
                                fullname='M. Power Observer2')
cfg2_powerobservers = PloneGroupDescriptor('cfg2_powerobservers', 'cfg2_powerobservers', [])
powerobserver2.ploneGroups = [cfg2_powerobservers]
restrictedpowerobserver1 = UserDescriptor('restrictedpowerobserver1',
                                          [],
                                          email="restrictedpowerobserver1@plonemeeting.org",
                                          fullname='M. Restricted Power Observer 1')
cfg1_restrictedpowerobservers = PloneGroupDescriptor('cfg1_restrictedpowerobservers',
                                                     'cfg1_restrictedpowerobservers',
                                                     [])
restrictedpowerobserver1.ploneGroups = [cfg1_restrictedpowerobservers]
restrictedpowerobserver2 = UserDescriptor('restrictedpowerobserver2',
                                          [],
                                          email="restrictedpowerobserver2@plonemeeting.org",
                                          fullname='M. Restricted Power Observer 2')
cfg2_restrictedpowerobservers = PloneGroupDescriptor('cfg2_restrictedpowerobservers',
                                                     'cfg2_restrictedpowerobservers',
                                                     [])
restrictedpowerobserver2.ploneGroups = [cfg2_restrictedpowerobservers]
# budget impact editors
budgetimpacteditor = UserDescriptor('budgetimpacteditor',
                                    [],
                                    email="budgetimpacteditor@plonemeeting.org",
                                    fullname='M. Budget Impact Editor')
cfg1_budgetimpacteditors = PloneGroupDescriptor('cfg1_budgetimpacteditors', 'cfg1_budgetimpacteditors', [])
budgetimpacteditor.ploneGroups = [cfg1_budgetimpacteditors,
                                  cfg1_powerobservers]
# item templates manager
templatemanager1 = UserDescriptor('templatemanager1',
                                  [],
                                  email="templatemanager1@plonemeeting.org",
                                  fullname='M. Template Manager1')
cfg1_templatemanagers = PloneGroupDescriptor('cfg1_itemtemplatesmanagers',
                                             'cfg1_itemtemplatesmanagers',
                                             [])
templatemanager1.ploneGroups = [cfg1_templatemanagers]

developers = OrgDescriptor('developers', 'Developers', u'Devel')
developers.creators.append(pmCreator1)
developers.creators.append(pmCreator1b)
developers.creators.append(pmManager)
developers.prereviewers.append(pmReviewerLevel1)
developers.reviewers.append(pmReviewer1)
developers.reviewers.append(pmReviewerLevel2)
developers.reviewers.append(pmManager)
developers.observers.append(pmObserver1)
developers.observers.append(pmReviewer1)
developers.observers.append(pmManager)
developers.advisers.append(pmAdviser1)
developers.advisers.append(pmManager)

vendors = OrgDescriptor('vendors', 'Vendors', u'Devil')
vendors.creators.append(pmCreator2)
vendors.prereviewers.append(pmReviewer2)
vendors.reviewers.append(pmReviewer2)
vendors.observers.append(pmReviewer2)
vendors.observers.append(pmObserver2)
vendors.advisers.append(pmReviewer2)
vendors.advisers.append(pmManager)

# Do voters able to see items to vote for
# developers.observers.append(voter1)
# developers.observers.append(voter2)
# vendors.observers.append(voter1)
# vendors.observers.append(voter2)

# Add a vintage group
endUsers = OrgDescriptor('endUsers', 'End users', u'EndUsers', active=False)

# Add 2 organizations outside "My org"
org_outside1 = OrgDescriptor('orgOutside1', 'Org outside 1', u'OrgOutside1', active=False)
org_outside1.parent_path = ".."
org_outside2 = OrgDescriptor('orgOutside2', 'Org outside 2', u'OrgOutside2', active=False)
org_outside2.parent_path = ".."

# Add an external user
cadranel = UserDescriptor('cadranel', [], fullname='M. Benjamin Cadranel')

# Recurring items
recItem1 = RecurringItemDescriptor(
    'recItem1',
    'Recurring item #1',
    proposingGroup='developers',
    description='<p>This is the first recurring item.</p>',
    decision='<p>First recurring item approved</p>')
recItem2 = RecurringItemDescriptor(
    'recItem2',
    'Recurring item #2',
    proposingGroup='developers',
    description='<p>This is the second recurring item.</p>',
    decision='<p>Second recurring item approved</p>')
# item templates
template1 = ItemTemplateDescriptor(
    'template1', 'Template1',
    '', category='development', description='<p>This is template1.</p>',
    decision='<p>Template1 decision</p>')
template2 = ItemTemplateDescriptor(
    'template2', 'Template2',
    'vendors', category='development', description='<p>This is template2.</p>',
    decision='<p>Template1 decision</p>', templateUsingGroups=['vendors'])

# Meeting configuration
# PloneMeeting assembly
meetingPma = MeetingConfigDescriptor(
    'plonemeeting-assembly', 'PloneMeeting assembly', 'PloneMeeting assembly', isDefault=True)
meetingPma.meetingManagers = ['pmManager']
meetingPma.shortName = 'Pma'
meetingPma.assembly = 'Gauthier Bastien, Gilles Demaret, Kilian Soree, ' \
                      'Arnaud Hubaux, Jean-Michel Abe, Stephan Geulette, ' \
                      'Godefroid Chapelle, Gaetan Deberdt, Gaetan Delannay'
meetingPma.signatures = 'Bill Gates, Steve Jobs'
meetingPma.categories = [development, research, events]
meetingPma.classifiers = [classifier1, classifier2, classifier3]
meetingPma.meetingcategories = [mcategory1, mcategory2, mcategory3]
meetingPma.annexTypes = [financialAnalysis, budgetAnalysisCfg1, overheadAnalysis,
                         itemAnnex, previewAnnex, previewHideDownloadAnnex,
                         decisionAnnex, marketingAnalysis,
                         adviceAnnex, adviceLegalAnalysis, meetingAnnex]
meetingPma.usedItemAttributes = ('description', 'toDiscuss', 'itemTags', 'itemIsSigned',)
meetingPma.usedMeetingAttributes = ('assembly', 'assembly_excused', 'assembly_absents',
                                    'assembly_guests', 'signatures', 'place',)
meetingPma.maxShownListings = '100'
meetingPma.workflowAdaptations = ['delayed']
meetingPma.itemPositiveDecidedStates = ['accepted']
meetingPma.onMeetingTransitionItemActionToExecute = (
    {'meeting_transition': 'freeze',
     'item_action': 'itemfreeze',
     'tal_expression': ''},

    {'meeting_transition': 'publish',
     'item_action': 'itemfreeze',
     'tal_expression': ''},
    {'meeting_transition': 'publish',
     'item_action': 'itempublish',
     'tal_expression': ''},

    {'meeting_transition': 'decide',
     'item_action': 'itemfreeze',
     'tal_expression': ''},
    {'meeting_transition': 'decide',
     'item_action': 'itempublish',
     'tal_expression': ''},

    {'meeting_transition': 'publish_decisions',
     'item_action': 'itemfreeze',
     'tal_expression': ''},
    {'meeting_transition': 'publish_decisions',
     'item_action': 'itempublish',
     'tal_expression': ''},
    {'meeting_transition': 'publish_decisions',
     'item_action': 'accept',
     'tal_expression': ''},

    {'meeting_transition': 'close',
     'item_action': 'itemfreeze',
     'tal_expression': ''},
    {'meeting_transition': 'close',
     'item_action': 'itempublish',
     'tal_expression': ''},
    {'meeting_transition': 'close',
     'item_action': 'accept',
     'tal_expression': ''},

    {'meeting_transition': 'backToCreated',
     'item_action': 'backToItemPublished',
     'tal_expression': ''},
    {'meeting_transition': 'backToCreated',
     'item_action': 'backToItemFrozen',
     'tal_expression': ''},
    {'meeting_transition': 'backToCreated',
     'item_action': 'backToPresented',
     'tal_expression': ''},)

meetingPma.insertingMethodsOnAddItem = ({'insertingMethod': 'on_proposing_groups', 'reverse': '0'}, )
meetingPma.defaultLabels = [
    {'color': 'blue', 'by_user': False, 'title': 'Label'},
    {'color': 'yellow', 'by_user': True, 'title': 'Personal label'},
    {'color': 'green', 'by_user': True, 'title': 'Lu'},
    {'color': 'yellow', 'by_user': True, 'title': 'Suivi'}]
meetingPma.committees = (
    {'acronym': 'Comm1',
     'auto_from': [],
     'default_assembly': '',
     'default_attendees': [],
     'default_place': 'Place 1',
     'default_signatories': [],
     'default_signatures': 'Function 1\r\nSignature 1\r\nFunction 2\r\nSignature 2',
     'enabled': '1',
     'enable_editors': '0',
     'label': "Committee 1",
     'row_id': 'committee_1',
     'supplements': '0',
     'using_groups': []},
    {'acronym': 'Comm2',
     'auto_from': [],
     'default_assembly': '',
     'default_attendees': [],
     'default_place': 'Place 1',
     'default_signatories': [],
     'default_signatures': 'Function 1\r\nSignature 1\r\nFunction 2\r\nSignature 2',
     'enabled': '1',
     'enable_editors': '0',
     'label': "Committee 2",
     'row_id': 'committee_2',
     'supplements': '2',
     'using_groups': []},
    {'acronym': 'CommForItem',
     'auto_from': [],
     'default_assembly': '',
     'default_attendees': [],
     'default_place': '',
     'default_signatories': [],
     'default_signatures': '',
     'enabled': 'item_only',
     'enable_editors': '0',
     'label': "Committee for item",
     'row_id': 'committee_for_item',
     'supplements': '0',
     'using_groups': []}, )
meetingPma.useAdvices = True
meetingPma.selectableAdvisers = ['developers', 'vendors']
meetingPma.itemAdviceStates = ['proposed']
meetingPma.itemAdviceEditStates = ['proposed', 'validated']
meetingPma.itemAdviceViewStates = ['presented']
meetingPma.transitionsReinitializingDelays = ('backToItemCreated', )
meetingPma.orderedGroupsInCharge = ['developers', 'vendors']
meetingPma.allItemTags = '\n'.join(('Strategic decision', 'Genericity mechanism', 'User interface'))
meetingPma.sortAllItemTags = True
meetingPma.recurringItems = (recItem1, recItem2, )
meetingPma.itemTemplates = (template1, template2, )
meetingPma.powerObservers = (
    {'row_id': 'powerobservers',
     'label': 'Power observers',
     'item_states': ('itemcreated', 'presented', 'accepted', 'delayed'),
     'item_access_on': u'',
     'meeting_states': ('frozen', 'published', 'decided', 'closed'),
     'meeting_access_on': u'',
     'orderindex_': '1'},
    {'row_id': 'restrictedpowerobservers',
     'label': 'Restricted power observers spécial',
     'item_states': [],
     'item_access_on': u'',
     'meeting_states': [],
     'meeting_access_on': u'',
     'orderindex_': '2'})
meetingPma.useVotes = True
meetingPma.styleTemplates = [stylesTemplate1, stylesTemplate2]
meetingPma.podTemplates = [agendaTemplate, decisionsTemplate, itemTemplate, dashboardTemplate, allItemTemplate]
meetingPma.selectableCopyGroups = [developers.getIdSuffixed('reviewers'), vendors.getIdSuffixed('reviewers')]
meetingPma.meetingConfigsToCloneTo = [
    {'meeting_config': 'cfg2',
     'trigger_workflow_transitions_until': NO_TRIGGER_WF_TRANSITION_UNTIL}]
meetingPma.addContactsCSV = False

# Plonegov-assembly
meetingPga = MeetingConfigDescriptor(
    'plonegov-assembly', 'PloneGov assembly', 'PloneGov assembly')
meetingPga.meetingManagers = ['pmManager', 'pmManager2']
meetingPga.shortName = 'Pga'
meetingPga.assembly = 'Bill Gates, Steve Jobs'
meetingPga.signatures = 'Bill Gates, Steve Jobs'
meetingPga.categories = [deployment, maintenance, development, events,
                         research, projects, marketing, subproducts]
meetingPga.classifiers = [classifier1, classifier2, classifier3]
meetingPga.annexTypes = [financialAnalysis, legalAnalysis,
                         budgetAnalysisCfg2, itemAnnex, decisionAnnex,
                         adviceAnnex, adviceLegalAnalysis, meetingAnnex]
meetingPga.usedItemAttributes = (
    'description', 'toDiscuss', 'associatedGroups', 'itemIsSigned', 'category', 'copyGroups')
meetingPga.onMeetingTransitionItemActionToExecute = deepcopy(
    meetingPma.onMeetingTransitionItemActionToExecute)
meetingPga.insertingMethodsOnAddItem = ({'insertingMethod': 'on_categories', 'reverse': '0'}, )
meetingPga.orderedGroupsInCharge = ['developers', 'vendors']
meetingPga.itemTemplates = (template1, template2, )
meetingPga.workflowAdaptations = ['delayed']
meetingPga.useAdvices = False
meetingPga.selectableAdvisers = []
# use same values as meetingPma for powerObserversStates
meetingPga.powerObservers = deepcopy(meetingPma.powerObservers)
meetingPga.itemPositiveDecidedStates = ['accepted']
meetingPga.selectableCopyGroups = [developers.getIdSuffixed('reviewers'), vendors.getIdSuffixed('reviewers')]
meetingPga.itemCopyGroupsStates = ['validated', 'itempublished', 'itemfrozen', 'accepted', 'delayed']
# reuse itemTemplate from meetingPma
pgaItemTemplate = PodTemplateDescriptor('itemTemplate', 'Meeting item')
pgaItemTemplate.pod_template_to_use = {'cfg_id': meetingPma.id, 'template_id': itemTemplate.id}
pgaItemTemplate.pod_portal_types = ['MeetingItem']
pgaItemTemplate.style_template = ['styles2']
meetingPga.styleTemplates = [stylesTemplate1, stylesTemplate2]
meetingPga.podTemplates = [pgaItemTemplate]

# Define held positions to use on persons
held_pos1 = HeldPositionDescriptor('held_pos1',
                                   u'Assembly member 1',
                                   defaults=['present', 'voter'],
                                   usages=['assemblyMember'],
                                   signature_number='1')
held_pos2 = HeldPositionDescriptor('held_pos2',
                                   u'Assembly member 2',
                                   defaults=['present', 'voter'],
                                   usages=['assemblyMember'])
held_pos3 = HeldPositionDescriptor('held_pos3',
                                   u'Assembly member 3',
                                   defaults=['present', 'voter'],
                                   usages=['assemblyMember'])
held_pos4 = HeldPositionDescriptor('held_pos4',
                                   u'Assembly member 4 & 5',
                                   defaults=['present', 'voter'],
                                   usages=['assemblyMember'],
                                   signature_number='2')

# Add persons
person1 = PersonDescriptor('person1',
                           u'Person1LastName',
                           u'Person1FirstName',
                           held_positions=[held_pos1])
person1.photo = u'person1.png'
person1.firstname_abbreviated = u'P1'
person2 = PersonDescriptor('person2',
                           u'Person2LastName',
                           u'Person2FirstName',
                           held_positions=[held_pos2])
person2.firstname_abbreviated = u'P2'
person3 = PersonDescriptor('person3',
                           u'Person3LastName',
                           u'Person3FirstName',
                           gender=u'F',
                           held_positions=[held_pos3])
person3.firstname_abbreviated = u'P3'
person4 = PersonDescriptor('person4',
                           u'Person4LastName',
                           u'Person4FirstName',
                           gender=u'F',
                           held_positions=[held_pos4])
person4.firstname_abbreviated = u'P4'

# The whole configuration object -----------------------------------------------
data = PloneMeetingConfiguration('My meetings', (meetingPma, meetingPga),
                                 (developers, vendors, endUsers, org_outside1, org_outside2))
# necessary for testSetup.test_pm_ToolAttributesAreOnlySetOnFirstImportData
data.restrictUsers = False
data.persons = [person1, person2, person3, person4]
data.usersOutsideGroups = [siteadmin, cadranel, voter1, voter2,
                           powerobserver1, powerobserver2,
                           restrictedpowerobserver1, restrictedpowerobserver2,
                           budgetimpacteditor, templatemanager1, pmManager2]
contactsTemplate = PodTemplateDescriptor('contactsTemplate', 'Export organizations', dashboard=True)
contactsTemplate.odt_file = 'organizations-export.ods'
contactsTemplate.pod_formats = ['ods', 'xls']
contactsTemplate.dashboard_collections_ids = ['all_orgs']
contactsTemplate.use_objects = True
data.contactsTemplates = [contactsTemplate]
data.directory_position_types = [
    {'token': u'default',
     'name': u'Défaut'},
    {'token': u'administrator',
     'name': u'Administrateur|Administrateurs|Administratrice|Administratrices'}, ]
