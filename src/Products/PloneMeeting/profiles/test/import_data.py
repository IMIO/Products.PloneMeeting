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

from Products.PloneMeeting.profiles import *

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
    'decision', 'Decision', 'decision.png', '', True)  # Could be used once we
    # will digitally sign decisions ? Indeed, once signed, we will need to
    # store them (together with the signature) as separate files.
decisionAnnex = MeetingFileTypeDescriptor(
    'decision-annex', 'Decision annex(es)', 'decisionAnnex.png', '', True)
# A vintage file type
marketingAnalysis = MeetingFileTypeDescriptor(
    'marketing-annex', 'Marketing annex(es)', 'legalAnalysis.png', '', True,
    active=False)

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
pmManager = UserDescriptor('pmManager', ['MeetingManager'], email="pmmanager@plonemeeting.org", fullname='M. PMManager')
pmCreator1 = UserDescriptor('pmCreator1', [], email="pmcreator1@plonemeeting.org", fullname='M. PMCreator One')
pmCreator1b = UserDescriptor('pmCreator1b', [], email="pmcreator1b@plonemeeting.org", fullname='M. PMCreator One bee')
pmReviewer1 = UserDescriptor('pmReviewer1', [], email="pmreviewer1@plonemeeting.org", fullname='M. PMReviewer One')
pmCreator2 = UserDescriptor('pmCreator2', [], email="pmcreator2@plonemeeting.org", fullname='M. PMCreator Two')
pmReviewer2 = UserDescriptor('pmReviewer2', [], email="pmreviewer2@plonemeeting.org", fullname='M. PMReviewer Two')
pmAdviser1 = UserDescriptor('pmAdviser1', [], email="pmadviser1@plonemeeting.org", fullname='M. PMAdviser One')
voter1 = UserDescriptor('voter1', [], email="voter1@plonemeeting.org", fullname='M. Voter One')
voter2 = UserDescriptor('voter2', [], email="voter2@plonemeeting.org", fullname='M. Voter Two')
powerobserver1 = UserDescriptor('powerobserver1',
                                [],
                                email="powerobserver1@plonemeeting.org",
                                fullname='M. Power Observer1')
# powerobserver1 is MeetingPowerObserverLocal because in the meetingPma '_powerobservers' group
plonemeeting_assembly_powerobservers = PloneGroupDescriptor('plonegov-assembly_powerobservers',
                                                            'plonegov-assembly_powerobservers',
                                                            [])
powerobserver1.ploneGroups = [plonemeeting_assembly_powerobservers, ]
powerobserver2 = UserDescriptor('powerobserver2',
                                [],
                                email="powerobserver2@plonemeeting.org",
                                fullname='M. Power Observer2')

developers = GroupDescriptor('developers', 'Developers', 'Devel',
                             givesMandatoryAdviceOn='python:False')
developers.creators.append(pmCreator1)
developers.creators.append(pmCreator1b)
developers.creators.append(pmManager)
developers.reviewers.append(pmReviewer1)
developers.reviewers.append(pmManager)
developers.observers.append(pmReviewer1)
developers.observers.append(pmManager)
developers.advisers.append(pmAdviser1)
developers.advisers.append(pmManager)

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
    'recItem1', 'Recurring item #1',
    '', category='developers', description='<p>This is the first recurring item.</p>',
    decision='First recurring item approved')
recItem2 = RecurringItemDescriptor(
    'recItem2', 'Recurring item #2',
    '', category='developers', description='<p>This is the second recurring item.</p>',
    decision='Second recurring item approved')
# item templates
template1 = RecurringItemDescriptor(
    'template1', 'Template1',
    '', category='developers', description='<p>This is template1.</p>',
    decision='<p>Template1 decision</p>', usages=['as_template_item', ])
template2 = RecurringItemDescriptor(
    'template2', 'Template2',
    'vendors', category='developers', description='<p>This is template2.</p>',
    decision='<p>Template1 decision</p>', usages=['as_template_item', ],
    templateUsingGroups=['vendors', ])

