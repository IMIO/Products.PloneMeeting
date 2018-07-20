# Imports ----------------------------------------------------------------------
import os
import os.path


# ------------------------------------------------------------------------------
class Cleaner:
    exts = ('.pyc', '.log')
    def makeDir(self, folder):
        os.mkdir(folder)
        f = file('%s/Readme.txt' % folder, 'w')
        f.write('This is a temp folder.')
        f.close()
    def run(self, verbose=True):
        # Remove files with an extention listed in self.exts
        for root, dirs, files in os.walk('..'):
            for fileName in files:
                ext = os.path.splitext(fileName)[1]
                if (ext in Cleaner.exts) or ext.endswith('~'):
                    fileToRemove = os.path.join(root, fileName)
                    if verbose:
                        print 'Removing %s...' % fileToRemove
                    os.remove(fileToRemove)

# Main program -----------------------------------------------------------------
if __name__ == '__main__':
    Cleaner().run()
# ------------------------------------------------------------------------------
