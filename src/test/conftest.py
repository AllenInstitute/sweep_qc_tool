

# Making this app's source code a package breaks the windows freeze, so 
# we'll get imports via path munging
import sys
import os
sys.path.append(os.path.join(
    os.path.dirname(
        os.path.dirname(__file__)
    ),
    "main",
    "python"
))