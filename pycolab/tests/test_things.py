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

"""pycolab "things" for testing, and a protocol to talk to them.

This module contains several lightweight `Sprite`s and `Drape`s, and a protocol
that makes it easy to inject code into their `update` methods. The sites of
these injections are ideal for specifying tests, particularly if your test case
inherits from the `PycolabTestCase` class also defined in this module. A typical
pattern looks like this:

    from pycolab.tests import test_things as tt

    class MyTest(tt.PycolabTestCase):

      def testSomething(self):
         ...
         # set up the game
         ...

         # Tell the Sprite or Drape (a class from this module) handling
         # character 'p' to expect the game board to look a certain way.
         tt.pre_update(engine, 'p', self.expectBoard(['...#########...',
                                                      '...#       #...',
                                                      '...#    p  #...',
                                                      '...# X     #...',
                                                      '...#########...']))

         # Execute the next game iteration; the comparison we just expressed
         # above will be evaluated here.
         observation, reward, discount = engine.play('e')

Or use the versatile `assertMachinima` test function to test an entire sequence
of actions, expected observations, and more.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

import numpy as np

from pycolab import ascii_art
from pycolab import cropping
from pycolab import things as plab_things
from pycolab.prefab_parts import drapes
from pycolab.prefab_parts import sprites

import six


def pre_update(engine, character, thing_to_do):
  """Make the test entity for `character` do something before updating itself.

  Assuming the pycolab game `engine` has the character `character` handled by
  one of the `Sprite`s or `Drape`s handled in this module, then on the next game
  iteration, that entity will execute `thing_to_do` before performing any of its
  own update tasks.

  This code injection works only for the next game iteration, after which it
  is cleared.

  Args:
    engine: a pycolab game.
    character: a character handled in the game by an instance of one of the
        `Sprite`s or `Drape`s defined in this module.
    thing_to_do: a callable that takes all of the arguments to the `Sprite`
        or `Drape` `update` method.
  """
  engine.the_plot.setdefault('test_pre_update', {})[character] = thing_to_do


def post_update(engine, character, thing_to_do):
  """Make the test entity for `character` do something after updating itself.

  Assuming the pycolab game `engine` has the character `character` handled by
  one of the `Sprite`s or `Drape`s handled in this module, then on the next game
  iteration, that entity will execute `thing_to_do` after performing all of its
  own update tasks.

  This code injection works only for the next game iteration, after which it
  is cleared.

  Args:
    engine: a pycolab game.
    character: a character handled in the game by an instance of one of the
        `Sprite`s or `Drape`s defined in this module.
    thing_to_do: a callable that takes all of the arguments to the `Sprite`
        or `Drape` `update` method.
  """
  engine.the_plot.setdefault('test_post_update', {})[character] = thing_to_do


def get_pre_update(entity, the_plot):
  """Retrieve pre-update callable for `entity` for the next game iteration.

  Once retrieved, the pre-update callable is cleared, so the callable will only
  be called for the current game iteration.

  This function is intended mainly as a helper for the `Sprite`s and `Drape`s
  defined in this module. Most user code will not need to use it.

  Args:
    entity: the pycolab game entity for which we wish to retrieve any pre-update
        callable.
    the_plot: the `Plot` object for the pycolab game passed to `pre_update` when
        registering a callable for `entity`.

  Returns:
    the callable registered for this entity via `pre_update`, or a null
    callable if none was registered.
  """
  return the_plot.setdefault('test_pre_update', {}).pop(
      entity.character, lambda *args, **kwargs: None)


def get_post_update(entity, the_plot):
  """Retrieve post-update callable for `entity` for the next game iteration.

  Once retrieved, the post-update callable is cleared, so the callable will only
  be called for the current game iteration.

  This function is intended mainly as a helper for the `Sprite`s and `Drape`s
  defined in this module. Most user code will not need to use it.

  Args:
    entity: the pycolab game entity for which we wish to retrieve any
        post-update callable.
    the_plot: the `Plot` object for the pycolab game passed to `post_update`
        when registering a callable for `entity`.

  Returns:
    the callable registered for this entity via `post_update`, or a null
    callable if none was registered.
  """
  return the_plot.setdefault('test_post_update', {}).pop(
      entity.character, lambda *args, **kwargs: None)


class TestSprite(plab_things.Sprite):
  """A `Sprite` subclass that executes injected pre- and post-update callables.

  This `Sprite` does nothing by default except execute the pre- and post-update
  callables registered by `pre_update` and `post_update`. You may subclass this
  `Sprite` and add your own behaviours by overriding the `real_update` method,
  which this `Sprite`'s `update` method calls in between the two injected
  callables.
  """

  def update(self, actions, board, layers, backdrop, things, the_plot):
    """This `update` implementation is "final". Do not override."""
    pre_update_callable = get_pre_update(self, the_plot)
    pre_update_callable(actions, board, layers, backdrop, things, the_plot)

    self.real_update(actions, board, layers, backdrop, things, the_plot)

    post_update_callable = get_post_update(self, the_plot)
    post_update_callable(actions, board, layers, backdrop, things, the_plot)

  def real_update(self, actions, board, layers, backdrop, things, the_plot):
    """Override this method to add `update` code to `TestSprite` subclasses."""
    pass


class TestDrape(plab_things.Drape):
  """A `Drape` subclass that executes injected pre- and post-update callables.

  This `Drape` does nothing by default except execute the pre- and post-update
  callables registered by `pre_update` and `post_update`. You may subclass this
  `Drape` and add your own behaviours by overriding the `real_update` method,
  which this `Drape`'s `update` method calls in between the two injected
  callables.
  """

  def update(self, actions, board, layers, backdrop, things, the_plot):
    """This `update` implementation is "final". Do not override."""
    pre_update_callable = get_pre_update(self, the_plot)
    pre_update_callable(actions, board, layers, backdrop, things, the_plot)

    self.real_update(actions, board, layers, backdrop, things, the_plot)

    post_update_callable = get_post_update(self, the_plot)
    post_update_callable(actions, board, layers, backdrop, things, the_plot)

  def real_update(self, actions, board, layers, backdrop, things, the_plot):
    """Override this method to add `update` code to `TestDrape` subclasses."""
    pass


class TestMazeWalker(sprites.MazeWalker, TestSprite):
  """A `MazeWalker` that supports the injected callables of `TestSprite`.

  Overrides `TestSprite`s `real_update` method to implement basic maze-walking
  behaviour; you may override `real_update` if you'd prefer your own mapping
  from actions to invocations of `MazeWalker` motion action helper methods.
  By default, actions may either be strings denoting compass-directions of
  single-cell motion ('n', 'ne', 'e', 'se', 's', 'sw', 'w', and 'nw') or
  dicts mapping characters to such strings, in which case this `Sprite` will
  obey the string stored under `self.character`.

  If no valid action can be identified for this `Sprite` by either means, the
  `Sprite` will invoke the `_stay` motion action helper method.

  The result of any motion action helper method invoked by a `TestMazeWalker`
  is stored in the `Plot` object under the key 'walk_result_X', where X is the
  sprite character controlled by this `TestMazeWalker`.
  """

  def real_update(self, actions, board, layers, backdrop, things, the_plot):

    if isinstance(actions, str):
      direction = actions
    elif isinstance(actions, dict):
      direction = actions.get(self.character, None)
    else:
      direction = None

    if direction == 'nw':
      result = self._northwest(board, the_plot)
    elif direction == 'n':
      result = self._north(board, the_plot)
    elif direction == 'ne':
      result = self._northeast(board, the_plot)
    elif direction == 'e':
      result = self._east(board, the_plot)
    elif direction == 'se':
      result = self._southeast(board, the_plot)
    elif direction == 's':
      result = self._south(board, the_plot)
    elif direction == 'sw':
      result = self._southwest(board, the_plot)
    elif direction == 'w':
      result = self._west(board, the_plot)
    else:
      result = self._stay(board, the_plot)

    the_plot['walk_result_{}'.format(self.character)] = result


class TestScrolly(drapes.Scrolly, TestDrape):
  """A `Scrolly` that supports the injected callables of `TestSprite`.

  Overrides `TestDrape`s `real_update` method to implement basic maze-walking
  behaviour; you may override `real_update` if you'd prefer your own mapping
  from actions to invocations of `Scrolly` motion action helper methods.
  By default, actions may either be strings denoting compass-directions of
  single-cell motion ('n', 'ne', 'e', 'se', 's', 'sw', 'w', and 'nw') or
  dicts mapping characters to such strings, in which case this `Sprite` will
  obey the string stored under `self.character` (or do nothing if there is no
  such entry).

  If no valid action can be identified for this `Drape` by either means, the
  `Drape` will invoke the `_stay` motion action helper method.
  """

  def real_update(self, actions, board, layers, backdrop, things, the_plot):

    if isinstance(actions, str):
      direction = actions
    elif isinstance(actions, dict):
      direction = actions.get(self.character, None)
    else:
      direction = None

    if direction == 'nw':
      self._northwest(the_plot)
    elif direction == 'n':
      self._north(the_plot)
    elif direction == 'ne':
      self._northeast(the_plot)
    elif direction == 'e':
      self._east(the_plot)
    elif direction == 'se':
      self._southeast(the_plot)
    elif direction == 's':
      self._south(the_plot)
    elif direction == 'sw':
      self._southwest(the_plot)
    elif direction == 'w':
      self._west(the_plot)
    else:
      self._stay(the_plot)


class PycolabTestCase(unittest.TestCase):
  """`TestCase` subclass with convenience methods for pycolab testing."""

  def assertBoard(self, actual_board, art, err_msg=''):
    """Assert that a pycolab game board matches expected ASCII art.

    Args:
      actual_board: a pycolab game board, in its 2-D `uint8` nparray
          manifestation. This is the `board` member of a `rendering.Observation`
          namedtuple.
      art: an ASCII-art diagram, as a list of same-length ASCII strings,
          portraying the expected game board.
      err_msg: optional error message to include in `AssertionError`s raised
          by this method.

    Raises:
      AssertionError: `art` does not match `actual_board`.
    """
    np.testing.assert_array_equal(actual_board,
                                  ascii_art.ascii_art_to_uint8_nparray(art),
                                  err_msg)

  def expectBoard(self, art, err_msg=''):  # pylint: disable=invalid-name
    """Produce a callable that invokes `assertBoard`.

    This method is a convenient means of injecting a call to `assertBoard`
    via the `pre_update` and `post_update` methods defined above. The second
    argument to the callable returned by this method will be used as the
    `actual_board` argument to `assertBoard`, with the remaining arguments
    supplied by this function's parameters.

    Args:
      art: see `assertBoard`.
      err_msg: see `assertBoard`.

    Returns:
      a callable suitable for use as the `thing_to_do` argument to `pre_update`
      and `post_update`.
    """
    def expecter(actions, board, layers, backdrop, things, the_plot):
      del actions, layers, backdrop, things, the_plot  # Unused.
      self.assertBoard(board, art, err_msg)
    return expecter

  def assertMachinima(self, engine, frames,
                      pre_updates=None, post_updates=None, result_checker=None,
                      croppers=None):
    """Assert that gameplay produces a "movie" of expected observations.

    [Machinima](https://en.wikipedia.org/wiki/Machinima) is the creation of
    movies with game engines. This test method allows you to demonstrate that
    a sequence of canned actions would produce a sequence of observations. Other
    tests and behaviours may be imposed on the `Sprite`s and `Drape`s in the
    sequence as well.

    Args:
      engine: a pycolab game engine whose `its_showtime` method has already been
          called. Note: if you are using croppers, you may want to supply the
          observation result from `its_showtime` to the croppers so that they
          will have a chance to see the first observation in the same way they
          do in the `CursesUi`.
      frames: a sequence of n-tuples, where `n >= 2`. The first element in each
          tuple is the action that should be submitted to `engine` via the
          `play` method; the second is an ASCII-art diagram (see `assertBoard`)
          portraying the observation we expect the `play` method to return, or a
          list of such diagrams if the `croppers` argument is not None (see
          below). Any further elements of the tuple are stored in the engine's
          `Plot` object under the key `'machinima_args'`. These are commonly
          used to pass expected values to `assertEqual` tests to callables
          provided via `pre_updates` and `post_updates`.
      pre_updates: optional dict mapping single-character strings (which should
          correspond to `Sprite`s and `Drape`s that inherit from test classes in
          this module) to a callable that is injected into the entity via
          `pre_update` at each game iteration. These callables are usually used
          to specify additional testing asserts.
      post_updates: optional dict mapping single-character strings (which should
          correspond to `Sprite`s and `Drape`s that inherit from test classes in
          this module) to a callable that is injected into the entity via
          `post_update` at each game iteration. These callables are usually used
          to specify additional testing asserts.
      result_checker: optional callable that, at every game iteration, receives
          arguments `observation`, `reward`, `discount`, and `args`. The first
          three are the return values of the engine's `play` method; `args` is
          the `machinima_args` elements for that game iteration (see `frames`).
          The `observation` is the original game engine observation;
          `result_checker` does not receive the output of any of the `croppers`.
          (If you need to check cropped observations, consider passing your
          croppers to `result_checker` via `machinima_args` and cropping the
          observation yourself.)
      croppers: None, or a list of `cropping.ObservationCropper` instances
          and/or None values. If None, then `frames[i][1]` should be an
          ASCII-art diagram to compare against frames as emitted by the engine;
          if a list, then `frames[i][1]` should be a list of diagrams to compare
          against the outputs of each of the croppers. A None value in
          `croppers` is a "null" or "pass-through" cropper: the corresponding
          entry in `frames[i][1]` should expect the original game engine
          observation. NB: See important usage note in the documentation for
          the `engine` arg.

    Raises:
      AssertionError: an observation produced by the game engine does not match
          one of the observation art diagrams in `frames`.
      ValueError: if croppers is non-None and the number of
          `ObservationCropper`s it contains differs from the number of ASCII-art
          diagrams in one of the elements of `frames`.
    """
    if pre_updates is None: pre_updates = {}
    if post_updates is None: post_updates = {}

    # If we have croppers, replace None values with pass-through croppers, then
    # tell all croppers which game we're playing.
    if croppers is not None:
      try:
        croppers = tuple(
            cropping.ObservationCropper() if c is None else c for c in croppers)
      except TypeError:
        raise TypeError('The croppers argument to assertMachinima must be a '
                        'sequence or None, not a "bare" object.')
      for cropper in croppers:
        cropper.set_engine(engine)

    # Step through the game and verify expected results at each frame.
    for i, frame in enumerate(frames):
      action = frame[0]
      art = frame[1]
      args = frame[2:]

      engine.the_plot['machinima_args'] = args

      for character, thing_to_do in six.iteritems(pre_updates):
        pre_update(engine, character, thing_to_do)
      for character, thing_to_do in six.iteritems(post_updates):
        post_update(engine, character, thing_to_do)

      observation, reward, discount = engine.play(action)

      if croppers is None:
        self.assertBoard(observation.board, art,
                         err_msg='Frame {} observation mismatch'.format(i))
      else:
        # It will be popular to construct iterables of ASCII art using zip (as
        # shown in cropping_test.py); we graciously convert art to a tuple,
        # since the result of Python 3's zip does not support len().
        art = tuple(art)
        if len(art) != len(croppers): raise ValueError(
            'Frame {} in the call to assertMachinima has {} ASCII-art diagrams '
            'for {} croppers. These counts should be the same.'.format(
                i, len(art), len(croppers)))
        for j, (cropped_art, cropper) in enumerate(zip(art, croppers)):
          self.assertBoard(
              cropper.crop(observation).board, cropped_art,
              err_msg='Frame {}, crop {} observation mismatch'.format(i, j))

      if result_checker is not None:
        result_checker(observation, reward, discount, args)
