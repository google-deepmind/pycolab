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

"""The pycolab "Plot" blackboard.

All details are in the docstring for `Plot`.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pycolab.protocols import logging as plab_logging


class Plot(dict):
  """The pycolab "plot" object---a blackboard for communication.

  By design, a game's `Engine`, its `Backdrop`, and its `Sprite`s and `Drape`s
  are not really meant to talk to each other directly; instead, they leave
  messages for each other in the game's `Plot` object. With the exception of
  messages to the `Engine`, these messages are free-form and persistent; in
  fact, let's drop the pretense---a `Plot` is really just a `dict` with some
  extra methods and properties, and to talk to each other, these entities should
  just modify the dict in the usual ways, adding, removing, and modyfing
  whatever entries they like. (Responsibly, of course.)

  (Note: in a limited way, the `Backdrop` and `Sprite`s and `Drape`s are allowed
  to inspect each other, but these inspections should be limited to small,
  read-only interactions via public methods and attributes. This capability is
  only really there to simplify things like getting the row/col coordinates of
  other sprites. Try not to abuse it!)

  (Note 2: Game developers who are designing ways for `Sprite`s, `Drape`s and
  the `Backdrop` to communicate with each other via the `Plot` object might find
  the `setdefault` method on `dict` to be especially useful. Or not.)

  The messages to the Engine have more structure. A `Backdrop`, a `Sprite`, or
  a `Drape` can direct the engine to do any of the following:

  * Change the z-ordering of the `Sprite`s and `Drape`s.
  * Add some quantity to the reward being returned to the player (or player)
    in response to their action.
  * Terminate the game.

  A dedicated method exists within the `Plot` object for all of these actions.

  The `Plot` object also has an imporant role for games that participate in
  `Story`s: values in the `Plot` persist between games; in fact, they are the
  only data guaranteed to do so. Individual games that participate in a `Story`
  also use the `Plot` to control what happens next after they terminate.

  Lastly, the `Plot` object contains a number of public attributes that the
  `Engine` can use to communicate various statistics about the game to the
  various other game entities.
  """

  class _EngineDirectives(object):
    """A container for instructions for modifying an `Engine`'s internal state.

    External code is not meant to manipulate `_EngineDirectives` objects
    directly, but `Engine` and `Plot` objects can do it. Properties of this
    class include:

    * `z_updates`: an indexable of 2-tuples `(c1, c2)`, whose semantics are
      "move the `Sprite` or `Drape` that paints with character `c1` in front of
      the `Sprite` or `Drape` that paints with character `c2`." If `c2` is
      None, the `Sprite` or `Drape` is moved all the way to the back of the
      z-order (i.e. behind everything except the `Backdrop`).
    * `summed_reward`: None, if there is no reward to be reported to the player
      (or players) during a game iteration. Otherwise, this can be any value
      appropriate to the game. If there's ever any chance that more than one
      entity (`Sprite`, `Drape`, or `Backdrop`) would supply a reward during a
      game iteration, the value should probably be of a type that supports the
      `+` operator in a relevant way.
    * `game_over`: a boolean value which... is True until the game is over.
    * `discount`: reinforcement learning discount factor to report to the
      player during a game iteration; typically a fixed value until the end of
      the game is reached, then 0.
    """
    # For fast access
    __slots__ = ('z_updates', 'summed_reward', 'game_over', 'discount')

    def __init__(self):
      """Construct a no-op `_EngineDirectives`.

      Builds an `_EngineDirectives` that indicate that the `Engine` should not
      change any state.
      """
      self.z_updates = []
      self.summed_reward = None
      self.game_over = False
      self.discount = 1.0

  def __init__(self):
    """Construct a new `Plot` object."""
    super(Plot, self).__init__()

    # The current frame actually starts at -1, but before any of the
    # non-`Engine` entities see it, it will have been incremented to 0 for the
    # first frame.
    self._frame = -1

    # Will hold the current update group when the `update` methods of `Sprite`s
    # and `Drape`s are called.
    self._update_group = None

    # For Storys only: holds keys or indices indicating which game preceded
    # the current game, which game is the current game, and which game should
    # be started next after the current game terminates, respectively. A None
    # value for _next_chapter means that the story should terminate after the
    # current game ends.
    #
    # These members are not used if a Story is not underway.
    self._prior_chapter = None
    self._this_chapter = None
    self._next_chapter = None

    # Set an initial set of engine directives (at self._engine_directives),
    # which basically amount to telling the Engine do nothing.
    self._clear_engine_directives()

  ### Public methods for changing global game state. ###

  def change_z_order(self, move_this, in_front_of_that):
    """Tell an `Engine` to change the z-order of some `Sprite`s and/or `Drape`s.

    During a game iteration, the `Backdrop` and each `Sprite` or `Drape` has
    an opportunity to call this method as often as it wants. Each call indicates
    that one `Sprite` or `Drape` should appear in front of another---or in
    front of no other if it should be moved all the way to the back of the
    z-order, behind everything else except for the `Backdrop`.

    These requests are processed at each game iteration after the `Engine` has
    consulted the `Backdrop` and all `Sprite`s and `Layer`s for updates, but
    before the finished observation to be shown to the player (or players) is
    rendered. The requests are processed in the order they are made to the
    `Plot` object, so this ordering of requests:

         '#' in front of '$'
         '$' in front of '%'

    could result in a different `Sprite` or `Drape` being foremost from the
    reverse ordering.

    Args:
      move_this: the character corresponding to the `Sprite` or `Drape` to move
          in the z-order.
      in_front_of_that: the character corresponding to the `Sprite` or `Drape`
          that the moving entity should move in front of, or None if the moving
          entity should go all the way to the back (just in front of the
          `Backdrop`).

    Raises:
      ValueError: if `move_this` or `in_front_of_that` are not both single ASCII
          characters.
    """
    self._value_error_if_character_is_bad(move_this)
    if in_front_of_that is not None:
      self._value_error_if_character_is_bad(in_front_of_that)

    # Construct a new set of engine directives with updated z-update directives.
    self._engine_directives.z_updates.append((move_this, in_front_of_that))

  def terminate_episode(self, discount=0.0):
    """Tell an `Engine` to terminate the current episode.

    During a game iteration, any `Backdrop`, `Sprite`, or `Drape` can call this
    method. Once the `Engine` has finished consulting these entities for
    updates, it will mark the episode as complete, render the final observation,
    and return it to the player (or players).

    Args:
      discount: reinforcement learning discount factor to associate with this
          episode termination; must be in the range [0, 1]. Ordinary episode
          terminations should use the default value 0.0; rarely, some
          environments may use different values to mark interruptions or other
          abnormal termination conditions.

    Raises:
      ValueError: if `discount` is not in the [0,1] range.
    """
    if not 0.0 <= discount <= 1.0:
      raise ValueError('Discount must be in range [0,1].')

    # Construct a new set of engine directives with the death warrant signed.
    self._engine_directives.game_over = True
    self._engine_directives.discount = discount

  def add_reward(self, reward):
    """Add a value to the reward the `Engine` will return to the player(s).

    During a game iteration, any `Backdrop`, `Sprite`, or `Drape` can call this
    method to add value to the reward that the `Engine` will return to the
    player (or players) for having taken the action (or actions) supplied in the
    `actions` argument to `Engine`'s `play` method.

    This value need not be a number, but can be any kind of value appropriate to
    the game.  If there's ever any chance that more than one `Sprite`, `Drape`,
    or `Backdrop` would supply a reward during a game iteration, the value
    should probably be of a type that supports the `+=` operator in a relevant
    way, since this method uses addition to accumulate reward. (For custom
    classes, this typically means implementing the `__iadd__` method.)

    If this method is never called during a game iteration, the `Engine` will
    supply None to the player (or players) as the reward.

    Args:
      reward: reward value to accumulate into the current game iteration's
          reward for the player(s). See discussion for details.
    """
    if self._engine_directives.summed_reward is None:
      self._engine_directives.summed_reward = reward
    else:
      self._engine_directives.summed_reward += reward

  def log(self, message):
    """Log a message for eventual disposal by the game engine user.

    Here, "game engine user" means a user interface or an environment interface,
    which may eventually display the message to an actual human being in a
    useful way (writing it to a file, showing it in a game console, etc.).

    **Calling this method doesn't mean that a log message will appear in the
    process logs.** It's up to your program to collect your logged messages from
    the `Plot` object and dispose of them appropriately.

    See `protocols/logging.py` for more details. (This function is sugar for the
    `log` function in that module.)

    Args:
      message: A string message to convey to the game engine user.
    """
    plab_logging.log(self, message)

  def change_default_discount(self, discount):
    """Change the discount reported by the `Engine` for non-terminal steps.

    During a game iteration, the `Backdrop` and each `Sprite` or `Drape` have an
    opportunity to call this method (but don't have to). The last one to call
    will determine the new reinforcement learning discount factor that will be
    supplied to the player at every non-terminal step (until this method is
    called again).

    Even for the same game, discounts often need to be different for different
    agent architectures, so conventional approaches to setting a fixed
    non-terminal discount factor include building a discount multiplier into
    your agent or using some kind of wrapper that intercepts and changes
    discounts before the agent sees them. This method here is mainly reserved
    for rare settings where those approaches would not be suitable. Most games
    will not need to use it.

    Args:
      discount: New value of discount in the range [0,1].

    Raises:
      ValueError: if `discount` is not in the [0,1] range.
    """
    if not 0.0 <= discount <= 1.0:
      raise ValueError('Default discount must be in range [0,1].')
    self._engine_directives.discount = discount

  @property
  def frame(self):
    """Counts game iterations, with the first iteration starting at 0."""
    return self._frame

  @property
  def update_group(self):
    """The current update group being consulted by the `Engine`."""
    return self._update_group

  @property
  def default_discount(self):
    """The current non-terminal discount factor used by the `Engine`."""
    return self._engine_directives.discount

  ### Public properties for global story state. ###

  @property
  def prior_chapter(self):
    """Key/index for the prior game in a `Story`, or None for no prior game."""
    return self._prior_chapter

  @property
  def this_chapter(self):
    """Key/index for the current game in a `Story`."""
    return self._this_chapter

  @property
  def next_chapter(self):
    """Key/index for the next game in a `Story`, or None for no next game."""
    return self._next_chapter

  @next_chapter.setter
  def next_chapter(self, next_chapter):
    """Indicate which game should appear next in the current `Story`.

    If the current game is running as part of a `Story`, and if that `Story` was
    initialised with a dict as the `chapters` constructor argument, this method
    allows game entities to indicate which entry in the `chapters` dict holds
    the next game that the `Story` should run after the current game terminates.
    Or, if called with a `None` argument, this method directs the `Story` to
    report termination to the player after the current game terminates. Either
    way, the last call to this method before termination is the one that
    determines what actually happens.

    This method only does something meaningful if a `Story` is actually underway
    and if the `Story`'s `chapters` constructor argument was a dict; otherwise
    it has no effect whatsoever.

    Args:
      next_chapter: A key into the dict passed as the `chapters` argument to the
          `Story` constructor, or None. No checking is done against `chapters`
          to ensure that this argument is a valid key.
    """
    self._next_chapter = next_chapter

  ### Setters and other helpers for Engine ###

  @frame.setter
  def frame(self, val):
    """Update game iterations. Only `Engine` and tests may use this setter."""
    assert val == self._frame + 1  # Frames increase one-by-one.
    self._frame = val

  @update_group.setter
  def update_group(self, group):
    """Set the current update group. Only `Engine` and tests may do this."""
    self._update_group = group

  def _clear_engine_directives(self):
    """Reset this `Plot`'s set of directives to the `Engine`.

    The reset directives essentially tell the `Engine` to make no changes to
    its internal state. The `Engine` will typically call this method at the
    end of every game iteration, once all of the existing directives have been
    consumed.

    Only `Engine` and `Plot` methods may call this method.
    """
    self._engine_directives = self._EngineDirectives()

  def _get_engine_directives(self):
    """Accessor for this `Plot`'s set of directives to the `Engine`.

    Only `Engine` and `Plot` methods may call this method.

    Returns:
      This `Plot`'s set of directions to the `Engine`.
    """
    return self._engine_directives

  ### Setters and other helpers for Story ###

  @prior_chapter.setter
  def prior_chapter(self, val):
    """Update last chapter. Only `Story` and tests may use this setter."""
    self._prior_chapter = val

  @this_chapter.setter
  def this_chapter(self, val):
    """Update current chapter. Only `Story` and tests may use this setter."""
    self._this_chapter = val

  ### Private helpers for error detection ###

  def _value_error_if_character_is_bad(self, character):
    try:
      ord(character)
    except TypeError:
      raise ValueError(
          '{} was used as an argument in a call to change_z_order, but only '
          'single ASCII characters are valid arguments'.format(repr(character)))
