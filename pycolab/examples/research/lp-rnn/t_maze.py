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

"""T-mazes of varying difficulty.

In this variation of the classic T-maze task, the agent starts in a small
chamber. A cue displays indicating which arm of the T maze to go down. Soon
(configurable), a blue "teleporter" appears. As soon as the agent traverses the
teleporter, the cue disappears, and the agent is transported into a "limbo" cell
where it is completely immobilised for a time. Before long (configurable), the
agent is transported again to the T-maze itself and must go down the arm cued at
the start of the episode.

The `--difficulty` flag selects between six different T-mazes which differ only
in size. A larger maze presumably will require better exploration for the agent
to solve.

NOTE: This game achieves egocentric scrolling via pycolab's "scrolly"
infrastructure. The newer "cropping" method is a much easier way to make games
with scrolling.  Please refer to `examples/better_scrolly_maze.py` for a better
example of cropping at work.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import curses
import random
import sys

import numpy as np
from pycolab import ascii_art
from pycolab import human_ui
from pycolab import rendering
from pycolab import things as plab_things
from pycolab.prefab_parts import drapes as prefab_drapes
from pycolab.prefab_parts import sprites as prefab_sprites


if __name__ == '__main__':  # Avoid defining flags when used as a library.
  parser = argparse.ArgumentParser(
      description='Play T-maze.', epilog=(
          'NOTE: Default options configure the game as the agents in the paper '
          'played it. These settings may not be much fun for humans, though.'))
  parser.add_argument('--difficulty', metavar='d', type=int, default=4,
                      help='Difficulty setting. Higher=harder.')
  parser.add_argument('--cue_after_teleport', action='store_true',
                      help='Show cue after teleport.')
  parser.add_argument('--timeout_frames', metavar='t', type=int, default=1000,
                      help='Frames before game times out (-1 for infinity).')
  parser.add_argument('--teleport_delay', metavar='t', type=int, default=50,
                      help='Frames before teleporter "opens".')
  parser.add_argument('--limbo_time', metavar='t', type=int, default=280,
                      help='Time in limbo while teleporting.')
  FLAGS = parser.parse_args()


# pylint: disable=line-too-long,bad-continuation
MAZE_ART = [
#    | 0       | 10      | 20      | 30      | 40      | 50      | 60      | 70      | 80      | 90      | 100     | 110     | 120     | 130     | 140     | 150     | 160     | 170     | 180     | 190
    '                                                                                                                                                                                               ',  # 0
    '                                                                                                                                       ##   #   ##                                             ',
    '                                                                                                                                         ## # ##                                               ',
    '                                                                                         +  #####                                          ###                                                 ',
    '                                                                                            #ttt#                                      ##### #####                                             ',  # 4
    '                                                                                            #   #                                          ###                                                 ',
    '                                                                                            # P #                                        ## # ##                                               ',
    '                                                                                            #####                                      ##   #   ##                                             ',  # 7
    '                                                                                                                                                                                               ',
    '                                                                                                                                                                                               ',
    '***********************************************************************************************************************************************************************************************',  # 10
    '***********************************************************************************************************************************************************************************************',
    '************************************************************************************#####################**************************************************************************************',
    '************************************************************************************#                   #**************************************************************************************',
    '************************************************************************************#                   #**************************************************************************************',
    '************************************************************************************#   #############   #**************************************************************************************',  # 15
    '************************************************************************************#   #***********#   #**************************************************************************************',
    '************************************************************************************#   #***********#   #**************************************************************************************',
    '************************************************************************************#lll#***********#rrr#**************************************************************************************',
    '************************************************************************************#####***********#####**************************************************************************************',
    '***********************************************************************************************************************************************************************************************',  # 20
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '*******************************************************************************###############################*********************************************************************************',
    '*******************************************************************************#                             #*********************************************************************************',
    '*******************************************************************************#                             #*********************************************************************************',  # 25
    '*******************************************************************************#   #######################   #*********************************************************************************',
    '*******************************************************************************#   #*********************#   #*********************************************************************************',
    '*******************************************************************************#   #*********************#   #*********************************************************************************',
    '*******************************************************************************#lll#*********************#rrr#*********************************************************************************',
    '*******************************************************************************#####*********************#####*********************************************************************************',  # 30
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '************************************************************************#############################################**************************************************************************',
    '************************************************************************#                                           #**************************************************************************',  # 35
    '************************************************************************#                                           #**************************************************************************',
    '************************************************************************#   #####################################   #**************************************************************************',
    '************************************************************************#   #***********************************#   #**************************************************************************',
    '************************************************************************#   #***********************************#   #**************************************************************************',
    '************************************************************************#lll#***********************************#rrr#**************************************************************************',  # 40
    '************************************************************************#####***********************************#####**************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************#######################################################################*************************************************************',  # 45
    '***********************************************************#                                                                     #*************************************************************',
    '***********************************************************#                                                                     #*************************************************************',
    '***********************************************************#   ###############################################################   #*************************************************************',
    '***********************************************************#   #*************************************************************#   #*************************************************************',
    '***********************************************************#   #*************************************************************#   #*************************************************************',  # 50
    '***********************************************************#lll#*************************************************************#rrr#*************************************************************',
    '***********************************************************#####*************************************************************#####*************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',  # 55
    '***************************************#################################################################################################################***************************************',
    '***************************************#                                                                                                               #***************************************',
    '***************************************#                                                                                                               #***************************************',
    '***************************************#   #########################################################################################################   #***************************************',
    '***************************************#   #*******************************************************************************************************#   #***************************************',  # 60
    '***************************************#   #*******************************************************************************************************#   #***************************************',
    '***************************************#lll#*******************************************************************************************************#rrr#***************************************',
    '***************************************#####*******************************************************************************************************#####***************************************',
    '***********************************************************************************************************************************************************************************************',
    '***********************************************************************************************************************************************************************************************',  # 65
    '***********************************************************************************************************************************************************************************************',
    '***#########################################################################################################################################################################################***',
    '***#                                                                                                                                                                                       #***',
    '***#                                                                                                                                                                                       #***',
    '***#   #################################################################################################################################################################################   #***',  # 70
    '***#   #*******************************************************************************************************************************************************************************#   #***',
    '***#   #*******************************************************************************************************************************************************************************#   #***',
    '***#lll#*******************************************************************************************************************************************************************************#rrr#***',
    '***#####*******************************************************************************************************************************************************************************#####***',
    '***********************************************************************************************************************************************************************************************',  # 75
    '***********************************************************************************************************************************************************************************************',
]
# pylint: enable=line-too-long,bad-continuation


# These are big blocks that cue the player which direction to move in the maze.
CUE_ART = [
    '           ',
    '           ',
    '           ',
    '           ',
    'QQ       QQ',
    'QQ       QQ',
    'QQ       QQ',
]


# The initial teleporter and all goals look the same. Also, the "dirt" and the
# maze walls look the same.
REPAINT_MAPPING = {'t': '~', 'l': '~', 'r': '~', '*': '#'}


# These colours are only for humans to see in the CursesUi.
COLOURS = {' ': (0, 0, 0),      # Black background
           '#': (764, 0, 999),  # Maze walls
           'P': (0, 999, 999),  # This is you, the player
           'Q': (0, 999, 0),    # Cue blocks
           '~': (0, 0, 999)}    # Teleporter and goals


def make_game(level, cue_after_teleport,
              timeout_frames=-1,
              teleport_delay=0,
              limbo_time=10):
  """Builds and returns a T-maze for the selected level."""
  # A helper object that helps us with Scrolly-related setup paperwork.
  scrolly_info = prefab_drapes.Scrolly.PatternInfo(
      MAZE_ART, CUE_ART,
      board_northwest_corner_mark='+', what_lies_beneath=' ')

  walls_kwargs = scrolly_info.kwargs('#')
  speckle_kwargs = scrolly_info.kwargs('*')
  teleporter_kwargs = scrolly_info.kwargs('t')
  left_kwargs = scrolly_info.kwargs('l')
  right_kwargs = scrolly_info.kwargs('r')
  player_position = scrolly_info.virtual_position('P')

  engine = ascii_art.ascii_art_to_game(
      CUE_ART, what_lies_beneath=' ',
      sprites={
          'P': ascii_art.Partial(PlayerSprite, player_position)},
      drapes={
          'Q': ascii_art.Partial(CueDrape, cue_after_teleport),
          '#': ascii_art.Partial(MazeDrape, **walls_kwargs),
          '*': ascii_art.Partial(SpeckleDrape, **speckle_kwargs),
          't': ascii_art.Partial(TeleporterDrape,
                                 level, teleport_delay, limbo_time,
                                 **teleporter_kwargs),
          'l': ascii_art.Partial(GoalDrape, 'left', **left_kwargs),
          'r': ascii_art.Partial(GoalDrape, 'right', **right_kwargs)},
      update_schedule=[['Q', '#', '*'], ['P'], ['l', 't', 'r']],
      z_order='*#ltrQP')

  # Store timeout frames in the Plot so all sprites and drapes can access it.
  engine.the_plot['timeout_frames'] = (
      float('inf') if timeout_frames < 0 else timeout_frames)

  return engine


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player, the maze explorer."""

  def __init__(self, corner, position, character, virtual_position):
    """Constructor: player is egocentric and can't walk through walls."""
    super(PlayerSprite, self).__init__(
        corner, position, character, egocentric_scroller=True, impassable='#')
    self._teleport(virtual_position)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del backdrop, things, layers  # Unused

    if 0 <= the_plot.frame - the_plot.get('teleportation_order_frame', -1) <= 1:
      self._stay(board, the_plot)  # See PseudoTeleportingScrolly docstring.
    elif actions == 1:    # go upward?
      self._north(board, the_plot)
    elif actions == 2:  # go downward?
      self._south(board, the_plot)
    elif actions == 3:  # go leftward?
      self._west(board, the_plot)
    elif actions == 4:  # go rightward?
      self._east(board, the_plot)
    elif actions == 5:  # do nothing?
      self._stay(board, the_plot)
    elif actions in [0, 6]:  # quit the game?
      the_plot['timeout_frames'] = the_plot.frame + 1


