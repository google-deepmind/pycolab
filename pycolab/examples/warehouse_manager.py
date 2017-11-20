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

"""A game that has absolutely nothing to do with Sokoban.

Command-line usage: `warehouse_manager.py <level>`, where `<level>` is an
optional integer argument selecting Warehouse Manager levels 0, 1, or 2.

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
from pycolab import rendering
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites


WAREHOUSES_ART = [
    # Legend:
    #     '#': impassable walls.            '.': outdoor scenery.
    #     '_': goal locations for boxes.    'P': player starting location.
    #     '0'-'9': box starting locations.  ' ': boring old warehouse floor.

    ['..........',
     '..######..',     # Map #0, "Tyro"
     '..#  _ #..',
     '.##12 ##..',     # In this map, all of the sprites have the same thing
     '.#  _3 #..',     # underneath them: regular warehouse floor (' ').
     '.#_  4P#..',     # (Contrast with Map #1.) This allows us to use just a
     '.#_######.',     # single character as the what_lies_beneath argument to
     '.# # ## #.',     # ascii_art_to_game.
     '.# 5  _ #.',
     '.########.',
     '..........'],

    ['.............',
     '.....#######.',  # Map #1, "Pretty Easy Randomly Generated Map"
     '....##    _#.',
     '.#### ## __#.',  # This map starts one of the boxes (5) atop one of the
     '.#         #.',  # box goal locations, and since that means that there are
     '.# 1__# 2  #.',  # different kinds of things under the sprites depending
     '.# 3 ###   #.',  # on the map location, we have to use a whole separate
     '.#  45  67##.',  # ASCII art diagram for the what_lies_beneath argument to
     '.#      P #..',  # ascii_art_to_game.
     '.##########..',
     '.............'],

    ['.............',
     '....########.',  # Map #2, "The Open Source Release Will Be Delayed if I
     '....#  _ 1 #.',  #          Can't Think of a Name for This Map"
     '.#### 2 #  #.',
     '.#_ # 3 ## #.',  # This map also requires a full-map what_lies_beneath
     '.#   _  _#P#.',  # argument.
     '.# 45_6 _# #.',
     '.#   #78#  #.',
     '.#  _    9 #.',
     '.###########.',
     '.............'],
]


WAREHOUSES_WHAT_LIES_BENEATH = [
    # What lies below Sprite characters in WAREHOUSES_ART?

    ' ',               # In map #0, ' ' lies beneath all sprites.

    ['.............',
     '.....#######.',  # In map #1, different characters lie beneath sprites.
     '....##    _#.',
     '.#### ## __#.',  # This ASCII art map shows an entirely sprite-free
     '.#         #.',  # rendering of Map #1, but this is mainly for human
     '.# ___#    #.',  # convenience. The ascii_art_to_game function will only
     '.#   ###   #.',  # consult cells that are "underneath" characters
     '.#   _    ##.',  # corresponding to Sprites and Drapes in the original
     '.#        #..',  # ASCII art map.
     '.##########..',
     '.............'],

    ['.............',
     '....########.',     # For map #2.
     '....#  _   #.',
     '.####   #  #.',
     '.#_ # _ ## #.',
     '.#   _  _# #.',
     '.#  __  _# #.',
     '.#   #  #  #.',
     '.#  _      #.',
     '.###########.',
     '.............'],
]


# Using the digits 0-9 in the ASCII art maps is how we allow each box to be
# represented with a different sprite. The only reason boxes should look
# different (to humans or AIs) is when they are in a goal location vs. still
# loose in the warehouse.
#
# Boxes in goal locations are rendered with the help of an overlying Drape that
# paints X characters (see JudgeDrape), but for loose boxes, we will use a
# rendering.ObservationCharacterRepainter to convert the digits to identical 'x'
# characters.
WAREHOUSE_REPAINT_MAPPING = {c: 'x' for c in '0123456789'}


# These colours are only for humans to see in the CursesUi.
WAREHOUSE_FG_COLOURS = {' ': (870, 838, 678),  # Warehouse floor.
                        '#': (428, 135, 0),    # Warehouse walls.
                        '.': (39, 208, 67),    # External scenery.
                        'x': (729, 394, 51),   # Boxes loose in the warehouse.
                        'X': (850, 603, 270),  # Boxes on goal positions.
                        'P': (388, 400, 999),  # The player.
                        '_': (834, 588, 525)}  # Box goal locations.

WAREHOUSE_BG_COLOURS = {'X': (729, 394, 51)}   # Boxes on goal positions.


def make_game(level):
  """Builds and returns a Warehouse Manager game for the selected level."""
  warehouse_art = WAREHOUSES_ART[level]
  what_lies_beneath = WAREHOUSES_WHAT_LIES_BENEATH[level]

  # Create a Sprite for every box in the game ASCII-art.
  sprites = {c: BoxSprite for c in '1234567890' if c in ''.join(warehouse_art)}
  sprites['P'] = PlayerSprite
  # We also have a "Judge" drape that marks all boxes that are in goal
  # locations, and that holds the game logic for determining if the player has
  # won the game.
  drapes = {'X': JudgeDrape}

  # This update schedule simplifies the game logic considerably. The boxes
  # move first, and they only move if there is already a Player next to them
  # to push in the same direction as the action. (This condition can only be
  # satisfied by one box at a time.
  #
  # The Judge runs next, and handles various adminstrative tasks: scorekeeping,
  # deciding whether the player has won, and listening for the 'q'(uit) key. If
  # neither happen, the Judge draws Xs over all boxes that are in a goal
  # position. The Judge runs in its own update group so that it can detect a
  # winning box configuration the instant it is made---and so it can clean up
  # any out-of-date X marks in time for the Player to move into the place where
  # they used to be.
  #
  # The Player moves last, and by the time they try to move into the spot where
  # the box they were pushing used to be, the box (and any overlying drape) will
  # have moved out of the way---since it's in a third update group (see `Engine`
  # docstring).
  update_schedule = [[c for c in '1234567890' if c in ''.join(warehouse_art)],
                     ['X'],
                     ['P']]

  # We are also relying on the z order matching a depth-first traversal of the
  # update schedule by default---that way, the JudgeDrape gets to make its mark
  # on top of all of the boxes.
  return ascii_art.ascii_art_to_game(
      warehouse_art, what_lies_beneath, sprites, drapes,
      update_schedule=update_schedule)


class BoxSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for boxes in our warehouse.

  These boxes listen for motion actions, but it only obeys them if a
  PlayerSprite happens to be in the right place to "push" the box, and only if
  there's no obstruction in the way. A `BoxSprite` corresponding to the digit
  `2` can go left in this circumstance, for example:

      .......
      .#####.
      .#   #.
      .# 2P#.
      .#####.
      .......

  but in none of these circumstances:

      .......     .......     .......
      .#####.     .#####.     .#####.
      .#   #.     .#P  #.     .#   #.
      .#P2 #.     .# 2 #.     .##2P#.
      .#####.     .#####.     .#####.
      .......     .......     .......

  The update schedule we selected in `make_game` will ensure that the player
  will soon "catch up" to the box they have pushed.
  """

  def __init__(self, corner, position, character):
    """Constructor: simply supplies characters that boxes can't traverse."""
    impassable = set('#.0123456789PX') - set(character)
    super(BoxSprite, self).__init__(corner, position, character, impassable)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del backdrop, things  # Unused.

    # Implements the logic described in the class docstring.
    rows, cols = self.position
    if actions == 0:    # go upward?
      if layers['P'][rows+1, cols]: self._north(board, the_plot)
    elif actions == 1:  # go downward?
      if layers['P'][rows-1, cols]: self._south(board, the_plot)
    elif actions == 2:  # go leftward?
      if layers['P'][rows, cols+1]: self._west(board, the_plot)
    elif actions == 3:  # go rightward?
      if layers['P'][rows, cols-1]: self._east(board, the_plot)


