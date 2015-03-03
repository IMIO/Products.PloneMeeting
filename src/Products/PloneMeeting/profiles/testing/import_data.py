# -*- coding: utf-8 -*-
# Copyright (c) 2012 by PloneGov
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

from Products.PloneMeeting.config import MEETINGREVIEWERS
from Products.PloneMeeting.profiles import CategoryDescriptor
from Products.PloneMeeting.profiles import GroupDescriptor
from Products.PloneMeeting.profiles import ItemTemplateDescriptor
from Products.PloneMeeting.profiles import MeetingConfigDescriptor
from Products.PloneMeeting.profiles import MeetingFileTypeDescriptor
from Products.PloneMeeting.profiles import MeetingUserDescriptor
from Products.PloneMeeting.profiles import PloneGroupDescriptor
from Products.PloneMeeting.profiles import PloneMeetingConfiguration
from Products.PloneMeeting.profiles import PodTemplateDescriptor
from Products.PloneMeeting.profiles import RecurringItemDescriptor
from Products.PloneMeeting.profiles import UserDescriptor

# First meeting type: a fictitious PloneGov assembly ---------------------------

# Categories
deployment = CategoryDescriptor('deployment', 'Deployment topics')
maintenance = CategoryDescriptor('maintenance', 'Maintenance topics')
development = CategoryDescriptor('development', 'Development topics')
events = CategoryDescriptor('events', 'Events')
research = CategoryDescriptor('research', 'Research topics')
projects = CategoryDescriptor('projects', 'Projects')
# A vintage category
marketing = CategoryDescriptor('marketing', 'Marketing', active=False)
# usingGroups category
subproducts = CategoryDescriptor('subproducts', 'Subproducts wishes', usingGroups=('vendors',))

# File types
financialAnalysis = MeetingFileTypeDescriptor(
    'financial-analysis', 'Financial analysis', 'financialAnalysis.png',
    'Predefined title for financial analysis')
legalAnalysis = MeetingFileTypeDescriptor(
    'legal-analysis', 'Legal analysis', 'legalAnalysis.png', '')
budgetAnalysis = MeetingFileTypeDescriptor(
    'budget-analysis', 'Budget analysis', 'budgetAnalysis.png', '')
itemAnnex = MeetingFileTypeDescriptor(
    'item-annex', 'Other annex(es)', 'itemAnnex.png', '')
decision = MeetingFileTypeDescriptor(
    'decision', 'Decision', 'decision.png', '', 'item_decision')  # Could be used once we
    # will digitally sign decisions ? Indeed, once signed, we will need to
    # store them (together with the signature) as separate files.
decisionAnnex = MeetingFileTypeDescriptor(
    'decision-annex', 'Decision annex(es)', 'decisionAnnex.png', '', 'item_decision')
# A vintage file type
marketingAnalysis = MeetingFileTypeDescriptor(
    'marketing-annex', 'Marketing annex(es)', 'legalAnalysis.png', '', 'item_decision',
    active=False)
# Advice file types
adviceAnnex = MeetingFileTypeDescriptor(
    'advice-annex', 'Advice annex(es)', 'itemAnnex.png', '', 'advice')
adviceLegalAnalysis = MeetingFileTypeDescriptor(
    'advice-legal-analysis', 'Advice legal analysis', 'legalAnalysis.png', '', 'advice')

# Pod templates
agendaTemplate = PodTemplateDescriptor('agendaTemplate', 'Meeting agenda')
agendaTemplate.podTemplate = 'Agenda.odt'
agendaTemplate.podCondition = 'python:here.meta_type=="Meeting"'

decisionsTemplate = PodTemplateDescriptor('decisionsTemplate',
                                          'Meeting decisions')
decisionsTemplate.podTemplate = 'Decisions.odt'
decisionsTemplate.podCondition = 'python:here.meta_type=="Meeting" and ' \
                                 'here.adapted().isDecided()'

itemTemplate = PodTemplateDescriptor('itemTemplate', 'Meeting item')
itemTemplate.podTemplate = 'Item.odt'
itemTemplate.podCondition = 'python:here.meta_type=="MeetingItem"'

