# Copyright 2019 the pycolab Authors
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
"""Box-World game for Pycolab.

See README.md for more details.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import itertools
import string
import sys
import numpy as np

from pycolab import ascii_art
from pycolab import human_ui
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites

if __name__ == '__main__':  # Avoid defining flags when used as a library.
  parser = argparse.ArgumentParser(description='Play Box-World.')
  parser.add_argument(
      '--grid_size', type=int, default=12, help='height and width of the grid.')
  parser.add_argument(
      '--solution_length',
      nargs='+',
      type=int,
      default=(1, 2, 3, 4),
      help='number of boxes in the path to the goal.')
  parser.add_argument(
      '--num_forward',
      nargs='+',
      type=int,
      default=(0, 1, 2, 3, 4),
      help='possible values for num of forward distractors.')
  parser.add_argument(
      '--num_backward',
      nargs='+',
      type=int,
      default=(0,),
      help='possible values for num of backward distractors.')
  parser.add_argument(
      '--branch_length',
      type=int,
      default=1,
      help='length of forward distractor branches.')
  parser.add_argument(
      '--max_num_steps',
      type=int,
      default=120,
      help='number of steps before the episode is halted.')
  parser.add_argument(
      '--random_state',
      type=int,
      default=None,
      help='random number generator state.')
  FLAGS = parser.parse_args()

# Module constants
GEM = '*'
PLAYER = '.'
BACKGROUND = ' '
BORDER = '#'

COLORS = [(700, 350, 350), (700, 454, 350), (700, 559, 350), (700, 664, 350),
          (629, 700, 350), (524, 700, 350), (420, 700, 350), (350, 700, 384),
          (350, 700, 490), (350, 700, 595), (350, 700, 700), (350, 594, 700),
          (350, 490, 700), (350, 384, 700), (419, 350, 700), (524, 350, 700),
          (630, 350, 700), (700, 350, 665), (700, 350, 559), (700, 350, 455)]

MAX_NUM_KEYS = len(COLORS)
KEYS = list(string.ascii_lowercase[:MAX_NUM_KEYS])
LOCKS = list(string.ascii_uppercase[:MAX_NUM_KEYS])

OBJECT_COLORS = {
    PLAYER: (500, 500, 500),
    GEM: (999, 999, 999),
    BACKGROUND: (800, 800, 800),
    BORDER: (0, 0, 0),
}
OBJECT_COLORS.update({k: v for (k, v) in zip(KEYS, COLORS)})
OBJECT_COLORS.update({k: v for (k, v) in zip(LOCKS, COLORS)})

REWARD_GOAL = 10.
REWARD_STEP = 0.
REWARD_OPEN_CORRECT = 1.
REWARD_OPEN_WRONG = -1.

WALL_WIDTH = 1

MAX_PLACEMENT_TRIES = 200
MAX_GENERATION_TRIES = 200

NORTH = (-1, 0)
EAST = (0, 1)
SOUTH = (1, 0)
WEST = (0, -1)

ACTION_NORTH = 0
ACTION_SOUTH = 1
ACTION_WEST = 2
ACTION_EAST = 3
ACTION_DELAY = -1

ACTION_MAP = {
    ACTION_NORTH: NORTH,
    ACTION_SOUTH: SOUTH,
    ACTION_WEST: WEST,
    ACTION_EAST: EAST,
}


class PlayerSprite(prefab_sprites.MazeWalker):
  """A `Sprite` for the player.

  This `Sprite` simply ties actions to moving.
  """

  def __init__(self, corner, position, character, grid_size, x, y, distractors,
               max_num_steps):
    """Initialise a PlayerSprite.

    Args:
      corner: standard `Sprite` constructor parameter.
      position: standard `Sprite` constructor parameter.
      character: standard `Sprite` constructor parameter.
      grid_size: int, height and width of the grid.
      x: int, initial player x coordinate on the grid.
      y: int, initial player y coordinate on the grid.
      distractors: <desc>.
      max_num_steps: int, number of steps before the episode is halted.
    """
    # Indicate to the superclass that we can't walk off the board.
    super(PlayerSprite, self).__init__(
        corner, [y, x], character, impassable=BORDER, confined_to_board=True)
    self.distractors = distractors
    self._max_num_steps = max_num_steps
    self._step_counter = 0

  def _in_direction(self, direction, board):
    """Report character in the direction of movement and its coordinates."""
    new_position = np.array(self.position) + direction
    char = chr(board[new_position[0], new_position[1]])
    if char == BORDER:
      return None, None
    else:
      return char, new_position.tolist()

  def update(self, actions, board, layers, backdrop, things, the_plot):
    del backdrop  # Unused.

    # Only actually move if action is one of the 4 directions of movement.
    # Action could be -1, in which case we skip this altogether.
    if actions in range(4):
      # Add penalty per step.
      the_plot.add_reward(REWARD_STEP)

      direction = ACTION_MAP[actions]
      target_character, target_position = self._in_direction(direction, board)
      # This will return None if target_character is None
      target_thing = things.get(target_character)
      inventory_item = chr(board[0, 0])

      # Moving the player can only occur under 3 conditions:
      # (1) Move if there is nothing in the way.
      if not target_thing:
        self._move(board, the_plot, direction)
      else:
        # (2) If there is a lock in the way, only move if you hold the key that
        # opens the lock.
        is_lock = target_character in LOCKS
        if is_lock and inventory_item == target_thing.key_that_opens:
          self._move(board, the_plot, direction)
        # (3) If there is a gem or key in the way, only move if that thing is
        # not locked.
        thing_is_locked = target_thing.is_locked_at(things, target_position)
        if not is_lock and not thing_is_locked:
          self._move(board, the_plot, direction)

      self._step_counter += 1

      # Episode terminates if maximum number of steps is reached.
      if self._step_counter > self._max_num_steps:
        the_plot.terminate_episode()

      # Inform plot of overlap between player and thing.
      if target_thing:
        the_plot['over_this'] = (target_character, self.position)


class BoxThing(plab_things.Drape):
  """Base class for locks, keys and gems."""

  def __init__(self, curtain, character, x, y):
    super(BoxThing, self).__init__(curtain, character)
    self.curtain[y][x] = True

  def is_locked_at(self, things, position):
    """Check if a key or gem is locked at a given position."""
    y, x = position
    # Loop through all possible locks that can be locking this key or gem.
    for lock_chr in things.keys():
      if lock_chr in LOCKS and things[lock_chr].curtain[y][x + 1]:
        return True
    return False

  def where_player_over_me(self, the_plot):
    """Check if player is over this thing. If so, returns the coordinates."""
    over_this = the_plot.get('over_this')
    if over_this:
      character, (y, x) = over_this
      if character == self.character and self.curtain[y][x]:
        return y, x
    else:
      return False


class GemDrape(BoxThing):
  """The gem."""

  def update(self, actions, board, layers, backdrop, things, the_plot):
    if self.where_player_over_me(the_plot):
      the_plot.add_reward(REWARD_GOAL)
      the_plot.terminate_episode()


class KeyDrape(BoxThing):
  """The keys."""

  def update(self, actions, board, layers, backdrop, things, the_plot):
    position = self.where_player_over_me(the_plot)
    if position:
      inventory_item = chr(board[0, 0])
      if inventory_item in KEYS:
        things[inventory_item].curtain[0][0] = False
      self.curtain[position[0]][position[1]] = False
      self.curtain[0][0] = True


class LockDrape(BoxThing):
  """The locks."""

  def __init__(self, curtain, character, x, y):
    super(LockDrape, self).__init__(curtain, character, x, y)
    self.key_that_opens = KEYS[LOCKS.index(self.character)]

  def update(self, actions, board, layers, backdrop, things, the_plot):
    position = self.where_player_over_me(the_plot)
    if position:
      self.curtain[position[0]][position[1]] = False
      inventory_item = chr(board[0, 0])
      things[inventory_item].curtain[0][0] = False
      if (position[1], position[0]) in things[PLAYER].distractors:
        the_plot.add_reward(REWARD_OPEN_WRONG)
        the_plot.terminate_episode()
      else:
        the_plot.add_reward(REWARD_OPEN_CORRECT)


def _sample_keys_locks_long(rand,
                            solution_length_range,
                            num_forward_range,
                            num_backward_range,
                            branch_length=1):
  """Randomly sample a new problem."""

  solution_length = rand.choice(solution_length_range)
  num_forward = rand.choice(num_forward_range)
  num_backward = rand.choice(num_backward_range)

  locks = list(range(solution_length + 1))
  keys = list(range(1, solution_length + 1)) + [-1]

  # Forward distractors
  for _ in range(num_forward):
    lock = rand.choice(range(1, solution_length + 1))
    for _ in range(branch_length):
      key = None
      while key is None or key == lock:
        key = rand.choice(range(solution_length + 1, MAX_NUM_KEYS))
      locks.append(lock)
      keys.append(key)
      lock = key

  # Backward distractors. Note that branch length is not implemented here.
  for _ in range(num_backward):
    key = rand.choice(range(1, solution_length + 1))
    lock = rand.choice(range(solution_length + 1, MAX_NUM_KEYS))
    locks.append(lock)
    keys.append(key)

  return (solution_length, np.array([locks, keys]).T)


def _check_spacing(art, x, y):
  """Check that there's room for key and adjacent lock (incl. surround)."""
  bg = BACKGROUND
  space_for_key = all(
      art[i][j] == bg
      for i, j in itertools.product(range(y - 1, y + 2), range(x - 1, x + 2)))
  also_space_for_box = all(art[i][x + 2] == bg for i in range(y - 1, y + 2))
  return space_for_key and also_space_for_box