class JudgeDrape(plab_things.Drape):
  """A `Drape` that marks boxes atop goals, and also decides whether you've won.

  This `Drape` sits atop all of the box `Sprite`s and provides a "luxury"
  Sokoban feature: if one of the boxes is sitting on one of the goal states, it
  marks the box differently from others that are loose in the warehouse.

  While doing so, the `JudgeDrape` also counts the number of boxes on goal
  states, and uses this information to update the game score and to decide
  whether the game has finished.
  """

  def __init__(self, curtain, character):
    super(JudgeDrape, self).__init__(curtain, character)
    self._last_num_boxes_on_goals = 0

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Clear our curtain and mark the locations of all the boxes True.
    self.curtain.fill(False)
    for box_char in (c for c in '0123456789' if c in layers):
      self.curtain[things[box_char].position] = True
    # We can count the number of boxes we have now:
    num_boxes = np.sum(self.curtain)
    # Now logically-and the box locations with the goal locations. These are
    # all of the goals that are occupied by boxes at the moment.
    np.logical_and(self.curtain, (backdrop.curtain == backdrop.palette._),
                   out=self.curtain)

    # Compute the reward to credit to the player: the change in how many goals
    # are occupied by boxes at the moment.
    num_boxes_on_goals = np.sum(self.curtain)
    the_plot.add_reward(num_boxes_on_goals - self._last_num_boxes_on_goals)
    self._last_num_boxes_on_goals = num_boxes_on_goals

    # See if we should quit: it happens if the user solves the puzzle or if
    # they give up and execute the 'quit' action.
    if (actions == 5) or (num_boxes_on_goals == num_boxes):
      the_plot.terminate_episode()


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player, the Warehouse Manager.

  This `Sprite` requires no logic beyond tying actions to `MazeWalker`
  motion action helper methods, which keep the player from walking on top of
  obstacles. If the player has pushed a box, then the update schedule has
  already made certain that the box is out of the way (along with any
  overlying characters from the `JudgeDrape`) by the time the `PlayerSprite`
  gets to move.
  """

  def __init__(self, corner, position, character):
    """Constructor: simply supplies characters that players can't traverse."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='#.0123456789X')

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del backdrop, things, layers  # Unused.

    if actions == 0:    # go upward?
      self._north(board, the_plot)
    elif actions == 1:  # go downward?
      self._south(board, the_plot)
    elif actions == 2:  # go leftward?
      self._west(board, the_plot)
    elif actions == 3:  # go rightward?
      self._east(board, the_plot)


def main(argv=()):
  # Build a Warehouse Manager game.
  game = make_game(int(argv[1]) if len(argv) > 1 else 0)

  # Build an ObservationCharacterRepainter that will make all of the boxes in
  # the warehouse look the same.
  repainter = rendering.ObservationCharacterRepainter(WAREHOUSE_REPAINT_MAPPING)

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 0, curses.KEY_DOWN: 1,
                       curses.KEY_LEFT: 2, curses.KEY_RIGHT: 3,
                       -1: 4,
                       'q': 5, 'Q': 5},
      repainter=repainter, delay=100,
      colour_fg=WAREHOUSE_FG_COLOURS,
      colour_bg=WAREHOUSE_BG_COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