# Test users and groups
pmManager = UserDescriptor('pmManager', [], email="pmmanager@plonemeeting.org", fullname='M. PMManager')
pmCreator1 = UserDescriptor('pmCreator1', [], email="pmcreator1@plonemeeting.org", fullname='M. PMCreator One')
pmCreator1b = UserDescriptor('pmCreator1b', [], email="pmcreator1b@plonemeeting.org", fullname='M. PMCreator One bee')
pmReviewer1 = UserDescriptor('pmReviewer1', [], email="pmreviewer1@plonemeeting.org", fullname='M. PMReviewer One')
pmReviewerLevel1 = UserDescriptor('pmReviewerLevel1', [],
                                  email="pmreviewerlevel1@plonemeeting.org", fullname='M. PMReviewer Level One')
pmCreator2 = UserDescriptor('pmCreator2', [], email="pmcreator2@plonemeeting.org", fullname='M. PMCreator Two')
pmReviewer2 = UserDescriptor('pmReviewer2', [], email="pmreviewer2@plonemeeting.org", fullname='M. PMReviewer Two')
pmReviewerLevel2 = UserDescriptor('pmReviewerLevel2', [],
                                  email="pmreviewerlevel2@plonemeeting.org", fullname='M. PMReviewer Level Two')
pmAdviser1 = UserDescriptor('pmAdviser1', [], email="pmadviser1@plonemeeting.org", fullname='M. PMAdviser One')
voter1 = UserDescriptor('voter1', [], email="voter1@plonemeeting.org", fullname='M. Voter One')
voter2 = UserDescriptor('voter2', [], email="voter2@plonemeeting.org", fullname='M. Voter Two')
powerobserver1 = UserDescriptor('powerobserver1',
                                [],
                                email="powerobserver1@plonemeeting.org",
                                fullname='M. Power Observer1')
# powerobserver1 is 'power observer' because in the meetingPma '_powerobservers' group
plonemeeting_assembly_powerobservers = PloneGroupDescriptor('plonemeeting-assembly_powerobservers',
                                                            'plonemeeting-assembly_powerobservers',
                                                            [])
powerobserver1.ploneGroups = [plonemeeting_assembly_powerobservers, ]
powerobserver2 = UserDescriptor('powerobserver2',
                                [],
                                email="powerobserver2@plonemeeting.org",
                                fullname='M. Power Observer2')
restrictedpowerobserver1 = UserDescriptor('restrictedpowerobserver1',
                                          [],
                                          email="restrictedpowerobserver1@plonemeeting.org",
                                          fullname='M. Restricted Power Observer 1')
plonemeeting_assembly_restrictedpowerobservers = PloneGroupDescriptor('plonemeeting-assembly_restrictedpowerobservers',
                                                                      'plonemeeting-assembly_restrictedpowerobservers',
                                                                      [])
restrictedpowerobserver1.ploneGroups = [plonemeeting_assembly_restrictedpowerobservers, ]
restrictedpowerobserver2 = UserDescriptor('restrictedpowerobserver2',
                                          [],
                                          email="restrictedpowerobserver2@plonemeeting.org",
                                          fullname='M. Restricted Power Observer 2')
plonegov_assembly_restrictedpowerobservers = PloneGroupDescriptor('plonegov-assembly_restrictedpowerobservers',
                                                                  'plonegov-assembly_restrictedpowerobservers',
                                                                  [])
restrictedpowerobserver2.ploneGroups = [plonegov_assembly_restrictedpowerobservers, ]

developers = GroupDescriptor('developers', 'Developers', 'Devel')
developers.creators.append(pmCreator1)
developers.creators.append(pmCreator1b)
developers.creators.append(pmManager)
developers.reviewers.append(pmReviewer1)
developers.reviewers.append(pmManager)
developers.observers.append(pmReviewer1)
developers.observers.append(pmManager)
developers.advisers.append(pmAdviser1)
developers.advisers.append(pmManager)
# put pmReviewerLevel1 in first level of reviewers from what is in MEETINGREVIEWERS
getattr(developers, MEETINGREVIEWERS.keys()[-1]).append(pmReviewerLevel1)
# put pmReviewerLevel2 in second level of reviewers from what is in MEETINGREVIEWERS
getattr(developers, MEETINGREVIEWERS.keys()[0]).append(pmReviewerLevel2)

vendors = GroupDescriptor('vendors', 'Vendors', 'Devil')
vendors.creators.append(pmCreator2)
vendors.reviewers.append(pmReviewer2)
vendors.observers.append(pmReviewer2)
vendors.advisers.append(pmReviewer2)
vendors.advisers.append(pmManager)

# Do voters able to see items to vote for
developers.observers.append(voter1)
developers.observers.append(voter2)
vendors.observers.append(voter1)
vendors.observers.append(voter2)

# Add a vintage group
endUsers = GroupDescriptor('endUsers', 'End users', 'EndUsers', active=False)

