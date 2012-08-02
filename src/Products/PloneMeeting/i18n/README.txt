How to add msgids?

--> add them to the PloneMeeting.pot (PloneMeeting domain) or PloneMeeting-plone.pot (plone domain) files
--> run "i18ndude sync --pot the_pot_file the_po_file_to_be_updated"
--> translate the new msgids

How to create a new language translation file?

--> run "i18ndude sync --pot the_pot_file the_new_po_file"
--> modify the first msgstr of the freshly created .po file
    --> define a correct "Language-Code: \n" and a correct "Language-Name: \n"