# File types
overheadAnalysis = MeetingFileTypeDescriptor(
    'overhead-analysis', 'Administrative overhead analysis',
    'overheadAnalysis.png', '')

meetingPma = MeetingConfigDescriptor(
    'plonemeeting-assembly', 'PloneMeeting assembly', 'PloneMeeting assembly')
meetingPma.shortName = 'Pma'
meetingPma.assembly = 'Gauthier Bastien, Gilles Demaret, Kilian Soree, ' \
                      'Arnaud Hubaux, Jean-Michel Abe, Stephan Geulette, ' \
                      'Godefroid Chapelle, Gaetan Deberdt, Gaetan Delannay'
meetingPma.signatures = meetingPga.assembly
meetingPma.categories = [development, research]
meetingPma.meetingFileTypes = [
    financialAnalysis, overheadAnalysis, itemAnnex, decisionAnnex, marketingAnalysis]
meetingPma.usedItemAttributes = ('toDiscuss', 'itemTags', 'itemIsSigned',)
meetingPma.usedMeetingAttributes = ('place',)
meetingPma.itemDecidedStates = ('accepted', 'refused', 'delayed', 'confirmed', 'itemarchived')
meetingPma.sortingMethodOnAddItem = 'on_proposing_groups'
meetingPma.useGroupsAsCategories = True
meetingPma.allItemTags = '\n'.join(('Strategic decision', 'Genericity mechanism', 'User interface'))
meetingPma.sortAllItemTags = True
meetingPma.recurringItems = (recItem1, recItem2, template1, template2, )
# use same values as meetingPga for powerObserversStates
meetingPma.itemPowerObserversStates = meetingPga.itemPowerObserversStates
meetingPma.meetingPowerObserversStates = meetingPga.meetingPowerObserversStates
meetingPma.useVotes = True
meetingPma.meetingUsers = [pmReviewer1_voter, pmManager_observer,
                           cadranel_signer, muser_voter1, muser_voter2]
meetingPma.podTemplates = [agendaTemplate, decisionsTemplate, itemTemplate]
meetingPma.selectableCopyGroups = [developers.getIdSuffixed('reviewers'), vendors.getIdSuffixed('reviewers'), ]

# Plonegov-assembly
meetingPga = MeetingConfigDescriptor(
    'plonegov-assembly', 'PloneGov assembly', 'PloneGov assembly',
    isDefault=True)
meetingPga.shortName = 'Pga'
meetingPga.assembly = 'Bill Gates, Steve Jobs'
meetingPga.signatures = meetingPga.assembly
meetingPga.categories = [deployment, maintenance, development, events,
                         research, projects, marketing, subproducts]
meetingPga.meetingFileTypes = [
    financialAnalysis, legalAnalysis, budgetAnalysis, itemAnnex,
    decisionAnnex]
meetingPga.usedItemAttributes = ('toDiscuss', 'associatedGroups', 'itemIsSigned',)
meetingPga.sortingMethodOnAddItem = 'on_categories'
meetingPga.useGroupsAsCategories = False
meetingPga.useAdvices = True
meetingPga.itemAdviceStates = ['proposed', 'validated']
meetingPga.itemAdviceEditStates = ['proposed', ]
meetingPga.itemAdviceViewStates = ['presented', ]
meetingPga.itemPowerObserversStates = ('itemcreated', 'presented', 'accepted', 'delayed', 'refused')
meetingPga.meetingPowerObserversStates = ('frozen', 'published', 'decided', 'closed')
meetingPga.itemDecidedStates = ('accepted', 'refused', 'delayed', 'confirmed', 'itemarchived')
meetingPga.useCopies = True
meetingPga.selectableCopyGroups = [developers.getIdSuffixed('reviewers'), vendors.getIdSuffixed('reviewers'), ]

# The whole configuration object -----------------------------------------------
data = PloneMeetingConfiguration('My meetings', (meetingPga, meetingPma),
                                 (developers, vendors, endUsers))
data.usersOutsideGroups = [cadranel, voter1, voter2, powerobserver1, powerobserver2]
# ------------------------------------------------------------------------------
