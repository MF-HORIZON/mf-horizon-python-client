"""
An example plot
==================================================

This file will be run to generate a page in the sphinx-gallery 'examples' docs section.
The python in this script is executed by sphinx-gallery at build time, because the
file is prefixed `plot_`. In addition, sphinx-gallery will capture the matplotlib
plot outputs.
"""
import matplotlib.pyplot as plt
import numpy as np

import mf_horizon_client.hello as hello

###########################################################
# Say hello to Bob:
#
name = "Bob"
print(hello.greeting_text(name))


###########################################################
# Plot a sin curve
#
ax = plt.gca()
x = np.linspace(0, 2 * np.pi, 100)
y = np.sin(x)
ax.plot(x, y)
ax.set_xlabel("x")
ax.set_ylabel("sin(x)")
# Calling plt.show() isn't strictly necessary, but means we can test this script
# from the command line / IDE and still view the outputs:
plt.show()
