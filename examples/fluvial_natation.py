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

"""Swimming a river, walking a chain, whatever you like to call it.

Keys: left, right - move the "swimmer". Fight current to get to the right.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses

import numpy as np

import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites


GAME_ART = ['===================================================',
            '     .      :   ,     `     ~          ,    .    ` ',
            '   ,    ~   P     :     .  `    ,    ,    ~    `   ',
            '     `   .     ~~   ,     .   :     .   `     `   ~',
            '===================================================']


COLOURS_FG = {'P': (0, 999, 0),       # The swimmer
              '=': (576, 255, 0),     # The river bank
              ' ': (0, 505, 999),     # Empty water
              '.': (999, 999, 999),   # Waves on the water
              ',': (999, 999, 999),
              '`': (999, 999, 999),
              ':': (999, 999, 999),
              '~': (999, 999, 999)}


COLOURS_BG = {'.': (0, 505, 999),     # Waves on the water have the "water"
              ',': (0, 505, 999),     # colour as their background colour.
              '`': (0, 505, 999),
              ':': (0, 505, 999),
              '~': (0, 505, 999)}


def make_game():
  """Builds and returns a Fluvial Natation game."""
  return ascii_art.ascii_art_to_game(
      GAME_ART, what_lies_beneath=' ',
      sprites={'P': PlayerSprite},
      backdrop=RiverBackdrop)


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player.

  This `Sprite` ties actions to going left and right. On even-numbered game
  iterations, it moves left in addition to whatever the user action specifies,
  akin to the current sweeping a swimmer downriver. If the player goes beyond
  the right edge of the game board, the game is won; if it goes beyond the left
  edge, the game is lost.
  """

  def __init__(self, corner, position, character):
    """Inform superclass that we can go anywhere."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='')

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del layers, backdrop, things   # Unused.

    # Move one square left on even game iterations.
    if the_plot.frame % 2 == 0:
      self._west(board, the_plot)

    # Apply swimming commands.
    if actions == 0:    # swim leftward?
      self._west(board, the_plot)
    elif actions == 1:  # swim rightward?
      self._east(board, the_plot)

    # See if the game is won or lost.
    if self.virtual_position[1] < 0:
      the_plot.add_reward(-1)
      the_plot.terminate_episode()
    elif self.virtual_position[1] >= board.shape[1]:
      the_plot.add_reward(1)
      the_plot.terminate_episode()


class RiverBackdrop(plab_things.Backdrop):
  """A `Backdrop` for the river.

  This `Backdrop` rotates the river part of the backdrop leftward on every even
  game iteration, making the river appear to be flowing.
  """

  def update(self, actions, board, layers, things, the_plot):
    del actions, board, layers, things   # Unused.

    if the_plot.frame % 2 == 0:
      self.curtain[1:4, :] = np.roll(self.curtain[1:4, :], shift=-1, axis=1)


def main(argv=()):
  del argv  # Unused.

  # Build a Fluvial Natation game.
  game = make_game()

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_LEFT: 0, curses.KEY_RIGHT: 1, -1: 2},
      delay=200, colour_fg=COLOURS_FG, colour_bg=COLOURS_BG)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