class CueDrape(plab_things.Drape):
  """Cues the player to seek the left or right goal.

  Also responsible for choosing which goal the player should seek in the first
  place. This choice is noted in the `which_goal` attribute of this Object.

  Also imposes a very slight penalty for simply existing.
  """

  def __init__(self, curtain, character, cue_after_teleport):
    super(CueDrape, self).__init__(curtain, character)

    # Choose the goal direction and blank out half the cue to indicate which
    # direction the player should go.
    self.which_goal = 'left' if random.random() < 0.5 else 'right'
    if self.which_goal == 'left':
      self.curtain[:, 6:] = False
    else:
      self.curtain[:, :6] = False

    # Mark whether we should disappear after the player teleports.
    self._cue_after_teleport = cue_after_teleport

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Just clears the cue after teleport, if desired.
    if not self._cue_after_teleport and the_plot.get('yo_we_have_teleported'):
      del the_plot['yo_we_have_teleported']
      self.curtain[:] = False

    # If it's time to time out, end the episode. Otherwise, incur a penalty for
    # doing nothing. But never award a score on the first or last frame, since
    # FlowEnvironment is buggy and can't handle it (at least not on the first).
    if the_plot.frame >= the_plot['timeout_frames']:
      the_plot.terminate_episode()
    elif the_plot.frame > 1:
      the_plot.add_reward(-0.001)


