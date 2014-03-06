from setuptools import setup, find_packages
import os

version = '3.2.0.1'

setup(name='Products.PloneMeeting',
      version=version,
      description="Official meetings management",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=["Programming Language :: Python", ],
      keywords='',
      author='',
      author_email='',
      url='http://www.communesplone.org/les-outils/applications-metier/gestion-des-deliberations',
      license='GPL',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      namespace_packages=['Products'],
      include_package_data=True,
      zip_safe=False,
      extras_require=dict(
            test=['unittest2',
                  'profilehooks',
                  'zope.testing',
                  'plone.testing',
                  'plone.app.testing',
                  'Products.CMFPlacefulWorkflow',
                  'zope.testing',
                  'Products.PloneTestCase'],
            templates=['Genshi',
                  ]),
      install_requires=[
          'setuptools',
          'appy',
          'Plone',
          'Pillow',
          'collective.ckeditor',
          'collective.documentviewer',
          'communesplone.iconified_document_actions',
          'imio.pm.locales',
          'imio.migrator',
          'imio.actionspanel',
          'plone.directives.form',
          'Products.DataGridField',
          'Products.cron4plone', ],
      entry_points={},
      )