def _generate_random_game(rand, grid_size, solution_length, num_forward,
                          num_backward, branch_length, max_num_steps):
  """Generate game proceduraly; aborts if `MAX_PLACEMENT_TRIES` is reached."""

  # Sample new problem.
  solution_length, locks_keys = _sample_keys_locks_long(rand,
                                                        solution_length,
                                                        num_forward,
                                                        num_backward,
                                                        branch_length)

  # By randomizing the list of keys and locks we use all the possible colors.
  key_lock_ids = list(zip(KEYS, LOCKS))
  rand.shuffle(key_lock_ids)

  full_map_size = grid_size + WALL_WIDTH * 2
  art = [
      [BACKGROUND for i in range(full_map_size)] for _ in range(full_map_size)
  ]

  art = np.array(art)
  art[:WALL_WIDTH, :] = BORDER
  art[-WALL_WIDTH:, :] = BORDER
  art[:, :WALL_WIDTH] = BORDER
  art[:, -WALL_WIDTH:] = BORDER

  drapes = {}
  distractors = []
  placement_tries = 0

  # Place items necessary for the sampled problem
  for i, (l, k) in enumerate(locks_keys):
    is_distractor = False
    if i > solution_length:
      is_distractor = True
    placed = False
    while not placed:
      if placement_tries > MAX_PLACEMENT_TRIES:
        return False
      x = rand.randint(0, grid_size - 3) + WALL_WIDTH
      y = rand.randint(1, grid_size - 1) + WALL_WIDTH
      if _check_spacing(art, x, y):
        placed = True
        # Check if box contains the gem
        if k == -1:
          art[y][x] = GEM
          drapes[GEM] = ascii_art.Partial(GemDrape, x=x, y=y)
        else:
          key = key_lock_ids[k - 1][0]
          art[y][x] = key
          drapes[key] = ascii_art.Partial(KeyDrape, x=x, y=y)
        # Check if box has a lock
        if l != 0:
          lock = key_lock_ids[l - 1][1]
          art[y][x + 1] = lock
          drapes[lock] = ascii_art.Partial(LockDrape, x=x + 1, y=y)
          if is_distractor:
            distractors.append((x + 1, y))
      else:
        placement_tries += 1

  # Place player
  placed = False
  while not placed:
    if placement_tries > MAX_PLACEMENT_TRIES:
      return False
    x = rand.randint(0, grid_size - 1) + WALL_WIDTH
    y = rand.randint(1, grid_size - 1) + WALL_WIDTH
    if art[y][x] == BACKGROUND:
      sprites = {
          PLAYER:
              ascii_art.Partial(PlayerSprite, grid_size, x, y, distractors,
                                max_num_steps)
      }
      placed = True
      art[y][x] = PLAYER
    else:
      placement_tries += 1

  order = sorted(drapes.keys())
  update_schedule = [PLAYER] + order
  z_order = order + [PLAYER]

  art_as_list_of_strings = []
  for art_ in art:
    art_as_list_of_strings.append(''.join(art_))
  art = art_as_list_of_strings

  art = [''.join(a) for a in art]
  game = ascii_art.ascii_art_to_game(
      art=art,
      what_lies_beneath=BACKGROUND,
      sprites=sprites,
      drapes=drapes,
      update_schedule=update_schedule,
      z_order=z_order)
  return game


