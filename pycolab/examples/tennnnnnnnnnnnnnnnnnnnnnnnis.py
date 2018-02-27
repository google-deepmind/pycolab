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

"""What would it be like to play tennis in a long corridor?

This tennis-like uses a court too big to fit on your screen, so instead you
and your opponent get three separate views: one of your paddle, one of your
opponent's paddle, and one that follows the ball.

The game terminates when either player gets four points.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import random

import enum
import numpy as np

from pycolab import ascii_art
from pycolab import cropping
from pycolab import human_ui
from pycolab import things as plab_things


# pylint: disable=line-too-long
MAZE_ART = [
    '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%',
    '%                   ##                                               # ###   # ###                                                                ###    ###                                              #             %',
    '%   1          #####                                         # ###   ##   #  ##   #  # ###                                                 ###   #      #       ###                                      #              %',
    '%   1   @     #   #    ###                           # ###   ##   #  #    #  #    #  ##   #  # ###                            #     ###   #       #      #     #       ###                               #              %',
    '%                 #   #   #                  # ###   ##   #  #    # #    #  #    #   #    #  ##   #  # ###                         #       #   ###    ###       #     #       ###                  ###  #               %',
    '%                 #  #####   # ###   # ###   ##   #  #    # #    #                  #    #   #    #  ##   #  # ###   # ###    #     #   ###                  ###       #     #       ###    ###   #                     %',
    '%                #   #       ##   #  ##   #  #    # #    #                                  #    #   #    #  ##   #  ##   #   #  ###                                ###       #     #      #       #   #            2   %',
    '%                     ####   #    #  #    # #    #                                                  #    #   #    #  #    #  #                                             ###       #      #   ###                 2   %',
    '%                           #    #  #    #                                                                  #    #  #    #                                                        ###    ###                            %',
    '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%']
# pylint: enable=line-too-long


# These colours are only for humans to see in the CursesUi.
COLOUR_FG = {' ': (0, 0, 0),        # Default black background
             '%': (82, 383, 86),    # Dark green court border
             '#': (123, 574, 129),  # Lighter green court features
             '1': (999, 999, 999),  # White player-1 paddle
             '2': (999, 999, 999),  # White player-2 paddle
             '@': (787, 999, 227)}  # Tennis ball

COLOUR_BG = {'@': (0, 0, 0)}  # So the tennis ball looks like @ and not a block.


class Actions(enum.IntEnum):
  """Actions for paddle movement."""
  STAY = 0
  UP = 1
  DOWN = 2
  QUIT = 3


def make_game():
  """Builds and returns a game of tennnnnnnnnnnnnnnnnnnnnnnnis."""
  return ascii_art.ascii_art_to_game(
      MAZE_ART, what_lies_beneath=' ',
      sprites={
          '@': BallSprite},
      drapes={
          '1': PaddleDrape,
          '2': PaddleDrape},
      update_schedule=['1', '2', '@'])


def make_croppers():
  """Builds and returns three `ObservationCropper`s for tennnn...nnnnis."""
  return [
      # Player 1 view.
      cropping.FixedCropper(
          top_left_corner=(0, 0), rows=10, cols=10),

      # The ball view.
      cropping.ScrollingCropper(
          rows=10, cols=31, to_track=['@'], scroll_margins=(0, None)),

      # Player 2 view.
      cropping.FixedCropper(
          top_left_corner=(0, len(MAZE_ART[0])-10), rows=10, cols=10),
  ]


class BallSprite(plab_things.Sprite):
  """A Sprite that handles the ball, and also scoring and quitting."""

  def __init__(self, corner, position, character):
    super(BallSprite, self).__init__(corner, position, character)
    self._y_shift_modulus = 1       # Every this-many frames...
    self._dy = 0                    # ...shift the ball vertically this amount.
    self._dx = -1                   # Horizontally this amount in *all* frames.
    self._score = np.array([0, 0])  # We keep track of score internally.

  def update(self, actions, board, layers, backdrop, things, the_plot):
    row, col = self._position  # Current ball position.
    reward = np.array([0, 0])  # Default reward for a game step.

    def horizontal_bounce(new_dx):  # Shared actions for horizontal bounces.
      self._y_shift_modulus = random.randrange(1, 6)
      self._dy = random.choice([-1, 1])
      self._dx = new_dx

    # Handle vertical motion.
    self._dy = {1: 1, 8: -1}.get(row, self._dy)  # Bounce off top/bottom walls!
    if the_plot.frame % self._y_shift_modulus == 0: row += self._dy

    # Handle horizontal motion.
    col += self._dx
    # Have we hit a paddle?
    if things['1'].curtain[row, col-1]:
      horizontal_bounce(new_dx=1)
    elif things['2'].curtain[row, col+1]:
      horizontal_bounce(new_dx=-1)
    # Have we hit a wall? Same as for a paddle, but awards the opponent a point.
    elif layers['%'][row, col-1]:
      reward = np.array([0, 1])
      horizontal_bounce(new_dx=1)
    elif layers['%'][row, col+1]:
      reward = np.array([1, 0])
      horizontal_bounce(new_dx=-1)

    # Update the position and the score.
    self._position = self.Position(row=row, col=col)
    the_plot.add_reward(reward)
    self._score += reward

    # Finally, see if a player has won, or if a user wants to quit.
    if any(self._score >= 4): the_plot.terminate_episode()
    if actions is not None and actions.get('quit'): the_plot.terminate_episode()


class PaddleDrape(plab_things.Drape):
  """A Drape that handles a paddle."""

  def __init__(self, curtain, character):
    """Finds out where the paddle is."""
    super(PaddleDrape, self).__init__(curtain, character)
    self._paddle_top = min(np.where(self.curtain)[0])
    self._paddle_col = min(np.where(self.curtain)[1])

  def update(self, actions, board, layers, backdrop, things, the_plot):
    # Move up or down as directed if there is room.
    action = Actions.STAY if actions is None else actions[self.character]
    if action == Actions.UP:
      if self._paddle_top > 1: self._paddle_top -= 1
    elif action == Actions.DOWN:
      if self._paddle_top < 7: self._paddle_top += 1

    # Repaint the paddle. Note "blinking" effect if the ball slips past us.
    self.curtain[:, self._paddle_col] = False
    blink = (things['@'].position.col <= self._paddle_col   # "past" us depends
             if self.character == '1' else                  # on which paddle
             things['@'].position.col >= self._paddle_col)  # we are.
    if not blink or (the_plot.frame % 2 == 0):
      paddle_rows = np.s_[self._paddle_top:(self._paddle_top + 2)]
      self.curtain[paddle_rows, self._paddle_col] = True


def main():
  # Build a game of tennnnnnnnnnnnnnnnnnnnnnnnis.
  game = make_game()
  # Build the croppers we'll use to make the observations.
  croppers = make_croppers()

  # Make a CursesUi to play it with.
  ui = human_ui.CursesUi(
      # Multi-agent arguments don't have to be dicts---they can be just about
      # anything; numpy arrays, scalars, nests, whatever.
      keys_to_actions={
          'r': {'1': Actions.UP, '2': Actions.STAY},
          'f': {'1': Actions.DOWN, '2': Actions.STAY},
          'u': {'1': Actions.STAY, '2': Actions.UP},
          'j': {'1': Actions.STAY, '2': Actions.DOWN},
          'q': {'1': Actions.STAY, '2': Actions.STAY, 'quit': True},
          -1: {'1': Actions.STAY, '2': Actions.STAY},
      },
      delay=33, colour_fg=COLOUR_FG, colour_bg=COLOUR_BG,
      croppers=croppers)

  # Let the game begin!
  ui.play(game)


if __name__ == '__main__':
  main()
