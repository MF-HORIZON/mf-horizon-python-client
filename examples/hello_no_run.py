"""
Example code that's just for show
==================================================

This file will be reformatted to generate a page in the sphinx-gallery 'examples' docs 
section.
The python in this script is **not** executed by sphinx-gallery at build time 
(no `plot_` prefix in the filename).
"""
import getpass

import mf_horizon_client.hello as hello

###########################################################
# Say hello to Bob:
#

name = "Bob"
print(hello.greeting_text(name))


###########################################################
# Say hello to Alice:
#
print(hello.greeting_text("Alice"))

###########################################################
# Say hello to current user:
#
print(hello.greeting_text(getpass.getuser().capitalize()))
