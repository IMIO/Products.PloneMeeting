Meeting
=======

En général :
------------
- plus de mutator ni accessors sauf pour certains cas :
  - get_assembly_xxx, get_signatures
  - get_attendees_xxx, get_signatories, get_voters
  - get_place (permet de gérer fonctionnement avec champs place/place_other)
- type de contenu dans content/meeting.py
- workflow dans workflows/meeting.py
- views dans browser/meeting.py
- meta_type ne fonctionne plus, ne plus utiliser `context.meta_type` mais `context.getTagName()`
- dans les tests :
    - plus besoin de passer une date pour créer une séance si pas nécessaire :
    `self.create('Meeting', date=DateTime('2020/05/05'))` >> `self.create('Meeting')`
    - classe `testMeeting` renommée en `testMeetingType`

Champs/attributs :
------------------
- tous les champs et méthodes de Meeting sont passés de camelCase à snake_case
    - souvent quand méthode identique sur MeetingItem ou MeetingAdvice, la méthode a aussi
    été migrée dans les autres classes (queryState/query_state, updateLocalRoles/update_local_roles, ...)
    - MeetingItem.getItemAbsents >> MeetingItem.get_item_absents mais par contre,
    MeetingItem.getAssemblyAbsents pas migrés car sont des accessors de fields du MeetingItem
    - ToolPloneMeeting.formatMeetingDate >> ToolPloneMeeting.format_date
- attributs persistents (PersistentMapping, ...) migrés en snake_case aussi (orderedContacts/ordered_contacts, ...)
- formalisation affichage assembly striked/html/empty_tags/... plus de méthode MeetingItem.displayStrikedAssembly,
  ceci est un paramètre "striked=False" de MeetingItem.getAssembly, même chose côté séance

Indexes :
---------
- indexes renommés :
    - linkedMeetingDate et getDate >> meeting_date
    - linkedMeetingUID >> meeting_uid
    - getPreferredMeeting >> preferred_meeting_uid
    - getPreferredMeetingDate >> preferred_meeting_date

TAL expressions :
-----------------
- la date de la séance est maintenant un datetime au lieu de DateTime
- quand cfg est disponible, utiliser isManager(cfg) ceci permet de réutiliser
  le cache (car context change trop souvent)
- 