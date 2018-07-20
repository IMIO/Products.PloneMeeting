# ------------------------------------------------------------------------------
from appy.shared.utils import LinesCounter

import os


# ------------------------------------------------------------------------------
hsFolder = os.path.dirname(os.getcwd())
print 'Analysing %s...' % hsFolder
LinesCounter(hsFolder).run()
# ------------------------------------------------------------------------------
