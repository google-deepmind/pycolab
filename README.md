# The `pycolab` game engine.

A highly-customisable gridworld game engine with some batteries included.
Make your own gridworld games to test reinforcement learning agents!

## Play some games!

If you're new, why not try playing some games first? For the full colour
experience on most UNIX-compatible systems:

  1. crack open a nice, new, modern terminal (iterm2 on Mac, gnome-terminal or
     xterm on linux). (Avoid screen/tmux for now---just the terminal, please.)
  2. set the terminal type to `xterm-256color` (usually, you do this by typing
     `export TERM=xterm-256color` at the command prompt).
  3. run the example games! One easy way is to cd to just above the `pycolab/`
     library directory (that is, cd to the root directory of the git repository
     or the distribution tarball, if you're using either of those) and run
     python with the appropriate `PYTHONPATH` environment variable. Example
     command line for `bash`-like shells:
     `PYTHONPATH=. python -B pycolab/examples/scrolly_maze.py`.

## Okay, install some dependencies first.

If that didn't work, you may need to obtain the following software packages that
pycolab depends on:

  1. Python 2.7, or Python 3.4 and up. We've had success with 2.7.6, 3.4.3, and
     3.6.3; other versions may work.
  2. Numpy. Our version is 1.13.3, but 1.9 seems to have the necessary features.
  3. Scipy, but only for running one of the examples. We have 0.13.3.

## Overview

pycolab is extensively documented and commented, so the best ways to understand
how to use it are:

  - check out examples in the `examples/` subdirectory,
  - read docstrings in the `.py` files.

For docstring reading, the best order is probably this one---stopping whenever
you like (the docs aren't going anywhere...):

  1. the docstring for the `Engine` class in `engine.py`
  2. the docstrings for the classes in `things.py`

Those two are probably the only bits of "required" reading in order to get an
idea of what's going on in `examples/`. From there, the following reading may be
of interest:

  3. `plot.py`: how do game components talk to one another---and how do I
     give the agent rewards and terminate episodes?
  4. `human_ui.py`: how can I try my game out myself?
  5. `prefab_parts/sprites.py`: useful `Sprite` subclasses, including
     `MazeWalker`, a pixel that can walk around but not through walls and
     obstacles.
  6. `cropping.py`: how can I generate the illusion of top-down scrolling by
     cleverly cropping an observation around a particular moving game element?
     (This is a common way to build partial observability into a game.)

Don't forget that you can *always read the tests*, too. These can help
demonstrate by example what all the various components do.

## Disclaimer

This is not an official Google product.

We just thought you should know that.
