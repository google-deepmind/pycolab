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

"""Position yourself to catch blocks based on a visual cue.

This game proceeds in two phases. The first phase is a "programming phase",
where the player sees each of the four visual cues (green blocks at the bottom
of the game board) paired randomly with either of two additional visual cues
(larger green blocks just above the cues, called "ball symbols"). These pairings
tell the player what actions they should take in the second phase of the game.

In the second phase of the game, the player must repeatedly move itself up or
down to position itself in front of either of two blocks: a yellow block or a
cyan block. These blocks approach the player from right to left. If the player
"catches" the correct block, it receives a point. The correct block is indicted
by the visual cue shown as the blocks begin to approach the player. If the cue
was paired with the left "ball symbol" during the programming phase, the player
should catch the yellow block; otherwise it should catch the cyan block.

Each episode of "Cued Catch" starts with a different mapping from cues to
blocks.  The player must learn to remember these associations in order to play
the game successfully.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import curses
import random
import sys

from pycolab import ascii_art
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites


# ASCII art for the game board. Not too representative: there is usually some
# cue showing on some part of the board.
GAME_ART = [
    '            ',
    '   P    a   ',
    '        b   ',
    '            ',
    '            ',
    '            ',
    '            ',
]


if __name__ == '__main__':  # Avoid defining flags when used as a library.
  parser = argparse.ArgumentParser(
      description='Play Cued Catch.',
      epilog=(
          'NOTE: Default options configure the game as the agents in the paper '
          'played it. These settings may not be much fun for humans, though.'))
  parser.add_argument('--initial_cue_duration', metavar='t', type=int,
                      default=10, help='Programming cue duration.')
  parser.add_argument('--cue_duration', metavar='t', type=int, default=10,
                      help='Query cue duration.')
  parser.add_argument('--num_trials', metavar='K', type=int, default=100,
                      help='Number of trials per episode.')
  # This flag is for establishing a control that requires no long term memory.
  parser.add_argument('--always_show_ball_symbol', action='store_true',
                      help='Control case: show ball symbols during trials.')
  # This flag is for experiments that require noise-tolerant memory.
  parser.add_argument('--reward_sigma', metavar='s', type=float, default=0.0,
                      help='Stddev for noise to add to ball-catch rewards.')
  # This flag is for experiments that require very long term memory.
  parser.add_argument('--reward_free_trials', metavar='K', type=int, default=40,
                      help='Provide no reward for the first K trials')
  FLAGS = parser.parse_args()


# These colours are only for humans to see in the CursesUi.
COLOURS = {' ': (0, 0, 0),        # Black background
           'P': (999, 999, 999),  # This is you, the player
           'Q': (0, 999, 0),      # Cue blocks
           'a': (999, 999, 0),    # Top ball
           'b': (0, 999, 999)}    # Bottom ball


def make_game(initial_cue_duration, cue_duration, num_trials,
              always_show_ball_symbol=False,
              reward_sigma=0.0,
              reward_free_trials=0):
  return ascii_art.ascii_art_to_game(
      art=GAME_ART,
      what_lies_beneath=' ',
      sprites={'P': ascii_art.Partial(
          PlayerSprite,
          reward_sigma=reward_sigma,
          reward_free_trials=reward_free_trials),
               'a': BallSprite,
               'b': BallSprite},
      drapes={'Q': ascii_art.Partial(
          CueDrape,
          initial_cue_duration, cue_duration, num_trials,
          always_show_ball_symbol)},
      update_schedule=['P', 'a', 'b', 'Q'])


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for our player, the catcher."""

  def __init__(self, corner, position, character,
               reward_sigma=0.0, reward_free_trials=0):
    """Initialise a PlayerSprite.

    Args:
      corner: standard `Sprite` constructor parameter.
      position: standard `Sprite` constructor parameter.
      character: standard `Sprite` constructor parameter.
      reward_sigma: standard deviation of reward for catching the ball (or
          not). A value of 0.0 means rewards with no noise.
      reward_free_trials: number of trials before any reward can be earned.
    """
    super(PlayerSprite, self).__init__(
        corner, position, character, impassable='', confined_to_board=True)
    self._reward_sigma = reward_sigma
    self._trials_till_reward = reward_free_trials

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Our motions are quite constrained: we can only move up or down one spot.
    if actions == 1 and self.virtual_position.row > 1:    # go up?
      self._north(board, the_plot)
    elif actions == 2 and self.virtual_position.row < 2:  # go down?
      self._south(board, the_plot)
    elif actions in [0, 4]:                               # quit the game?
      the_plot.terminate_episode()
    else:                                                 # do nothing?
      self._stay(board, the_plot)                         # (or can't move?)

    # Give ourselves a point if we landed on the correct ball.
    correct_ball = 'a' if the_plot.get('which_ball') == 'top' else 'b'
    if self._reward_sigma:
      if (self.position.col == things[correct_ball].position.col and
          self._trials_till_reward <= 0):
        the_plot.add_reward(
            float(self.position == things[correct_ball].position) +
            random.normalvariate(mu=0, sigma=self._reward_sigma))
      else:
        the_plot.add_reward(0)

    else:
      the_plot.add_reward(int(
          self.position == things[correct_ball].position and
          self._trials_till_reward <= 0
      ))

    # Decrement trials left till reward.
    if (self.position.col == things[correct_ball].position.col and
        self._trials_till_reward > 0):
      self._trials_till_reward -= 1


