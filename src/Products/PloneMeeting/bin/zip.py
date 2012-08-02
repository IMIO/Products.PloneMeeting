# Imports ----------------------------------------------------------------------
import os, os.path, zipfile, sys, shutil
from clean import Cleaner

# ------------------------------------------------------------------------------
class FolderDeleter:
    def delete(dirName):
        '''Recursively deletes p_dirName.'''
        dirName = os.path.abspath(dirName)
        for root, dirs, files in os.walk(dirName, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(dirName)
    delete = staticmethod(delete)

# ------------------------------------------------------------------------------
class Zipper:
    def __init__(self):
        self.productFolder = os.path.dirname(os.getcwd())
        self.productName = os.path.basename(self.productFolder)
        self.tempFolder = '/tmp/%s' % self.productName
        self.result = self.tempFolder + '.zip'
    def createZipFile(self):
        if os.path.exists(self.result):
            os.remove(self.result)
        zipFile = zipfile.ZipFile(self.result, 'w', zipfile.ZIP_DEFLATED)
        for dirname, dirnames, filenames in os.walk(self.tempFolder):
            for f in filenames:
                fileName = os.path.join(dirname, f)
                archiveName = fileName[5:] # Remove "/tmp/"
                zipFile.write(fileName, archiveName)
                # [2:] is there to avoid havin './' in the path in the zip file.
        zipFile.close()

    def run(self):
        # First, clean the product folder
        Cleaner().run()
        print 'Generating %s.zip...' % self.productName
        # Copy the product to a temp folder
        if os.path.exists(self.tempFolder):
            FolderDeleter.delete(self.tempFolder)
        shutil.copytree(self.productFolder, self.tempFolder)
        # Remove the .svn folders
        for dirpath, dirnames, filenames in os.walk(self.tempFolder):
            for dirname in dirnames:
                if dirname == '.svn':
                    FolderDeleter.delete(os.path.join(dirpath, dirname))
        # Create the zip
        self.createZipFile()
        os.rename(self.result, '%s/%s.zip' % (os.getcwd(), self.productName))
        FolderDeleter.delete(self.tempFolder)

# Main program -----------------------------------------------------------------
if __name__ == '__main__':
    Zipper().run()
# ------------------------------------------------------------------------------
