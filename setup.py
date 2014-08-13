from setuptools import setup, find_packages
import os

version = '3.3dev'

setup(name='Products.PloneMeeting',
      version=version,
      description="Official meetings management",
      long_description=open("README.txt").read() + "\n" +
           open(os.path.join("docs", "HISTORY.txt")).read(),
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
          "Topic :: Internet :: WWW/HTTP :: Site Management",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: Office/Business",
      ],
      keywords='plone official meetings management egov communesplone imio plonegov',
      author='',
      author_email='',
      url='http://www.imio.be/produits/gestion-des-deliberations',
      license='GPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      extras_require=dict(test=['unittest2',
                                'profilehooks',
                                'zope.testing',
                                'plone.testing',
                                'plone.app.testing',
                                'plone.app.robotframework',
                                'Products.CMFPlacefulWorkflow',
                                'zope.testing',
                                'Products.PloneTestCase'],
                          templates=['Genshi', ]),
      install_requires=[
          'setuptools',
          'appy',
          'Plone',
          'Pillow',
          'collective.ckeditor',
          'collective.documentviewer',
          'collective.datagridcolumns',
          'collective.js.fancytree',
          'collective.js.jqueryui',
          'collective.iconifieddocumentactions',
          'imio.pm.locales',
          'imio.helpers',
          'imio.migrator',
          'imio.actionspanel',
          'plone.directives.form',
          'plonetheme.imioapps',
          'Products.DataGridField',
          'Products.cron4plone', ],
      entry_points={},
      )
