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

"""Get to the top to win, but watch out for the fiery shockwaves of death.

Command-line usage: `shockwave.py <level>`, where `<level>` is an optional
integer argument that is either -1 (selecting a randomly-generated map) or
0 (selecting the map hard-coded in this module).

Tip: Try hiding in the blue bunkers.

Keys: up, left, right.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import sys

import numpy as np
from pycolab import ascii_art
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites
from scipy import ndimage


# Just one level for now.
LEVELS = [
    ['^^^^^^^^^^^^^^^',
     '               ',
     '  +           +',
     '  ==   ++  == +',
     '              +',
     '=======       +',
     ' +            +',
     '   +      ++   ',
     '+        ==    ',
     '+        +     ',
     '   =           ',
     ' +++ P    ++   '],
]


COLOURS = {'+': (0, 0, 999),      # Blue background. Safe from fire here.
           'P': (0, 999, 0),      # The green player.
           ' ': (500, 500, 500),  # Exposed areas where the player might die.
           '^': (700, 700, 700),  # Permanent safe zone.
           '=': (999, 600, 200),  # Impassable wall.
           '@': (999, 0, 0)}      # The fiery shockwave.


def random_level(height=12, width=12, safety_density=0.15):
  """Returns a random level."""
  level = np.full((height, width), ' ', dtype='|S1')

  # Add some safe areas.
  level[np.random.random_sample(level.shape) < safety_density] = '+'

  # Place walls on random, but not consecutive, rows. Also not on the top or
  # bottom rows.
  valid_rows = set(range(1, height))

  while valid_rows:
    row = np.random.choice(list(valid_rows))

    n_walls = np.random.randint(2, width - 1 - 2)
    mask = np.zeros((width,), dtype=np.bool)
    mask[:n_walls] = True
    np.random.shuffle(mask)
    level[row, mask] = '='

    valid_rows.discard(row - 1)
    valid_rows.discard(row)
    valid_rows.discard(row + 1)

  # Add the player.
  level[-1, np.random.randint(0, width - 1)] = 'P'
  # Add the safe zone.
  level[0] = '^'
  return [row.tostring() for row in level]


class PlayerSprite(prefab_sprites.MazeWalker):

  def __init__(self, corner, position, character):
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='=', confined_to_board=True)

  def update(self, actions, board, layers, backdrop, things, the_plot):

    if actions == 0:    # go upward?
      self._north(board, the_plot)
    elif actions == 1:  # go leftward?
      self._west(board, the_plot)
    elif actions == 2:  # go rightward?
      self._east(board, the_plot)
    elif actions == 3:  # stay put!
      self._stay(board, the_plot)


class ShockwaveDrape(plab_things.Drape):
  """Drape for the shockwave."""

  def __init__(self, curtain, character, width=2):
    """Initializes the `ShockwaveDrape`.

    Args:
      curtain: The curtain.
      character: Character for this drape.
      width: Integer width of the shockwave.
    """
    super(ShockwaveDrape, self).__init__(curtain, character)
    self._width = width
    self._distance_from_impact = np.zeros(self.curtain.shape)
    self._steps_since_impact = 0

  def update(self, actions, board, layers, backdrop, things, the_plot):

    if not self.curtain.any():
      impact_point = np.unravel_index(
          np.random.randint(0, self.curtain.size),
          self.curtain.shape)

      impact_map = np.full_like(self.curtain, True)
      impact_map[impact_point] = False

      self._distance_from_impact = ndimage.distance_transform_edt(impact_map)
      self._steps_since_impact = 0

      the_plot.log('BOOM! Shockwave initiated at {} at frame {}.'.format(
          impact_point, the_plot.frame))

    self.curtain[:] = (
        (self._distance_from_impact > self._steps_since_impact) &
        (self._distance_from_impact <= self._steps_since_impact + self._width) &
        (np.logical_not(layers['=']))
    )

    # Check if the player is safe, dead, or has won.
    player_position = things['P'].position

    if layers['^'][player_position]:
      the_plot.add_reward(1)
      the_plot.terminate_episode()

    under_fire = self.curtain[player_position]
    in_danger_zone = things[' '].curtain[player_position]

    if under_fire and in_danger_zone:
      the_plot.add_reward(-1)
      the_plot.terminate_episode()

    self._steps_since_impact += 1


class MinimalDrape(plab_things.Drape):
  """A Drape that just holds a curtain and contains no game logic."""

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del actions, board, layers, backdrop, things, the_plot  # Unused.


def make_game(level):
  """Builds and returns a Shockwave game."""
  if level == -1:
    level_art = random_level()
  else:
    level_art = LEVELS[level]

  return ascii_art.ascii_art_to_game(
      level_art,
      what_lies_beneath='+',
      sprites={'P': PlayerSprite},
      drapes={'@': ShockwaveDrape, ' ': MinimalDrape, '^': MinimalDrape},
      update_schedule=[' ', '^', 'P', '@'],
      z_order=[' ', '^', '@', 'P'],
  )


def main(argv=()):
  game = make_game(int(argv[1]) if len(argv) > 1 else 0)

  keys_to_actions = {
      curses.KEY_UP: 0,
      curses.KEY_LEFT: 1,
      curses.KEY_RIGHT: 2,
      -1: 3,
  }

  ui = human_ui.CursesUi(
      keys_to_actions=keys_to_actions,
      delay=500, colour_fg=COLOURS)

  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
