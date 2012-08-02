If you want to execute scripts in this folder:

1) cd in this folder (if you are somewhere else, the scripts won't work)
2) python <script_name>

clean.py
--------
clean.py removes all the temporary files (pyc, .py~, etc) from this product

zip.py
------
zip.py creates, in this folder, a zip file containing all the product files.
zip.py firstly calls clean.py and removes also all ".svn" folders if they
are present.