class PseudoTeleportingScrolly(prefab_drapes.Scrolly):
  """A scrolling `Drape` that pretends to support teleportation.

  So `prefab_drapes.Scrolly` does NOT like motions whose dx and dy are greater
  in magnitude than 1. Well, if you can't teleport within the scenery, we can at
  least pretend to do this by moving the entire scenery! Because `Scrolly`s can
  do whatever they please to their whole pattern. Sure, the `Scrolly` superclass
  tends to assume that the pattern is static, but we won't move the scenery
  around in a way that gets us into trouble. For best results, this means that
  the same motion constraints (i.e. walls in the way) should be present for all
  egocentric sprites both before and after the teleport.

  This superclass effectively establishes a protocol for teleportation. All
  subclasses should call its `update` before doing their own updates: if a
  "teleportation order" is found in the Plot, the method will `np.roll` the
  scenery to obey the order. None of the fancy safety checking stuff that comes
  along with the scrolling protocol is here. No sprites are moved to compensate
  for the motion. Also, take care not to scroll the scenery in a way that gives
  a `MazeWalker` a way to wander off of the screen...

  Any subclass can put in a teleportation order (to be obeyed in the next game
  iteration) via the `place_teleportation_order` method.

  All MazeWalker sprites and Scrolly drapes are advised to execute `_stay`
  commands during the frame specified in `the_plot['teleportation_order_frame']`
  and the frame immediately after. Otherwise you may walk through walls.
  Sorry about that.
  """

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Is there a teleportation order for this frame?
    if the_plot.get('teleportation_order_frame', -1) != the_plot.frame: return
    row_shift, col_shift = the_plot['teleportation_order']
    self.whole_pattern[:] = np.roll(self.whole_pattern, -row_shift, axis=0)
    self.whole_pattern[:] = np.roll(self.whole_pattern, -col_shift, axis=1)

  def place_teleportation_order(self, the_plot, row_shift, col_shift):
    """Order a teleportation to take place on the next game iteration.

    Args:
      the_plot: the game's `Plot` object.
      row_shift: number of rows to shift the scenery upward. Can be negative.
      col_shift: number of columns to shift the scenery left. Can be negative.
    """
    the_plot['teleportation_order_frame'] = the_plot.frame + 1
    the_plot['teleportation_order'] = (row_shift, col_shift)