def make_game(grid_size,
              solution_length,
              num_forward,
              num_backward,
              branch_length,
              random_state=None,
              max_num_steps=120):
  """Create a new Box-World game."""

  if random_state is None:
    random_state = np.random.RandomState(None)

  game = False
  tries = 0
  while tries < MAX_GENERATION_TRIES and not game:
    game = _generate_random_game(
        random_state,
        grid_size=grid_size,
        solution_length=solution_length,
        num_forward=num_forward,
        num_backward=num_backward,
        branch_length=branch_length,
        max_num_steps=max_num_steps)
    tries += 1

  if not game:
    raise RuntimeError('Could not generate game in MAX_GENERATION_TRIES tries.')
  return game


def main(unused_argv):

  game = make_game(
      grid_size=FLAGS.grid_size,
      solution_length=FLAGS.solution_length,
      num_forward=FLAGS.num_forward,
      num_backward=FLAGS.num_backward,
      branch_length=FLAGS.branch_length,
      max_num_steps=FLAGS.max_num_steps,
      random_state=FLAGS.random_state,
  )

  ui = human_ui.CursesUi(
      keys_to_actions={
          'w': ACTION_NORTH,
          's': ACTION_SOUTH,
          'a': ACTION_WEST,
          'd': ACTION_EAST,
          -1: ACTION_DELAY,
      },
      delay=50,
      colour_fg=OBJECT_COLORS)
  ui.play(game)


if __name__ == '__main__':
  main(sys.argv)
