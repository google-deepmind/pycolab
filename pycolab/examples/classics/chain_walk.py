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

"""An example implementation of the classic chain-walk problem."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab.prefab_parts import sprites as prefab_sprites


GAME_ART = ['..P...................']


def make_game():
  """Builds and returns a chain-walk game."""
  return ascii_art.ascii_art_to_game(
      GAME_ART, what_lies_beneath='.',
      sprites={'P': PlayerSprite})


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player.

  This sprite ties actions to going left and right. If it reaches the leftmost
  extreme of the board, it receives a small reward; if it reaches the rightmost
  extreme it receives a large reward. The game terminates in either case.
  """

  def __init__(self, corner, position, character):
    """Inform superclass that we can go anywhere."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='')

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del layers, backdrop, things   # Unused.

    # Apply motion commands.
    if actions == 0:    # walk leftward?
      self._west(board, the_plot)
    elif actions == 1:  # walk rightward?
      self._east(board, the_plot)

    # See if the game is over.
    if self.position[1] == 0:
      the_plot.add_reward(1.0)
      the_plot.terminate_episode()
    elif self.position[1] == (self.corner[1] - 1):
      the_plot.add_reward(100.0)
      the_plot.terminate_episode()


def main(argv=()):
  del argv  # Unused.

  # Build a chain-walk game.
  game = make_game()

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_LEFT: 0, curses.KEY_RIGHT: 1, -1: 2},
      delay=200)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
