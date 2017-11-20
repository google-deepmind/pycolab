# Copyright 2017 the pycolab Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A "game" whereby you move text around the board.

Keys: up, down, left, right - move. q - quit.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses

import numpy as np

import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab import things


HELLO_ART = ['                                    ',
             '  #   #  ### #    #     ###         ',
             '  #   # #    #    #    #   #        ',
             '  ##### #### #    #    #   #        ',
             '  #   # #    #    #    #   #        ',
             '  #   #  ###  ###  ###  ###         ',
             '                                    ',
             '     @   @  @@@   @@@  @    @@@@  1 ',
             '     @   @ @   @ @   @ @    @   @ 2 ',
             '     @ @ @ @   @ @@@@  @    @   @ 3 ',
             '     @ @ @ @   @ @   @ @    @   @   ',
             '      @@@   @@@  @   @  @@@ @@@@  4 ',
             '                                    ']


HELLO_COLOURS = {' ': (123, 123, 123),  # Only used in this program by
                 '#': (595, 791, 928),  # the CursesUi.
                 '@': (54, 501, 772),
                 '1': (999, 222, 222),
                 '2': (222, 999, 222),
                 '3': (999, 999, 111),
                 '4': (222, 222, 999)}


def make_game():
  """Builds and returns a Hello World game."""
  return ascii_art.ascii_art_to_game(
      HELLO_ART,
      what_lies_beneath=' ',
      sprites={'1': ascii_art.Partial(SlidingSprite, 0),
               '2': ascii_art.Partial(SlidingSprite, 1),
               '3': ascii_art.Partial(SlidingSprite, 2),
               '4': ascii_art.Partial(SlidingSprite, 3)},
      drapes={'@': RollingDrape},
      z_order='12@34')


class RollingDrape(things.Drape):
  """A Drape that just `np.roll`s the mask around either axis."""

  # There are four rolls to choose from: two shifts of size 1 along both axes.
  _ROLL_AXES = [0, 0, 1, 1]
  _ROLL_SHIFTS = [-1, 1, -1, 1]

  def update(self, actions, board, layers, backdrop, all_things, the_plot):
    del board, layers, backdrop, all_things  # unused

    if actions is None: return  # No work needed to make the first observation.
    if actions == 4: the_plot.terminate_episode()  # Action 4 means "quit".

    # If the player has chosen a motion action, use that action to index into
    # the set of four rolls.
    if actions < 4:
      rolled = np.roll(self.curtain,  # Makes a copy, alas.
                       self._ROLL_SHIFTS[actions], self._ROLL_AXES[actions])
      np.copyto(self.curtain, rolled)
      the_plot.add_reward(1)  # Give ourselves a point for moving.


class SlidingSprite(things.Sprite):
  """A Sprite that moves in diagonal directions."""

  # We have four mappings from actions to motions to choose from. The mappings
  # are arranged so that given any index i, then across all sets, the motion
  # that undoes motion i always has the same index j.
  _DX = ([-1, 1, -1, 1], [-1, 1, -1, 1], [1, -1, 1, -1], [1, -1, 1, -1])
  _DY = ([-1, 1, 1, -1], [1, -1, -1, 1], [1, -1, -1, 1], [-1, 1, 1, -1])

  def __init__(self, corner, position, character, direction_set):
    """Build a SlidingSprite.

    Args:
      corner: required argument for Sprite.
      position: required argument for Sprite.
      character: required argument for Sprite.
      direction_set: an integer in `[0,3]` that selects from any of four
          mappings from actions to (diagonal) motions.
    """
    super(SlidingSprite, self).__init__(corner, position, character)
    self._dx = self._DX[direction_set]
    self._dy = self._DY[direction_set]

  def update(self, actions, board, layers, backdrop, all_things, the_plot):
    del board, layers, backdrop, all_things, the_plot  # unused
    # Actions 0-3 are motion actions; the others we ignore.
    if actions is None or actions > 3: return
    new_col = (self._position.col + self._dx[actions]) % self.corner.col
    new_row = (self._position.row + self._dy[actions]) % self.corner.row
    self._position = self.Position(new_row, new_col)


def main(argv=()):
  del argv  # Unused.

  # Build a Hello World game.
  game = make_game()

  # Log a message in its Plot object.
  game.the_plot.log('Hello, world!')

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 0, curses.KEY_DOWN: 1, curses.KEY_LEFT: 2,
                       curses.KEY_RIGHT: 3, 'q': 4, 'Q': 4, -1: 5},
      delay=50, colour_fg=HELLO_COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