class MazeDrape(PseudoTeleportingScrolly):
  """A scrolling `Drape` handling the maze scenery."""

  def __init__(self, *args, **kwargs):
    """Just eliminates the scroll margins."""
    super(MazeDrape, self).__init__(*args, scroll_margins=None, **kwargs)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    super(MazeDrape, self).update(
        actions, board, layers, backdrop, things, the_plot)

    if 0 <= the_plot.frame - the_plot.get('teleportation_order_frame', -1) <= 1:
      self._stay(the_plot)  # See note in PseudoTeleportingScrolly docstring.
    elif actions == 1:    # is the player going upward?
      self._north(the_plot)
    elif actions == 2:  # is the player going downward?
      self._south(the_plot)
    elif actions == 3:  # is the player going leftward?
      self._west(the_plot)
    elif actions == 4:  # is the player going rightward?
      self._east(the_plot)
    elif actions == 5:  # is the player doing nothing?
      self._stay(the_plot)


class SpeckleDrape(PseudoTeleportingScrolly):
  """More scenery: this is just background with a nice speckle pattern."""

  def __init__(self, *args, **kwargs):
    """Just speckles the background scenery and eliminates scroll margins."""
    super(SpeckleDrape, self).__init__(*args, scroll_margins=None, **kwargs)
    self.whole_pattern[np.random.rand(*self.whole_pattern.shape) < 0.4] = False

  def update(self, actions, board, layers, backdrop, things, the_plot):
    super(SpeckleDrape, self).update(
        actions, board, layers, backdrop, things, the_plot)

    if 0 <= the_plot.frame - the_plot.get('teleportation_order_frame', -1) <= 1:
      self._stay(the_plot)  # See note in PseudoTeleportingScrolly docstring.
    elif actions == 1:    # is the player going upward?
      self._north(the_plot)
    elif actions == 2:  # is the player going downward?
      self._south(the_plot)
    elif actions == 3:  # is the player going leftward?
      self._west(the_plot)
    elif actions == 4:  # is the player going rightward?
      self._east(the_plot)
    elif actions == 5:  # is the player doing nothing?
      self._stay(the_plot)


