# ------------------------------------------------------------------------------
import os
from appy.shared.utils import LinesCounter

# ------------------------------------------------------------------------------
hsFolder = os.path.dirname(os.getcwd())
print 'Analysing %s...' % hsFolder
LinesCounter(hsFolder).run()
# ------------------------------------------------------------------------------
