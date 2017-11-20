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

"""A game faintly reminiscent of Catch.

Keys: left, right - move the "catcher".
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import random
import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab import rendering
from pycolab.prefab_parts import sprites as prefab_sprites


GAME_ART = ['   b   ',
            '       ',
            '       ',
            '       ',
            '       ',
            '       ',
            '       ',
            '       ',
            '       ',
            '   P   ']


# In Catch, both the ball and the player look identical.
REPAINT_MAPPING = {'b': 'X', 'P': 'X'}


# These "colours" are only for humans to see in the CursesUi.
COLOURS = {' ': (0, 0, 0),        # The game board is black.
           'X': (999, 999, 999)}  # The sprites are white.


def make_game():
  """Builds and returns an Apprehend game."""
  return ascii_art.ascii_art_to_game(
      GAME_ART, what_lies_beneath=' ',
      sprites={'P': PlayerSprite, 'b': BallSprite},
      update_schedule=['b', 'P'])


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player.

  This `Sprite` ties actions to going left and right. After every move, it
  checks whether its position is the same as the ball's position. If so, the
  game is won.
  """

  def __init__(self, corner, position, character):
    """Simply indicates to the superclass that we can't walk off the board."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='', confined_to_board=True)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del layers, backdrop  # Unused.

    if actions == 0:    # go leftward?
      self._west(board, the_plot)
    elif actions == 1:  # go rightward?
      self._east(board, the_plot)

    if self.virtual_position == things['b'].virtual_position:
      the_plot.add_reward(1)
      the_plot.terminate_episode()


class BallSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for the falling ball.

  This `Sprite` marches linearly toward one of the positions in the bottom row
  of the game board, selected at random. If it is able to go beyond this
  position, the game is lost.
  """

  def __init__(self, corner, position, character):
    """Inform superclass that we can go anywhere; initialise falling maths."""
    super(BallSprite, self).__init__(
        corner, position, character, impassable='')
    # Choose one of the positions in the bottom row of the game board, and
    # compute the per-row X motion (fractional) we'd need to fall there.
    self._dx = random.uniform(-2.499, 2.499) / (corner[0] - 1.0)
    # At each game iteration, we add _dx to this accumulator. If the accumulator
    # exceeds 0.5, we move one position right; if it goes below -0.5, we move
    # one position left. We then bump the accumulator by -1 and 1 respectively.
    self._x_accumulator = 0.0

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del actions, layers, backdrop, things   # Unused.

    # The ball is always falling downward.
    self._south(board, the_plot)
    self._x_accumulator += self._dx

    # Sometimes the ball shifts left or right.
    if self._x_accumulator < -0.5:
      self._west(board, the_plot)
      self._x_accumulator += 1.0
    elif self._x_accumulator > 0.5:
      self._east(board, the_plot)
      self._x_accumulator -= 1.0

    # Log the motion information for review in e.g. game consoles.
    the_plot.log('Falling with horizontal velocity {}.\n'
                 '  New location: {}.'.format(self._dx, self.virtual_position))

    # If we've left the board altogether, then the game is lost.
    if self.virtual_position[0] >= board.shape[0]:
      the_plot.add_reward(-1)
      the_plot.terminate_episode()


def main(argv=()):
  del argv  # Unused.

  # Build an Apprehend game.
  game = make_game()

  # Build an ObservationCharacterRepainter that will make the player and the
  # ball look identical.
  repainter = rendering.ObservationCharacterRepainter(REPAINT_MAPPING)

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_LEFT: 0, curses.KEY_RIGHT: 1, -1: 2},
      repainter=repainter, delay=500,
      colour_fg=COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