class TeleporterDrape(PseudoTeleportingScrolly):
  """A scrolling `Drape` handling the teleporter."""

  def __init__(self, curtain, character, level, teleport_delay, limbo_time,
               *args, **kwargs):
    """The `level` arg determines which maze we warp to."""
    super(TeleporterDrape, self).__init__(
        curtain, character, *args, scroll_margins=None, **kwargs)

    # If there is a delay before the teleporter is available, we save the
    # curtain supplied to the constructor (containing the visible teleporter)
    # and replace it with an empty curtain.
    self._teleport_delay = teleport_delay
    if self._teleport_delay > 0:
      self._saved_whole_pattern = self.whole_pattern.copy()
      self.whole_pattern[:] = False

    # Save the number of frames we have left in "limbo" whilst teleporting.
    self._limbo_countdown = limbo_time
    # Are we in limbo right now?
    self._in_limbo = False

    # The row and column containing the "limbo" cell.
    self._limbo_row = 4
    self._limbo_col = 140
    # The distance from the column of the limbo cell to the centre of any
    # of the goal selection hallways.
    self._dx = -46
    # The distance from the row of the limbo cell to the goal selection
    # hallway corresponding to the chosen difficulty level.
    self._dy = 11 * level + 9
    if (self._dy + 5) > self.whole_pattern.shape[0]: raise ValueError(
        'There is no {} difficulty level.'.format(level))

  def update(self, actions, board, layers, backdrop, things, the_plot):
    super(TeleporterDrape, self).update(
        actions, board, layers, backdrop, things, the_plot)

    # If there is a delay before the teleporter is available, count it down and
    # then show the teleporter once the delay expires.
    if self._teleport_delay > 0:
      self._teleport_delay -= 1
      if self._teleport_delay <= 0:
        np.copyto(self.whole_pattern, src=self._saved_whole_pattern)

    if 0 <= the_plot.frame - the_plot.get('teleportation_order_frame', -1) <= 1:
      self._stay(the_plot)  # See note in PseudoTeleportingScrolly docstring.
    elif actions == 1:    # is the player going upward?
      self._north(the_plot)
    elif actions == 2:  # is the player going downward?
      self._south(the_plot)
    elif actions == 3:  # is the player going leftward?
      self._west(the_plot)
    elif actions == 4:  # is the player going rightward?
      self._east(the_plot)
    else:  # is the player doing nothing or quitting?
      self._stay(the_plot)

    # If the player has reached the teleporter, teleport them and leave a note
    # in the plot (besides helping us keep track, it also tells the cue drape to
    # hide the cues, if so configured.
    if not the_plot.get('yo_we_have_teleported'):      # Not teleported yet?
      player_pattern_position = self.pattern_position_postscroll(
          things['P'].position, the_plot)
      if self.whole_pattern[player_pattern_position]:  # Player on teleporter?
        the_plot['yo_we_have_teleported'] = True       # We'll teleport now.
        if self._limbo_countdown <= 0:  # Bypass limbo, go straight to the maze.
          self.place_teleportation_order(
              the_plot, row_shift=self._dy, col_shift=0)
        else:                           # No bypass, go to limbo!
          self._in_limbo = True
          self.place_teleportation_order(
              the_plot,
              row_shift=(self._limbo_row - player_pattern_position.row),
              col_shift=(self._limbo_col - player_pattern_position.col))

    # If we're in limbo, wait until we can get out and then teleport to the
    # appropriate goal selection hallway.
    if self._in_limbo:
      self._limbo_countdown -= 1
      if self._limbo_countdown == 0:
        self._in_limbo = False
        self.place_teleportation_order(
            the_plot, row_shift=self._dy, col_shift=self._dx)


class GoalDrape(PseudoTeleportingScrolly):
  """A Drape for handling the goal pads."""

  def __init__(self, curtain, character, name, *args, **kwargs):
    """The `name` arg will be matched against the cue drape's chosen goal."""
    super(GoalDrape, self).__init__(
        curtain, character, *args, scroll_margins=None, **kwargs)
    self._name = name

  def update(self, actions, board, layers, backdrop, things, the_plot):
    super(GoalDrape, self).update(
        actions, board, layers, backdrop, things, the_plot)

    # If the player has reached the goal, assign a reward and prepare to
    # terminate the episode. (We can't terminate it ourselves because
    # FlowEnvironment maybe can't deal with terminating on a reward.)
    player_pattern_position = self.pattern_position_prescroll(
        things['P'].position, the_plot)
    if (self.whole_pattern[player_pattern_position] and
        the_plot.frame < the_plot['timeout_frames']):
      the_plot.add_reward(1.0 if self._name == things['Q'].which_goal else -1.0)
      the_plot['timeout_frames'] = the_plot.frame + 1

    if 0 <= the_plot.frame - the_plot.get('teleportation_order_frame', -1) <= 1:
      self._stay(the_plot)  # See note in PseudoTeleportingScrolly docstring.
    elif actions == 1:    # is the player going upward?
      self._north(the_plot)
    elif actions == 2:  # is the player going downward?
      self._south(the_plot)
    elif actions == 3:  # is the player going leftward?
      self._west(the_plot)
    elif actions == 4:  # is the player going rightward?
      self._east(the_plot)
    elif actions == 5:  # is the player doing nothing?
      self._stay(the_plot)


def main(argv):
  del argv  # Unused.

  # Build a t_maze game.
  game = make_game(FLAGS.difficulty,
                   FLAGS.cue_after_teleport,
                   FLAGS.timeout_frames,
                   FLAGS.teleport_delay,
                   FLAGS.limbo_time)

  # Build an ObservationCharacterRepainter that will make the teleporter and all
  # the goals look identical.
  repainter = rendering.ObservationCharacterRepainter(REPAINT_MAPPING)

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 1, curses.KEY_DOWN: 2,
                       curses.KEY_LEFT: 3, curses.KEY_RIGHT: 4,
                       -1: 5,
                       'q': 6, 'Q': 6},
      repainter=repainter, delay=100, colour_fg=COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
