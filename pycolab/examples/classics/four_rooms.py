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

"""An example implementation of the classic four-rooms scenario."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab.prefab_parts import sprites as prefab_sprites


GAME_ART = ['#############',
            '#     #     #',
            '#     #     #',
            '#     #     #',
            '#           #',
            '#     #     #',
            '#### ###### #',
            '#     #     #',
            '#     #     #',
            '#           #',
            '#     #     #',
            '# P   #     #',
            '#############']


def make_game():
  """Builds and returns a four-rooms game."""
  return ascii_art.ascii_art_to_game(
      GAME_ART, what_lies_beneath=' ',
      sprites={'P': PlayerSprite})


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player.

  This `Sprite` ties actions to going in the four cardinal directions. If we
  reach a magical location (in this example, (4, 3)), the agent receives a
  reward of 1 and the episode terminates.
  """

  def __init__(self, corner, position, character):
    """Inform superclass that we can't walk through walls."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='#')

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del layers, backdrop, things   # Unused.

    # Apply motion commands.
    if actions == 0:    # walk upward?
      self._north(board, the_plot)
    elif actions == 1:  # walk downward?
      self._south(board, the_plot)
    elif actions == 2:  # walk leftward?
      self._west(board, the_plot)
    elif actions == 3:  # walk rightward?
      self._east(board, the_plot)

    # See if we've found the mystery spot.
    if self.position == (4, 3):
      the_plot.add_reward(1.0)
      the_plot.terminate_episode()


def main(argv=()):
  del argv  # Unused.

  # Build a four-rooms game.
  game = make_game()

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 0, curses.KEY_DOWN: 1,
                       curses.KEY_LEFT: 2, curses.KEY_RIGHT: 3,
                       -1: 4},
      delay=200)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
