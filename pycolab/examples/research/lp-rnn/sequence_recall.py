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

"""The agent must remember a sequence of lights.

This task is reminiscent of electronic toy memory games from the '70s and '80s.
The player starts out immobilised at the centre of the screen while a sequence
of coloured lights flashes on the four surrounding "pads". After the sequence
ends, the agent is free to move. It must visit the pads in the same order as the
sequence it was just shown, as quickly as possible. If the same pad flashes
twice in a row, then the agent must enter, exit, and re-enter the pad in order
to replicate the sequence.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import curses
import random
import sys

import enum

import numpy as np
from pycolab import ascii_art
from pycolab import human_ui
from pycolab import rendering
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites


if __name__ == '__main__':  # Avoid defining flags when used as a library.
  parser = argparse.ArgumentParser(
      description='Play Sequence Recall.',
      epilog=(
          'NOTE: Default options configure the game as the agents in the paper '
          'played it. These settings may not be much fun for humans, though.'))
  parser.add_argument(
      '--sequence_length', metavar='K', type=int, default=4,
      help='Length of the light sequence the player must learn.')
  parser.add_argument(
      '--demo_light_on_frames', metavar='t', type=int, default=60,
      help='Lights during the "demo" stay on for t frames.')
  parser.add_argument(
      '--demo_light_off_frames', metavar='t', type=int, default=30,
      help='Lights during the "demo" stay off for t frames.')
  parser.add_argument(
      '--pause_frames', metavar='t', type=int, default=1,
      help='Agent is held t frames after the demo before moving.')
  parser.add_argument(
      '--timeout_frames', metavar='t', type=int, default=1000,
      help='Frames before game times out (-1 for infinity).')
  FLAGS = parser.parse_args()


GAME_ART = [
    '#####################',
    '#        222        #',
    '#      2222222      #',
    '#      2222222      #',
    '#      2222222      #',
    '#        222        #',
    '#  111         333  #',
    '#1111111 %%% 3333333#',
    '#1111111 %P% 3333333#',
    '#1111111 %%% 3333333#',
    '#  111         333  #',
    '#        444        #',
    '#      4444444      #',
    '#      4444444      #',
    '#      4444444      #',
    '#        444        #',
    '#####################',
]


# Repaints the WaitForSeekDrape to look identical to the maze walls.
REPAINT_MAPPING = {
    '%': '#',
}


# These colours are only for humans to see in the CursesUi.
COLOURS = {' ': (0, 0, 0),        # Black background
           '#': (764, 0, 999),    # Board walls
           '1': (0, 999, 0),      # Green light
           '2': (999, 0, 0),      # Red light
           '3': (0, 0, 999),      # Blue light
           '4': (999, 999, 0),    # Yellow light
           'M': (300, 300, 300),  # Mask drape (for turning a light "off")
           'P': (0, 999, 999)}    # Player


class _State(enum.Enum):
  """States for the game's internal state machine.

  In the game, states are placed in tuples with arguments like duration, etc.
  """
  # All lights off for some duration. Agent is frozen.
  OFF = 0

  # Specified light on for some duration. Agent is frozen.
  ON = 1

  # Agent is free to move. If they enter a specified light, they get a point. If
  # they enter any other light, they lose a point.
  SEEK = 2

  # Agent is free to move and is currently in one of the lights. This state is
  # basically the game waiting for the agent to leave the light.
  EXIT = 3

  # Game over!
  QUIT = 4


def make_game(sequence_length=4,
              demo_light_on_frames=60,
              demo_light_off_frames=30,
              pause_frames=30,
              timeout_frames=-1):
  """Builds and returns a sequence_recall game."""

  # Sample a game-controlling state machine program.
  program = _make_program(sequence_length,
                          demo_light_on_frames, demo_light_off_frames,
                          pause_frames)

  # Build the game engine.
  engine = ascii_art.ascii_art_to_game(
      GAME_ART, what_lies_beneath=' ',
      sprites={'P': PlayerSprite},
      drapes={'M': MaskDrape,
              '%': WaitForSeekDrape},
      update_schedule=['P', 'M', '%'],
      z_order='MP%')

  # Save the program and other global state in the game's Plot object.
  engine.the_plot['program'] = program
  engine.the_plot['frames_in_state'] = 0  # How long in the current state?
  engine.the_plot['timeout_frames'] = (  # Frames left until the game times out.
      float('inf') if timeout_frames < 0 else timeout_frames)

  return engine


def _make_program(sequence_length,
                  demo_light_on_frames, demo_light_off_frames,
                  pause_frames):
  """Sample a game-controlling state machine program."""
  # Select the sequence of lights that we'll illuminate.
  sequence = [random.choice('1234') for _ in range(sequence_length)]

  # Now create the state machine program that will control the game.
  program = []
  # Phase 1. Present the sequence.
  for g in sequence:
    program.extend([
        (_State.OFF, demo_light_off_frames),   # All lights off.
        (_State.ON, demo_light_on_frames, g),  # Turn on light g
    ])
  # Phase 2. Detain the agent for a little while.
  program.append(
      (_State.OFF, max(1, pause_frames)),  # At least 1 to turn off the light.
  )
  # Phase 3. The agent tries to replicate the sequence.
  for g in sequence:
    program.extend([
        (_State.SEEK, g),  # Agent should try to enter light g.
        (_State.EXIT,),    # Agent must leave whatever light it's in.
    ])
  # Phase 4. Quit the game.
  program[-1] = (_State.QUIT,)  # Replace final EXIT with a QUIT.

  return program


class MaskDrape(plab_things.Drape):
  """A `Drape` for the mask that obscures the game's lights.

  Also controls the state machine and performs score keeping.
  """

  def __init__(self, curtain, character):
    super(MaskDrape, self).__init__(curtain, character)

    # Both of the following to be filled by self._set_up_masks.
    # What the contents of the curtain should be when all lights are off.
    self._all_off_mask = None
    # Which parts of the curtain cover which light.
    self._mask_for_light = {g: None for g in '1234'}

  def _set_up_masks(self, backdrop):
    self._all_off_mask = np.zeros_like(backdrop.curtain, dtype=np.bool)
    for g in '1234':
      mask = (backdrop.curtain == backdrop.palette[g])
      self._mask_for_light[g] = mask
      self._all_off_mask |= mask

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # One-time: set up our mask data.
    if self._all_off_mask is None: self._set_up_masks(backdrop)

    state = the_plot['program'][0][0]  # Get current game state.
    args = the_plot['program'][0][1:]  # Get all arguments for the state.

    # Get player position---it's often useful.
    pos = things['P'].position

    # Increment the number of frames we will have been in this state at the end
    # of this game step.
    the_plot['frames_in_state'] += 1
    frames_in_state = the_plot['frames_in_state']  # Abbreviated

    # Behave as dictated by the state machine.
    if state == _State.QUIT:
      if frames_in_state == 1:              # If we just entered the QUIT state,
        the_plot['timeout_frames'] = 1      #     direct the game to time out.

    elif state == _State.OFF:
      if frames_in_state == 1:              # If we just entered the OFF state,
        self.curtain[:] |= self._all_off_mask  #  turn out all the lights.
      elif frames_in_state >= args[0]:      # If we've been here long enough,
        the_plot['program'].pop(0)          #     move on to the next state.
        the_plot['frames_in_state'] = 0

    elif state == _State.ON:                # If we just entered the ON state,
      if frames_in_state == 1:              #     turn on the specified light.
        self.curtain[:] -= self._mask_for_light[args[1]]
      elif frames_in_state >= args[0]:      # If we've been here long enough,
        the_plot['program'].pop(0)          #     move on to the next state.
        the_plot['frames_in_state'] = 0

    elif state == _State.SEEK:              # In the SEEK state, wait for the
      agent_above = chr(backdrop.curtain[pos])  # agent to enter a light.
      if agent_above != ' ':                    # Entry!
        self.curtain[:] -= self._mask_for_light[agent_above]  # Light goes on.
        the_plot.add_reward(                    # Was it the right light?
            1.0 if agent_above == args[0]       #    Yes, reward for you!
            else 0.0)                           #    No. You get nothing.
        the_plot['program'].pop(0)              # On to the next state.
        the_plot['frames_in_state'] = 0

    elif state == _State.EXIT:              # In the EXIT state, wait for the
      agent_above = chr(backdrop.curtain[pos])  # agent to exit a light.
      if agent_above == ' ':                    # Exit!
        self.curtain[:] |= self._all_off_mask   # All lights go out.
        the_plot['program'].pop(0)              # On to the next state.
        the_plot['frames_in_state'] = 0


class WaitForSeekDrape(plab_things.Drape):
  """A `Drape` that disappears when the game first enters a SEEK state."""

  def update(self, actions, board, layers, backdrop, things, the_plot):
    if (the_plot['frames_in_state'] == 1 and
        the_plot['program'][0][0] == _State.SEEK and
        self.curtain.any()): self.curtain[:] = False


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player.

  This `Sprite` ties actions to going in the four cardinal directions. In
  interactive settings, the user can also quit. `PlayerSprite` also administers
  a small penalty at every timestep to motivate the agent to act quickly.
  Finally, `PlayerSprite` handles episode timeout and all termination.
  """

  def __init__(self, corner, position, character):
    """Tells superclass we can't walk off the board or through walls."""
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='#', confined_to_board=True)

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del layers, backdrop, things  # Unused.

    state = the_plot['program'][0][0]  # Get current game state.

    if actions in [0, 6]:
      # Humans can quit the game at any time.
      the_plot['timeout_frames'] = 1

    elif state in (_State.SEEK, _State.EXIT):
      # But no agent is allowed to move unless the game state permits it.
      if actions == 1:    # go upward?
        self._north(board, the_plot)
      elif actions == 2:  # go downward?
        self._south(board, the_plot)
      elif actions == 3:  # go leftward?
        self._west(board, the_plot)
      elif actions == 4:  # go rightward?
        self._east(board, the_plot)
      elif actions == 5:  # do nothing?
        self._stay(board, the_plot)

    # Quit the game if timeout occurs.
    if the_plot['timeout_frames'] <= 0:
      the_plot.terminate_episode()
    else:
      # Otherwise, add a slight penalty for all episode frames (except the
      # first) to encourage the agent to act efficiently.
      if the_plot.frame > 1: the_plot.add_reward(-0.005)
      the_plot['timeout_frames'] -= 1


def main(argv):
  del argv  # Unused.

  # Build a sequence_recall game.
  game = make_game(FLAGS.sequence_length,
                   FLAGS.demo_light_on_frames,
                   FLAGS.demo_light_off_frames,
                   FLAGS.pause_frames,
                   FLAGS.timeout_frames)

  # Build an ObservationCharacterRepainter that will turn the light numbers into
  # actual colours.
  repainter = rendering.ObservationCharacterRepainter(REPAINT_MAPPING)

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 1, curses.KEY_DOWN: 2,
                       curses.KEY_LEFT: 3, curses.KEY_RIGHT: 4,
                       -1: 5,
                       'q': 6, 'Q': 6},
      delay=100, repainter=repainter, colour_fg=COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