class BallSprite(plab_things.Sprite):
  """A `Sprite` for the balls approaching the player."""

  def __init__(self, corner, position, character):
    """Mark ourselves as invisible at first."""
    super(BallSprite, self).__init__(corner, position, character)
    # Save start position.
    self._start_position = position
    # But mark ourselves invisible for now.
    self._visible = False

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Wait patiently until the initial programming cues have been shown.
    if not the_plot.get('programming_complete'): return

    # Cues are shown; we are visible now.
    self._visible = True

    # If we're to the left of the player, reposition ourselves back at the start
    # position and tell the cue drape to pick a new correct ball.
    if self.position.col < things['P'].position.col:
      self._position = self._start_position
      the_plot['last_ball_reset'] = the_plot.frame
    else:
      self._position = self.Position(self.position.row, self.position.col - 1)


class CueDrape(plab_things.Drape):
  """"Programs" the player, then chooses correct balls and shows cues.

  The cue drape goes through two phases.

  In the first phase, it presents each of the four cues serially along with a
  symbol that indicates whether the top ball or the bottom ball is the correct
  choice for that cue. (The symbol does not resemble one of the balls.) During
  this phase, no balls appear. Agent actions can move the player but accomplish
  nothing else. Each associational cue presentation lasts for a number of
  timesteps controlled by the `initial_cue_duration` constructor argument.

  Once all four cues have been shown in this way, the second phase presents a
  sequence of `num_trials` fixed-length trials. In each trial, one of the four
  cues is shown for `cue_duration` timesteps, and the two balls advance toward
  the player from the right-hand side of the screen. The agent must position the
  player to "catch" the ball that matches the cue shown at the beginning of the
  trial.

  The two phases can also be visually distinguished by the presence of some
  additional markers on the board.
  """

  _NUM_CUES = 4  # Must divide 12 evenly and be divisible by 2. So, 2, 4, 6, 12.

  def __init__(self, curtain, character,
               initial_cue_duration,
               cue_duration,
               num_trials,
               always_show_ball_symbol):
    super(CueDrape, self).__init__(curtain, character)

    self._initial_cue_duration = initial_cue_duration
    self._cue_duration = cue_duration
    self._num_trials_left = num_trials
    self._always_show_ball_symbol = always_show_ball_symbol

    # Assign balls to each of the cues.
    self._cues_to_balls = random.sample(
        ['top'] * (self._NUM_CUES // 2) + ['bottom'] * (self._NUM_CUES // 2),
        self._NUM_CUES)

    self._phase = 'first'
    # State for first phase.
    self._first_phase_tick = self._NUM_CUES * self._initial_cue_duration
    # State for second phase, initialised to bogus values.
    self._second_phase_cue_choice = -1
    self._second_phase_tick = -1
    self._second_phase_last_reset = -float('inf')

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Show the agent which phase we're in.
    self._show_phase_cue(self._phase)
    # Do phase-specific update.
    if self._phase == 'first':
      self._do_first_phase(the_plot)
    elif self._phase == 'second':
      self._do_second_phase(the_plot)

  ## Phase-specific updates.

  def _do_first_phase(self, the_plot):
    # Iterate through showing each of the cues.
    self._first_phase_tick -= 1  # Decrement number of steps left in this phase.
    cue = self._first_phase_tick // self._initial_cue_duration
    self._show_ball_symbol(self._cues_to_balls[cue])
    self._show_cue(cue)
    # End of phase? Move on to the next phase.
    if self._first_phase_tick <= 0:
      self._phase = 'second'
      the_plot['programming_complete'] = True
      self._second_phase_reset(the_plot)

  def _do_second_phase(self, the_plot):
    self._show_ball_symbol('neither')  # Clear ball symbol.
    # Reset ourselves if the balls have moved beyond the player.
    if the_plot.get('last_ball_reset') > self._second_phase_last_reset:
      self._second_phase_reset(the_plot)
    # Show the cue if it's still visible in this trial.
    if self._second_phase_tick > 0:
      self._show_cue(self._second_phase_cue_choice)
      if self._always_show_ball_symbol: self._show_ball_symbol(
          self._cues_to_balls[self._second_phase_cue_choice])
    else:
      self._show_cue(None)
      self._show_ball_symbol(None)
    # Countdown second phase clock.
    self._second_phase_tick -= 1

  def _second_phase_reset(self, the_plot):
    self._second_phase_cue_choice = random.randrange(self._NUM_CUES)
    the_plot['which_ball'] = self._cues_to_balls[self._second_phase_cue_choice]
    self._second_phase_tick = self._cue_duration
    self._second_phase_last_reset = the_plot.frame
    # Terminate if we've run out of trials.
    if self._num_trials_left <= 0: the_plot.terminate_episode()
    self._num_trials_left -= 1

  ## Display helpers

  def _show_phase_cue(self, phase):
    self.curtain[1:3, :] = False
    if phase == 'first':
      self.curtain[1:3, 0:2] = True
      self.curtain[1:3, -2:] = True
    # No cue for the second phase.

  def _show_ball_symbol(self, ball):
    self.curtain[3:5, :] = False
    if ball == 'top':
      self.curtain[3:5, 0:6] = True
    elif ball == 'bottom':
      self.curtain[3:5, -6:] = True

  def _show_cue(self, cue=None):
    self.curtain[-2:, :] = False
    if 0 <= cue < self._NUM_CUES:
      width = self.curtain.shape[1] // self._NUM_CUES
      l = cue * width
      r = l + width
      self.curtain[-2:, l:r] = True


def main(argv):
  del argv  # Unused.

  # Build a cued_catch game.
  game = make_game(FLAGS.initial_cue_duration,
                   FLAGS.cue_duration, FLAGS.num_trials,
                   FLAGS.always_show_ball_symbol,
                   FLAGS.reward_sigma,
                   FLAGS.reward_free_trials)

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      keys_to_actions={curses.KEY_UP: 1, curses.KEY_DOWN: 2,
                       -1: 3,
                       'q': 4, 'Q': 4},
      delay=200, colour_fg=COLOURS)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
