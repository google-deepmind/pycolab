# Copyright 2018 the pycolab Authors
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

"""An heroic undertaking of exploration and derring-do! Slay the dragon/duck!

Also, a demonstration of `storytelling.Story`.

Keys: up, down, left, right - move. q - quit.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import curses

import sys

from pycolab import ascii_art
from pycolab import cropping
from pycolab import human_ui
from pycolab import storytelling
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites


GAME_ART_CASTLE = ['##  ##   ##  ##',
                   '###############',
                   '#             #',
                   '#      D      #',  # As in "dragon" or "duck".
                   '#             #',
                   '#             #',
                   '#             #',
                   '###### P ######']  # As in "player".


GAME_ART_CAVERN = ['@@@@@@@@@@@@@@@',
                   '@@@@@@     @@@@',
                   '@@@@@      @@@@',
                   '@ @@    S    @@',  # As in "sword".
                   '            @@@',
                   'P @@@     @@@@@',  # As in "player".
                   '@@@@@@  @@@@@@@',
                   '@@@@@@@@@@@@@@@']


GAME_ART_KANSAS = ['######%%%######wwwwwwwwwwwwwwwwwwwwww@wwwwwww',
                   'w~~~~~%%%~~~~~~~~~~~~~~~~@~~~wwwww~~~~~~~~~~@',
                   'ww~~~~%%%~~~~~~~~~@~~~~~~~~~~~~~~~~~~~~~~@@@@',
                   'ww~~~~~%%%%~~~~~~~~~~~~~~~~~~~~~~~~~~~~~@@@@@',
                   '@ww~~~~~~%%%%~~~~~~~~~~~~~@~~%%%%%%%%%%%%%%%%',
                   'ww~~~~~~~~~~%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%',
                   'w~~~~~~@~~~~~~~~%%%%%%%%%%%%%%~~~~~~~~~~~~@@@',
                   'ww~~~~~~~~~~P~~~~~~~~~~~~~~~~~~~~~~~~~@~~~@@@',  # "Player".
                   'wwww~@www~~~~~~~~~wwwwww~~~@~~~~wwwww~~~~~~ww',
                   'wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww']


# These colours are only for humans to see in the CursesUi.
COLOURS = {' ': (0, 0, 0),        # Interior floors.
           '#': (447, 400, 400),  # Castle walls.
           '%': (999, 917, 298),  # Road.
           '~': (270, 776, 286),  # Grass.
           '@': (368, 333, 388),  # Stones and cave walls.
           'w': (309, 572, 999),  # Water. (The shores of Kansas.)
           'P': (999, 364, 0),    # Player.
           'S': (500, 999, 948),  # Sword.
           'D': (670, 776, 192)}  # Dragonduck.


def make_game():
  """Builds and returns an Ordeal game."""

  # Factories for building the three subgames of Ordeal.
  def make_castle():
    return ascii_art.ascii_art_to_game(
        GAME_ART_CASTLE, what_lies_beneath=' ',
        sprites=dict(P=PlayerSprite, D=DragonduckSprite),
        update_schedule=['P', 'D'], z_order=['D', 'P'])

  def make_cavern():
    return ascii_art.ascii_art_to_game(
        GAME_ART_CAVERN, what_lies_beneath=' ',
        sprites=dict(P=PlayerSprite), drapes=dict(S=SwordDrape),
        update_schedule=['P', 'S'])

  def make_kansas():
    return ascii_art.ascii_art_to_game(
        GAME_ART_KANSAS, what_lies_beneath='~', sprites=dict(P=PlayerSprite))

  # A cropper for cropping the "Kansas" part of the game to the size of the
  # other two games.
  crop_kansas = cropping.ScrollingCropper(
      rows=8, cols=15, to_track='P', scroll_margins=(2, 3))

  return storytelling.Story(
      chapters=dict(castle=make_castle, cavern=make_cavern, kansas=make_kansas),
      croppers=dict(castle=None, cavern=None, kansas=crop_kansas),
      first_chapter='kansas')


class SwordDrape(plab_things.Drape):
  """A `Drape` for the sword.

  This `Drape` simply disappears if the player sprite steps on any element where
  its curtain is True, setting the 'has_sword' flag in the Plot as it goes.
  I guess we'll give the player a reward for sword collection, too.
  """

  def update(self, actions, board, layers, backdrop, things, the_plot):
    if self.curtain[things['P'].position]:
      the_plot['has_sword'] = True
      the_plot.add_reward(1.0)
    if the_plot.get('has_sword'): self.curtain[:] = False  # Only one sword.


class DragonduckSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for the castle dragon, or duck. Whatever.

  This creature shuffles toward the player. It moves faster than the player
  since it can go diagonally. If the player has the sword, then if the creature
  touches the player, it dies and the player receives a point. Otherwise,
  contact is fatal to the player.
  """

  def __init__(self, corner, position, character):
    """Simply registers impassables and board confinement to the superclass."""
    super(DragonduckSprite, self).__init__(
        corner, position, character, impassable='#', confined_to_board=True)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    if the_plot.frame == 0: return  # Do nothing on the first frame..

    # Where is the player in relation to us?
    player = things['P'].position
    relative_locations = (self.position.row > player.row,  # Player is above us.
                          self.position.col < player.col,  # To the right.
                          self.position.row < player.row,  # Below us.
                          self.position.col > player.col)  # To the left.

    # Move toward player! -- (North..East...West..South).
    if relative_locations == (True, False, False, False):
      self._north(board, the_plot)
    elif relative_locations == (True, True, False, False):
      self._northeast(board, the_plot)
    elif relative_locations == (False, True, False, False):
      self._east(board, the_plot)
    elif relative_locations == (False, True, True, False):
      self._southeast(board, the_plot)
    elif relative_locations == (False, False, True, False):
      self._south(board, the_plot)
    elif relative_locations == (False, False, True, True):
      self._southwest(board, the_plot)
    elif relative_locations == (False, False, False, True):
      self._west(board, the_plot)
    elif relative_locations == (True, False, False, True):
      self._northwest(board, the_plot)

    # If we're on top of the player, battle! Note that we use the layers
    # argument to determine whether we're on top, which keeps there from being
    # battles that don't look like battles (basically, where the player and the
    # monster both move to the same location, but the screen hasn't updated
    # quite yet).
    if layers['P'][self.position]:
      # This battle causes a termination that will end the game.
      the_plot.next_chapter = None
      the_plot.terminate_episode()
      # But who is the winner?
      if the_plot.get('has_sword'):
        the_plot.add_reward(1.0)   # Player had the sword! Our goose is cooked!
        the_plot.change_z_order(move_this='D', in_front_of_that='P')
      else:
        the_plot.add_reward(-1.0)  # No sword. Chomp chomp chomp!
        the_plot.change_z_order(move_this='P', in_front_of_that='D')


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player.

  This `Sprite` mainly ties actions to the arrow keys, although it contains
  some logic that uses the Plot to make sure that when we transition between
  subgames (i.e. when we go from Cavern to Kansas and so forth), the player
  position reflects the idea that we've only moved a single step in the
  "real world".
  """

  def __init__(self, corner, position, character):
    """Simply registers impassables and board confinement to the superclass."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='@#w', confined_to_board=True)
    # Like corner, but inclusive of the last row/column.
    self._limits = self.Position(corner.row - 1, corner.col - 1)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    limits = self._limits  # Abbreviation.

    # This large if statement probably deserves to be abbreviated with a
    # protocol. Anyhow, the first four clauses handle actual agent actions.
    # Note how much of the work amounts to detecting whether we are moving
    # beyond the edge of the board, and if so, which game we should go to next.
    if actions == 0:  # go upward?
      if the_plot.this_chapter == 'kansas' and self.position.row <= 0:
        the_plot.next_chapter = 'castle'
        the_plot.terminate_episode()
      else:
        self._north(board, the_plot)

    elif actions == 1:  # go downward?
      if the_plot.this_chapter == 'castle' and self.position.row >= limits.row:
        the_plot.next_chapter = 'kansas'
        the_plot.terminate_episode()
      else:
        self._south(board, the_plot)

    elif actions == 2:  # go leftward?
      if the_plot.this_chapter == 'cavern' and self.position.col <= 0:
        the_plot.next_chapter = 'kansas'
        the_plot.terminate_episode()
      else:
        self._west(board, the_plot)

    elif actions == 3:  # go rightward?
      if the_plot.this_chapter == 'kansas' and self.position.col >= limits.col:
        the_plot.next_chapter = 'cavern'
        the_plot.terminate_episode()
      else:
        self._east(board, the_plot)

    elif actions == 4:  # just quit?
      the_plot.next_chapter = None  # This termination will be final.
      the_plot.terminate_episode()

    # This last clause of the big if statement handles the very first action in
    # a game. If we are starting this game just after concluding the previous
    # game in a Story, we teleport to a place that "lines up" with where we were
    # in the last game, so that our motion appears to be smooth.
    elif the_plot.frame == 0:
      if (the_plot.prior_chapter == 'kansas' and
          the_plot.this_chapter == 'castle'):
        self._teleport((limits.row, the_plot['last_position'].col))

      elif (the_plot.prior_chapter == 'castle' and
            the_plot.this_chapter == 'kansas'):
        self._teleport((0, the_plot['last_position'].col))

      elif (the_plot.prior_chapter == 'kansas' and
            the_plot.this_chapter == 'cavern'):
        self._teleport((the_plot['last_position'].row, 0))

      elif (the_plot.prior_chapter == 'cavern' and
            the_plot.this_chapter == 'kansas'):
        self._teleport((the_plot['last_position'].row, limits.col))

    # We always save our position to support the teleporting just above.
    the_plot['last_position'] = self.position


def main(argv=()):
  del argv  # Unused.

  # Build an Ordeal game.
  game = make_game()

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 0, curses.KEY_DOWN: 1,
                       curses.KEY_LEFT: 2, curses.KEY_RIGHT: 3,
                       'q': 4, -1: None},  # quit
      delay=200, colour_fg=COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
