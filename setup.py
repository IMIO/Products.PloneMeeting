from setuptools import setup, find_packages
import os

version = '3.0dev'

setup(name='Products.PloneMeeting',
      version=version,
      description="Official meetings management",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Programming Language :: Python",
        ],
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
            test=['unittest2', 'zope.testing', 'plone.testing',
                  'testfixtures',
                  'plone.app.testing','communesplone.iconified_document_actions','Products.CMFPlacefulWorkflow', 'zope.testing', 'Products.PloneTestCase'],
            templates=['Genshi',
                  ]),
      install_requires=[
          'setuptools',
          'appy',
          'Plone',
          'Pillow',
          'communesplone.iconified_document_actions',
          'imio.pm.locales',],
      entry_points={},
      )