# Add an external user
cadranel = UserDescriptor('cadranel', [], fullname='M. Benjamin Cadranel')

# Add meeting users (voting purposes)
pmReviewer1_voter = MeetingUserDescriptor('pmReviewer1')
pmManager_observer = MeetingUserDescriptor('pmManager',
                                           duty='Secrétaire de la Chancellerie',
                                           usages=['assemblyMember'])
cadranel_signer = MeetingUserDescriptor('cadranel', duty='Secrétaire',
                                        usages=['assemblyMember', 'signer'],
                                        signatureImage='SignatureCadranel.jpg',
                                        signatureIsDefault=True)
muser_voter1 = MeetingUserDescriptor('voter1', duty='Voter1',
                                     usages=['assemblyMember', 'voter', ])
muser_voter2 = MeetingUserDescriptor('voter2', duty='Voter2',
                                     usages=['assemblyMember', 'voter', ])

# Meeting configuration
# PloneMeeting assembly

# Recurring items
recItem1 = RecurringItemDescriptor(
    'recItem1',
    'Recurring item #1',
    proposingGroup='developers',
    description='<p>This is the first recurring item.</p>',
    decision='First recurring item approved')
recItem2 = RecurringItemDescriptor(
    'recItem2',
    'Recurring item #2',
    proposingGroup='developers',
    description='<p>This is the second recurring item.</p>',
    decision='Second recurring item approved')
# item templates
template1 = ItemTemplateDescriptor(
    'template1', 'Template1',
    '', category='developers', description='<p>This is template1.</p>',
    decision='<p>Template1 decision</p>')
template2 = ItemTemplateDescriptor(
    'template2', 'Template2',
    'vendors', category='developers', description='<p>This is template2.</p>',
    decision='<p>Template1 decision</p>', templateUsingGroups=['vendors', ])

# File types
overheadAnalysis = MeetingFileTypeDescriptor(
    'overhead-analysis', 'Administrative overhead analysis',
    'overheadAnalysis.png', '')

meetingPma = MeetingConfigDescriptor(
    'plonemeeting-assembly', 'PloneMeeting assembly', 'PloneMeeting assembly', isDefault=True)
meetingPma.meetingManagers = ['pmManager', ]
meetingPma.shortName = 'Pma'
meetingPma.assembly = 'Gauthier Bastien, Gilles Demaret, Kilian Soree, ' \
                      'Arnaud Hubaux, Jean-Michel Abe, Stephan Geulette, ' \
                      'Godefroid Chapelle, Gaetan Deberdt, Gaetan Delannay'
meetingPma.signatures = 'Bill Gates, Steve Jobs'
meetingPma.categories = [development, research]
meetingPma.meetingFileTypes = [financialAnalysis, overheadAnalysis,
                               itemAnnex, decisionAnnex, marketingAnalysis,
                               adviceAnnex, adviceLegalAnalysis]
meetingPma.usedItemAttributes = ('toDiscuss', 'itemTags', 'itemIsSigned',)
meetingPma.usedMeetingAttributes = ('place',)
meetingPma.itemDecidedStates = ('accepted', 'refused', 'delayed', 'confirmed', 'itemarchived')
meetingPma.transitionsForPresentingAnItem = ('propose', 'validate', 'present', )
meetingPma.onMeetingTransitionItemTransitionToTrigger = ({'meeting_transition': 'publish',
                                                          'item_transition': 'itempublish'},

                                                         {'meeting_transition': 'freeze',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'freeze',
                                                          'item_transition': 'itemfreeze'},

                                                         {'meeting_transition': 'decide',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'decide',
                                                          'item_transition': 'itemfreeze'},

                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'itemfreeze'},
                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'accept'},
                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'confirm'},

                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'itemfreeze'},
                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'accept'},
                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'confirm'},

                                                         {'meeting_transition': 'archive',
                                                          'item_transition': 'itemarchive'},

                                                         {'meeting_transition': 'backToCreated',
                                                          'item_transition': 'backToItemPublished'},
                                                         {'meeting_transition': 'backToCreated',
                                                          'item_transition': 'backToPresented'},)

