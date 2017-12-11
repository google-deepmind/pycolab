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

"""A game that has absolutely nothing to do with Portal.

In Aperture, your goal is to reach the cranachan (`C`). Use your Aperture
Blaster to convert special walls (dark blue) into 'apertures' (blue). You can
create up to two apertures at a time, and walking into one aperture will
transport you instantly to the other! You'll need to use you Blaster to get
around this world of platforms surrounded by deadly green ooze.

Command-line usage: `aperture.py <level>`, where `<level>` is an optional
integer argument selecting Aperture levels 0, 1, or 2.

Keys:
  up, down, left, right - move.
  w, a, s, d - shoot blaster up, left, down, right.
  q - quit.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses
import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites

from six.moves import xrange  # pylint: disable=redefined-builtin


LEVELS = [
    # Level 0: Entranceway.
    [
        '##############',
        '## A ...    @#',
        '##   ...    @#',
        '##@@@...    @#',
        '##......    @#',
        '##......    @#',
        '#@   ...    @#',
        '#@   ...    @#',
        '##   .......##',
        '## C .......##',
        '##############'
    ],
    # Level 1: Alien Containment Zone.
    [
        '#####################',
        '##A#@###########C#@##',
        '## # #         # # ##',
        '##   #  ZZ ZZ  #   ##',
        '## ### Z  Z  Z ### ##',
        '##.#    ZZ ZZ    ..##',
        '##.#    ZZZZZ    ..##',
        '##.#   Z Z Z Z   ..##',
        '##.#  Z  Z Z  Z  # ##',
        '## #  Z Z   Z Z  # ##',
        '## #             # ##',
        '## ............... @#',
        '##@##################',
        '#####################',
    ],
    # Level 2: Turbine Room.
    [
        '####################',
        '#########@@@########',
        '##C         ########',
        '########## ##@######',
        '#A #.........     ##',
        '## #.....   ..... @#',
        '## #..... @ ..... @#',
        '## #......#......###',
        '##  ..  ..#..  ..@##',
        '##  .. @##Z##@ .. ##',
        '##  ..  ..#..  .. ##',
        '##@@......#...... ##',
        '####..... @ ..... ##',
        '##@ .....   ..... ##',
        '##@ ............. @#',
        '####...     .....###',
        '#######@@@@@########',
        '####################'
    ]
]

FG_COLOURS = {
    'A': (999, 500, 0),    # Player wears an orange jumpsuit.
    'X': (200, 200, 999),  # Apertures are blue.
    '#': (700, 700, 700),  # Normal wall, bright grey.
    '@': (400, 400, 600),  # Special wall, grey-blue.
    '.': (100, 300, 100),  # Green ooze.
    'C': (999, 0, 0),      # Cranachan.
    ' ': (200, 200, 200),  # Floor.
    'Z': (0, 999, 0)       # Alien skin.
}

BG_COLOURS = {
    'A': (200, 200, 200),
    'X': (200, 200, 999),
    '#': (800, 800, 800),
    '@': (400, 400, 600),
    '.': (100, 300, 100),
    'C': (999, 800, 800),
    ' ': (200, 200, 200)
}


class PlayerSprite(prefab_sprites.MazeWalker):
  """The player.

  Parent class handles basic movement and collision detection. The special
  aperture drape handles the blaster. This class handles quitting the game and
  cranachan-consumption detection.
  """

  def __init__(self, corner, position, character):
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='#.@')

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del backdrop  # Unused.

    # Handles basic movement, but not movement through apertures.
    if actions == 0:  # go upward?
      self._north(board, the_plot)
    elif actions == 1:  # go downward?
      self._south(board, the_plot)
    elif actions == 2:  # go leftward?
      self._west(board, the_plot)
    elif actions == 3:  # go rightward?
      self._east(board, the_plot)
    elif actions == 9:  # quit?
      the_plot.terminate_episode()

    # Did we walk onto exit? If so, we win!
    if layers['C'][self.position]:
      the_plot.add_reward(1)
      the_plot.terminate_episode()

    # Did we walk onto an aperture? If so, then teleport!
    if layers['X'][self.position]:
      destinations = [p for p in things['X'].apertures if p != self.position]
      if destinations: self._teleport(destinations[0])


class ApertureDrape(plab_things.Drape):
  """Drape for all apertures.

  Tracks aperture locations, creation of new apertures using blaster, and will
  teleport the player if necessary.
  """

  def __init__(self, curtain, character):
    super(ApertureDrape, self).__init__(curtain, character)
    self._apertures = [None, None]

  def update(self, actions, board, layers, backdrop, things, the_plot):
    ply_y, ply_x = things['A'].position

    if actions == 5:  # w - shoot up?
      dx, dy = 0, -1
    elif actions == 6:  # a - shoot left?
      dx, dy = -1, 0
    elif actions == 7:  # s - shoot down?
      dx, dy = 0, 1
    elif actions == 8:  # d - shoot right?
      dx, dy = 1, 0
    else:
      return

    # Walk from the player along direction of blaster shot.
    height, width = layers['A'].shape
    for step in xrange(1, max(height, width)):
      cur_x = ply_x + dx * step
      cur_y = ply_y + dy * step
      if cur_x < 0 or cur_x >= width or cur_y < 0 or cur_y >= height:
        # Out of bounds, beam went nowhere.
        break
      elif layers['#'][cur_y, cur_x]:
        # Hit normal wall before reaching a special wall.
        break
      elif layers['X'][cur_y, cur_x]:
        # Hit an existing aperture.
        break
      if layers['@'][cur_y, cur_x]:
        # Hit special wall, create an aperture.
        self._apertures = self._apertures[1:] + [(cur_y, cur_x)]
        self.curtain.fill(False)
        for aperture in self.apertures:  # note use of None-filtered set.
          self.curtain[aperture] = True
        break

  @property
  def apertures(self):
    """Returns locations of all apertures in the map."""
    return tuple(a for a in self._apertures if a is not None)


def make_game(level_idx):
  return ascii_art.ascii_art_to_game(
      art=LEVELS[level_idx],
      what_lies_beneath=' ',
      sprites={'A': PlayerSprite},
      drapes={'X': ApertureDrape},
      update_schedule=[['A'], ['X']],  # Move player, then check apertures.
      z_order=['X', 'A'])  # Draw player on top of aperture.


def main(argv=()):
  game = make_game(int(argv[1]) if len(argv) > 1 else 0)

  ui = human_ui.CursesUi(
      keys_to_actions={
          # Basic movement.
          curses.KEY_UP: 0,
          curses.KEY_DOWN: 1,
          curses.KEY_LEFT: 2,
          curses.KEY_RIGHT: 3,
          -1: 4,  # Do nothing.
          # Shoot aperture gun.
          'w': 5,
          'a': 6,
          's': 7,
          'd': 8,
          # Quit game.
          'q': 9,
          'Q': 9,
      },
      delay=50,
      colour_fg=FG_COLOURS,
      colour_bg=BG_COLOURS)

  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
