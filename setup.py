from setuptools import find_packages
from setuptools import setup


version = '4.2.7.dev0'

setup(name='Products.PloneMeeting',
      version=version,
      description="Official meetings management",
      long_description=open("README.rst").read() + "\n" + open("CHANGES.rst").read(),
      # Get more strings from https://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          "Development Status :: 6 - Mature",
          "Environment :: Web Environment",
          "Framework :: Plone",
          "Framework :: Plone :: 4.3",
          "Intended Audience :: Customer Service",
          "Intended Audience :: Developers",
          "Intended Audience :: End Users/Desktop",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Operating System :: OS Independent",
          "Programming Language :: Other Scripting Engines",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.7",
          "Topic :: Internet :: WWW/HTTP :: Site Management",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: Office/Business",
      ],
      keywords='plone official meetings management egov communesplone imio plonegov',
      author='Gauthier Bastien',
      author_email='gauthier@imio.be',
      url='https://www.imio.be/nos-applications/ia-delib',
      license='GPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      extras_require=dict(test=['imio.helpers[test]',
                                'ipdb',
                                'plone.app.testing',
                                'profilehooks',
                                'plone.app.robotframework',
                                'Products.CMFPlacefulWorkflow'],
                          templates=['Genshi', ],
                          # temp backward compat
                          amqp=[]),
      install_requires=[
          'appy > 0.8.0',
          'archetypes.schematuning',
          'beautifulsoup4',
          'natsort',
          'setuptools',
          'Plone',
          'Pillow',
          'collective.behavior.internalnumber',
          'collective.ckeditor',
          'collective.contact.plonegroup',
          'collective.datagridcolumns',
          'collective.dexteritytextindexer',
          'collective.js.fancytree',
          'collective.js.jqueryui',
          'collective.js.tablednd',
          'collective.iconifieddocumentactions',
          'collective.messagesviewlet',
          'collective.upgrade',
          'collective.usernamelogger',
          'collective.wfadaptations',
          'communesplone.layout',
          'dexterity.localrolesfield',
          'ftw.labels',
          'imio.annex',
          'imio.pm.locales',
          'imio.pm.ws',
          'imio.dashboard>=2.0',
          'imio.helpers[lxml]',
          'imio.migrator',
          'imio.pyutils',
          'imio.zamqp.pm',
          'plone.app.lockingbehavior',
          'plone.app.versioningbehavior',
          'plone.directives.form',
          'plonemeeting.restapi',
          'plonetheme.imioapps',
          'Products.CPUtils',
          'Products.DataGridField',
          'Products.PasswordStrength',
          'Products.cron4plone', ],
      entry_points={},
      )