meetingPma.insertingMethodsOnAddItem = ({'insertingMethod': 'on_proposing_groups', 'reverse': '0'}, )
meetingPma.useGroupsAsCategories = True
meetingPma.useAdvices = True
meetingPma.itemAdviceStates = ['proposed', ]
meetingPma.itemAdviceEditStates = ['proposed', 'validated', ]
meetingPma.itemAdviceViewStates = ['presented', ]
meetingPma.transitionReinitializingDelays = 'backToItemCreated'
meetingPma.allItemTags = '\n'.join(('Strategic decision', 'Genericity mechanism', 'User interface'))
meetingPma.sortAllItemTags = True
meetingPma.recurringItems = (recItem1, recItem2, )
meetingPma.itemTemplates = (template1, template2, )
# use same values as meetingPga for powerObserversStates
meetingPma.itemPowerObserversStates = ('itemcreated', 'presented', 'accepted', 'delayed', 'refused')
meetingPma.meetingPowerObserversStates = ('frozen', 'published', 'decided', 'closed')
meetingPma.useVotes = True
meetingPma.meetingUsers = [pmReviewer1_voter, pmManager_observer,
                           cadranel_signer, muser_voter1, muser_voter2]
meetingPma.podTemplates = [agendaTemplate, decisionsTemplate, itemTemplate]
meetingPma.selectableCopyGroups = [developers.getIdSuffixed('reviewers'), vendors.getIdSuffixed('reviewers'), ]
meetingPma.meetingConfigsToCloneTo = [{'meeting_config': 'plonegov-assembly',
                                       'trigger_workflow_transitions_until': '__nothing__'}, ]

# Plonegov-assembly
meetingPga = MeetingConfigDescriptor(
    'plonegov-assembly', 'PloneGov assembly', 'PloneGov assembly')
meetingPga.meetingManagers = ['pmManager', ]
meetingPga.shortName = 'Pga'
meetingPga.assembly = 'Bill Gates, Steve Jobs'
meetingPga.signatures = 'Bill Gates, Steve Jobs'
meetingPga.categories = [deployment, maintenance, development, events,
                         research, projects, marketing, subproducts]
meetingPga.meetingFileTypes = [financialAnalysis, legalAnalysis,
                               budgetAnalysis, itemAnnex,
                               decisionAnnex, adviceAnnex, adviceLegalAnalysis]
meetingPga.usedItemAttributes = ('toDiscuss', 'associatedGroups', 'itemIsSigned',)
meetingPga.transitionsForPresentingAnItem = ('propose', 'validate', 'present', )
meetingPga.onMeetingTransitionItemTransitionToTrigger = ({'meeting_transition': 'publish',
                                                          'item_transition': 'itempublish'},

                                                         {'meeting_transition': 'freeze',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'freeze',
                                                          'item_transition': 'itemfreeze'},

                                                         {'meeting_transition': 'decide',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'decide',
                                                          'item_transition': 'itemfreeze'},

                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'itemfreeze'},
                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'accept'},
                                                         {'meeting_transition': 'close',
                                                          'item_transition': 'confirm'},

                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'itempublish'},
                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'itemfreeze'},
                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'accept'},
                                                         {'meeting_transition': 'publish_decisions',
                                                          'item_transition': 'confirm'},

                                                         {'meeting_transition': 'archive',
                                                          'item_transition': 'itemarchive'},

                                                         {'meeting_transition': 'backToCreated',
                                                          'item_transition': 'backToItemPublished'},
                                                         {'meeting_transition': 'backToCreated',
                                                          'item_transition': 'backToPresented'},)

meetingPga.insertingMethodsOnAddItem = ({'insertingMethod': 'on_categories', 'reverse': '0'}, )
meetingPga.useGroupsAsCategories = False
meetingPga.itemTemplates = (template1, template2, )
meetingPga.useAdvices = False
meetingPga.itemPowerObserversStates = ('itemcreated', 'presented', 'accepted', 'delayed', 'refused')
meetingPga.meetingPowerObserversStates = ('frozen', 'published', 'decided', 'closed')
meetingPga.itemDecidedStates = ('accepted', 'refused', 'delayed', 'confirmed', 'itemarchived')
meetingPga.useCopies = True
meetingPga.selectableCopyGroups = [developers.getIdSuffixed('reviewers'), vendors.getIdSuffixed('reviewers'), ]
meetingPga.itemCopyGroupsStates = ['validated', 'itempublished', 'itemfrozen', 'accepted', 'refused', 'delayed', ]

# The whole configuration object -----------------------------------------------
data = PloneMeetingConfiguration('My meetings', (meetingPga, meetingPma),
                                 (developers, vendors, endUsers))
data.usersOutsideGroups = [cadranel, voter1, voter2, powerobserver1, powerobserver2,
                           restrictedpowerobserver1, restrictedpowerobserver2]
# ------------------------------------------------------------------------------
