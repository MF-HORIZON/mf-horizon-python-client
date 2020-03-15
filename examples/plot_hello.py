"""
Example code that will be run when docs are built
==================================================

This file will be run to generate a page in the sphinx-gallery 'examples' docs section.
The python in this script is executed by sphinx-gallery at build time, because the 
file is prefixed `plot_`.
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
