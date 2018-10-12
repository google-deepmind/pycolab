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

"""Stories: games made of programmable sequences of pycolab games.

All details are in the docstring for `Story`.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

import numpy as np

from pycolab import cropping
from pycolab import engine
from pycolab import things

import six


class Story(object):
  """Base class for programmable sequences of pycolab games.

  A story is a game made from other pycolab games. In the same way that many
  video games present a sequence of distinct "levels", "stages", "rooms",
  "chapters", "zones", etc. to the player, a story can present a programmable
  sequence of mutually-compatible (see below) pycolab games as a continuous
  gameplay experience. This is one way to make richer, more complicated games.

  As a Python object, a `Story` has some of the methods and attributes of a
  pycolab `Engine`, but not all, and some of the assumptions that you can make
  about those methods and attributes for an `Engine` may not necessarily apply.
  It's intended that a `Story` should do most of the things you expect an
  `Engine` to do, and should plug into most of the places you expect a `Engine`
  to go, but for applications that depend very specifically on what the `Engine`
  methods and properties do (especially `z_order`, `things`, and `backdrop`),
  you ought to check docstrings to be sure.

  From the perspective of individual pycolab `Engine`s participating in the
  story, there are few hints of being part of a greater whole. The main one is
  that values left in the Plot by previous `Engine`s in the story are copied
  into the current `Engine`'s Plot. In fact, this is the only official way to
  pass information between successive pycolab games. `Story` transfers nothing
  else; each `Engine` has its own set of game entities that get discarded when
  the `Engine` terminates, and if sprite 'P' in game A is conceptually "the
  same" as sprite 'P' in game B, then they had better pass whatever notes to
  each other they need in the Plot in order to maintain this illusion.

  To make a story, first assemble a collection of argumentless builder functions
  for all of the pycolab games you want to include in the overall gameplay. Each
  builder must return an `Engine` object ready for its `its_showtime` method to
  be called. You will supply the builders to the `Story` constructor, as a dict
  or a list/tuple:

  - If a dict, then whenever a game terminates, the story queries that game's
    Plot object for the key indicating the next game to start (see the
    `Plot.next_chapter` setter). If this key is None, the story terminates.
    This mechanism allows for online generation of dynamic storylines.
  - If a list/tuple, then the story will present one game from each constructor
    in sequence, only terminating (from the player's point of view) after the
    last game terminates. (Games may still override this automatic ordering via
    `Plot.next_chapter`, and even set up story termination by setting the next
    chapter to None, but otherwise the sequential progress through the games
    happens on its own.)

  A story can only be assembled from compatible games. From `Story`'s
  perspective, games are compatible when:
    - any two games that use the same character use them in the same way (so,
      if 'P' is used by games A and B, then if it's a Sprite in game A, it must
      be a Sprite in game B as well).
    - their observations all have the same numbers of rows and columns. (You
      can use Croppers to help out with this---see the `__init__` docstring.)
  Your use case likely has even stricter compatibility requirements than these:
  for example, the available actions probably have to be the same across all
  games. That's up to you to look after.

  A few good things to know:

  1. In order to gather game information and assess compatibility, each game
     builder will be called at least once in `__init__`, and the `its_showtime`
     method will be called for each game that results. (The games will then
     be discarded.) *In this process, no information will be copied between
     Plots, so an `Engine` cannot always rely on finding information from other
     `Engine`s in the Plot, even if this is how they normally communicate.*
  2. The final observation and discount of all but the very last game are
     discarded. The final reward of all but the very last game is added to the
     first reward of the game that follows it. See documentation for the `play`
     method for further details.
  """

  def __init__(self, chapters, first_chapter=None, croppers=None):
    """Initialise a Story.

    Args:
      chapters: A dict or a list/tuple of argumentless builder functions that
          return `Engine` objects. See class docstring.
      first_chapter: A key/index identifying the first game in `chapters` to
          play in the story. If `chapters` is a list/tuple, this can be left
          as None for the default first game index (0).
      croppers: Optional `cropping.ObservationCropper` instance(s) for deriving
          identically-shaped observations from all of the games. This argument
          may either be:
          * None: no cropping occurs.
          * A single `cropping.ObservationCropper`: the same cropper is applied
            to every game in `chapters`.
          * An identical structure to `chapters`: the corresponding cropper is
            used for each game. A None value in this structure indicates that
            the corresponding game should not be cropped.
          Note that unlike the human_ui, it's not possible to specify more than
          one cropper per entry in `chapters`.

    Raises:
      ValueError: Arguments to the constructor are malformed, or the games
          supplied to the constructor are incompatible in some way.
    """
    # If chapters is a list/tuple, the user will expect the game to progress
    # through the games automatically. The user will also expect the game to
    # start on the first list element by default.
    self._auto_advance = not isinstance(chapters, collections.Mapping)
    if self._auto_advance and first_chapter is None: first_chapter = 0

    # Argument checking and normalisation. If chapters and croppers were
    # lists/tuples, this step will convert them to dicts indexed by integers.
    self._chapters, self._croppers = _check_and_normalise_story_init_args(
        chapters, first_chapter, croppers)
    del chapters, croppers  # Unnormalised; no longer needed.

    # Game compatibility checking, understanding how characters in the games are
    # used (i.e. as Sprites, Drapes, or in Backdrops), and identifying the shape
    # of the game board.
    (self._chars_sprites, self._chars_drapes, self._chars_backdrops,
     (self._rows, self._cols)) = (
         _check_game_compatibility_and_collect_game_facts(
             self._chapters, self._croppers))

    # Obtain the initial game and its cropper.
    self._current_game = self._chapters[first_chapter]()
    self._current_cropper = self._croppers[first_chapter]
    self._current_cropper.set_engine(self._current_game)

    # Set Story history attributes in the initial game's Plot.
    plot = self._current_game.the_plot  # Abbreviation.
    plot.prior_chapter = None
    plot.this_chapter = first_chapter
    if self._auto_advance:
      next_ch = plot.this_chapter + 1
      plot.next_chapter = next_ch if next_ch in self._chapters else None

    # True iff its_showtime() has been called and the game is underway.
    self._showtime = False
    # True iff the game has terminated. (It's still "showtime", though.)
    self._game_over = False

    # Cached dummy Sprites and Drapes for the .things attribute.
    self._dummy_sprites_for_shape = dict()
    self._dummy_drapes_for_shape = dict()

  def its_showtime(self):
    """Start the `Story` and compute its first observation.

    Operates analogously to `Engine.its_showtime`. In most circumstances, this
    method will simply call `its_showtime` on the first game in the story (as
    designated by the `chapters` or `first_chapter` arguments to the
    constructor) and return its results. If the game terminates immediately on
    the `its_showtime` call, though, the method creates and attempts to start
    the next game---and again if that game terminates on `its_showtime`, and
    so on.

    Throughout all of these attempts, the reward returned by the games'
    `its_showtime` methods is summed.

    If this method runs out of games to start, it gives up, returning the last
    game's observation, the sum of all the rewards returned by the
    `its_showtime` methods, and the last game's discount. **Note that this means
    that all preceding games' observations and discounts are discarded.**

    Returns:
      A three-tuple with the following members (see above and the `Engine`
      documentation for more details):
      * The observation: a `rendering.Observation` object.
      * An initial reward.
      * A reinforcement learning discount factor value.

    Raises:
      RuntimeError: if this method is called more than once.
    """
    if self._showtime:
      raise RuntimeError('its_showtime should not be called more than once.')

    # It's showtime!
    self._showtime = True

    # Start off the very first game. If it terminates immediately, start the
    # next. And so on, until a game doesn't terminate or we run out of games.
    observation, reward, discount = self._current_game.its_showtime()
    observation = self._current_cropper.crop(observation)
    if self._current_game.game_over:
      return self._start_next_game(observation, reward, discount)
    else:
      return observation, reward, discount

  def play(self, actions):
    """Perform another game iteration, applying player actions.

    Operates analogously to `Engine.play`. In most circumstances, this method
    will simply call `play` on the current game and return its results. If the
    game terminates immediately on the `play` call, though, the method creates
    and attempts to start the next game---and again if that game terminates on
    `its_showtime`, and so on.

    Throughout all of these attempts, the reward returned by the games'
    `its_showtime` methods is added to the reward returned by the game that
    terminated in the first place.

    Eventually, if a game finally starts successfully, this summed reward is
    returned along with the first observation and discount of the new game. If
    no game starts successfully, though, then the summed reward is returned
    along with the observation and discount of the last game that this method
    attempted to start.

    **Note: The behaviour described above means that except for the very last
    game in the story, the final observations and discounts of games are
    discarded.** If it's important for an agent to see a game's final
    observation before the next game in a story begins, it will be necessary
    for this last game to introduce an extra "no-op" step just before
    termination. One pattern for doing this is:

    * In `play` for all game entities: check for a "dummy_step" entry in the
      Plot and do nothing but call for termination if its value is the current
      frame number:
      `if the_plot.get('dummy_step') >= the_plot.frame:`
      `  return the_plot.terminate_episode()`.
      Multiple entities will call for termination, but it doesn't matter.
    * If an entity wishes to terminate the game, add the "dummy_step" entry
      to the Plot: `the_plot['dummy_step'] = the_plot.frame + 1`. The value is
      the frame number when true termination should occur---the example code
      specifies the next frame.

    Args:
      actions: Actions supplied by the external agent(s) in response to the
          last board. See `Engine.play` documentation for details.

    Returns:
      A three-tuple with the following members (see `Engine` documentation for
      more details:
      * The observation: a `rendering.Observation` object.
      * An initial reward.
      * A reinforcement learning discount factor value.

    Raises:
      RuntimeError: if this method has been called before the `Story` has been
          finalised via `its_showtime()`, or if this method has been called
          after the episode has terminated.
    """
    if not self._showtime:
      raise RuntimeError('play() cannot be called until the Story is placed in '
                         '"play mode" via the its_showtime() method.')
    if self._game_over:
      raise RuntimeError('play() was called after the last game managed by the '
                         'Story has terminated.')

    # Play the action. If the current game terminates, start the next game. And
    # so on, until a game doesn't terminate or we run out of games.
    observation, reward, discount = self._current_game.play(actions)
    observation = self._current_cropper.crop(observation)
    if self._current_game.game_over:
      return self._start_next_game(observation, reward, discount)
    else:
      return observation, reward, discount

  @property
  def the_plot(self):
    """A work-alike for `Engine.the_plot`.

    Returns:
      The Plot object from the current game. It is probably a bad idea to save
      a local reference to the returned Plot, since the next game in the story
      will use a different object.
    """
    return self._current_game.the_plot

  @property
  def rows(self):
    return self._rows

  @property
  def cols(self):
    return self._cols

  @property
  def game_over(self):
    return self._game_over

  @property
  def z_order(self):
    """A work-alike for `Engine.z_order`.

    Returns:
      A list of characters that would be a plausible z-order if this `Story`
      were actually a pycolab `Engine`. All Sprite and Drape characters that are
      not used by the current game are prepended to that game's z-order. It is
      probably a bad idea to save a local reference to the returned list.
    """
    current_game_z_order = self._current_game.z_order
    leftover_chars = sorted(
        self._chars_sprites.difference(current_game_z_order).union(
            self._chars_drapes.difference(current_game_z_order)))
    return leftover_chars + current_game_z_order

  ### Abstraction breakers ###

  @property
  def backdrop(self):
    """A work-alike for `Engine.backdrop`.

    Returns:
      A `things.Backdrop` object that would be a plausible Backdrop if this
      `Story` were actually a pycolab `Engine`. The `curtain` member is the
      actual curtain from the current game's Backdrop, but the `palette`
      member considers all of the characters used in the Backdrops of all of
      the games to be legal. The `update` method raises a RuntimeError.

      Note: this attribute returns a new `Backdrop` at each call. It's probably
      safe to save a local reference to the palette, but likely a bad idea to
      save a reference to the curtain or to the returned `Backdrop` in general.
    """
    return things.Backdrop(curtain=self._current_game.backdrop.curtain,
                           palette=engine.Palette(self._chars_backdrops))

  @property
  def things(self):
    """A work-alike for `Engine.things`.

    Returns:
      A dict mapping ASCII characters to `Sprite`s and `Drape`s---a collection
      of such game entities that would be (barely) plausible if this `Story`
      were actually a pycolab `Engine`. All the non-Backdrop entities from the
      current game are present, but for characters only associated with
      `Sprite`s and `Drape`s by the other games supplied to the `Story`
      constructor, some dummy objects are used instead. If you'd like to know
      whether a particular `Sprite` or `Drape` in the returned dict is a dummy,
      use the `is_fictional` method in this module.
    """
    synthesised_things = self._current_game.things

    for c in self._chars_sprites:
      if c not in synthesised_things:
        shape = (self._current_game.rows, self._current_game.cols)
        if shape not in self._dummy_sprites_for_shape:
          self._dummy_sprites_for_shape[shape] = _DummySprite(
              corner=things.Sprite.Position(*shape), character=c)
        synthesised_things[c] = self._dummy_sprites_for_shape[shape]

    for c in self._chars_drapes:
      if c not in synthesised_things:
        shape = (self._current_game.rows, self._current_game.cols)
        if shape not in self._dummy_drapes_for_shape:
          self._dummy_drapes_for_shape[shape] = _DummyDrape(
              curtain=np.zeros(shape, dtype=bool), character=c)
        synthesised_things[c] = self._dummy_drapes_for_shape[shape]

    return synthesised_things

  @property
  def current_game(self):
    """The pycolab `Engine` corresponding to the current game.

    Returns:
      The pycolab `Engine` that the `Story` is running right now. It's
      probably a bad idea to save a reference to this value, or really to use
      this value for much of anything outside of testing.
    """
    return self._current_game

  ### Private helpers ###

  def _start_next_game(self, observation, reward, discount):
    """Try to start a new game to replace a game that just terminated.

    Args:
      observation: Last observation of the game that just terminated.
      reward: Last reward of the game that just terminated.
      discount: Last discount of the game that just terminated.

    Returns:
      A three-tuple with the following members:
      * Either the first observation of a game that has successfully started
        as a replacement for the terminated game; or, if no games would start
        without terminating immediately, the final observation of the last game
        to terminate. (This value could be the `observation` argument if there
        were no games left to start.)
      * The sum of (a) the `reward` argument, (b) the rewards returned by all
        games that terminated immediately after this method tried to start them,
        and (c) the first reward of the game that this method started
        successfully (if this method did manage to start a game successfully).
      * Either the first discount of a game that has successfully started as a
        replacement for the terminated game; or, if no games would start without
        terminating immediately, the final discount of the last game to
        terminate. (This value could be the `discount` argument if there were no
        games left to start.)

    Raises:
      KeyError: For `Story`s constructed with a `dict` for the `chapters`
          argument: the key into `chapters` that a terminating game supplied
          to its plot (via the `next_chapter` setter) is not a valid key.
    """
    while True:
      assert self._current_game.game_over

      # Save the old game's Plot object.
      old_plot = self._current_game.the_plot

      # If there is no next game designated, the termination is final; pass
      # it on to the caller.
      if old_plot.next_chapter is None:
        self._game_over = True
        return observation, reward, discount

      # Otherwise, identify and build the next game.
      try:
        new_game = self._chapters[old_plot.next_chapter]()
        new_cropper = self._croppers[old_plot.next_chapter]
      except KeyError:
        # This error message seems like it could be misleading in the
        # auto-advance case, but the user should never see it unless one of the
        # games really did override the auto-advance indexing.
        raise KeyError(
            'The game that just finished in the Story currently underway '
            '(identified by the key/index "{}") said that the next game in the '
            'story should be {}, but no game was supplied to the Story '
            'constructor under that key or index.'.format(
                old_plot.this_chapter, repr(old_plot.next_chapter)))

      # Copy values from the old plot to the new plot.
      new_plot = new_game.the_plot  # Abbreviation.
      new_plot.update(old_plot)

      # Set Story history attributes in the new plot.
      new_plot.prior_chapter = old_plot.this_chapter
      new_plot.this_chapter = old_plot.next_chapter
      if self._auto_advance:
        next_ch = new_plot.this_chapter + 1
        new_plot.next_chapter = next_ch if next_ch in self._chapters else None

      # The new game is now the current game.
      self._current_game = new_game
      self._current_cropper = new_cropper
      self._current_cropper.set_engine(self._current_game)

      # Start the new game. This game's first observation and discount replace
      # the observation and discount from the old game, but reward accumulates.
      observation, more_reward, discount = self._current_game.its_showtime()
      observation = self._current_cropper.crop(observation)
      if more_reward is not None:
        reward = more_reward if reward is None else (reward + more_reward)

      # If this game hasn't terminated, our search for the next game is
      # complete. Break out of the loop by returning the game's first
      # observation and discount, along with the summed reward.
      if not self._current_game.game_over: return observation, reward, discount


def is_fictional(thing):
  """Test whether a `Sprite` or `Drape` is a dummy.

  Args:
    thing: A `Sprite` or `Drape`.

  Returns:
    True iff `thing` is one of the stand-in dummy `Sprite`s or `Drape`s returned
    by `Story.things`.
  """
  return isinstance(thing, (_DummySprite, _DummyDrape))


### Module-level private helpers ###


def _check_and_normalise_story_init_args(chapters, first_chapter, croppers):
  """Helper: check and normalise arguments for `Story.__init__`.

  Args:
    chapters: as in `Story.__init__`.
    first_chapter: as in `Story.__init__`.
    croppers: as in `Story.__init__`.

  Returns:
    a 2-tuple with the following members:
        [0]: A shallow copy of the contents of `chapters` into a dict. If
             `chapters` was a list, the resulting dict will have keys
             0..`len(chapters)-1`.
        [1]: A normalised version of `croppers`: always the same structure as
             the first tuple element, with each value a
             `cropping.ObservationCropper`; if no cropping was desired for a
             game, "no-op" croppers are supplied.

  Raises:
    ValueError: any of several argument check failures. See the error messages
        themselves for details.
  """
  # All this checking aims to be instructive to users, but is a bit verbose for
  # inclusion in the class constructor itself.
  if not chapters: raise ValueError(
      'The chapters argument to the Story constructor must not be empty.')

  # First, if the `chapters` argument is a list or tuple, convert it into a
  # dict, and convert a list/tuple `croppers` argument into a dict as well.
  if isinstance(chapters, collections.Sequence):
    chapters = dict(enumerate(chapters))
    if isinstance(croppers, collections.Sequence):
      croppers = dict(enumerate(croppers))

  if not isinstance(chapters, collections.Mapping): raise ValueError(
      'The chapters argument to the Story constructor must be either a dict '
      'or a list.')

  if None in chapters: raise ValueError(
      'None may not be a key in a Story chapters dict.')
  if first_chapter not in chapters: raise ValueError(
      'The key "{}", specified as a Story\'s first_chapter, does not appear in '
      'the chapters supplied to the Story constructor.'.format(first_chapter))

  # Normalise croppers argument into a dict of croppers. Note that
  # cropping.ObservationCropper is a "null cropper" that makes no changes.
  if croppers is None: croppers = cropping.ObservationCropper()
  if isinstance(croppers, cropping.ObservationCropper):
    croppers = {k: croppers for k in chapters.keys()}
  if (not isinstance(croppers, collections.Mapping) or
      set(chapters.keys()) != set(croppers.keys())): raise ValueError(
          'Since the croppers argument to the Story constructor was not None '
          'or a single ObservationCropper, it must be a collection with the '
          'same keys or indices as the chapters argument.')
  croppers = {k: cropping.ObservationCropper() if c is None else c
              for k, c in croppers.items()}

  # Normalise chapters to be a dict; croppers already is.
  chapters = dict(chapters)

  return chapters, croppers


def _check_game_compatibility_and_collect_game_facts(chapters, croppers):
  """Helper: compatibility checks, info gathering for `Story.__init__`.

  See the `Story` docstring for more information on compatibility.

  Args:
    chapters: `chapters` argument to `Story.__init__` after normalisation by
        `_check_and_normalise_story_init_args`.
    croppers: `croppers` argument to `Story.__init__` after normalisation by
        `_check_and_normalise_story_init_args`.

  Returns:
    a 4-tuple with the following members:
        [0]: The set of all characters used by at least one game for a Sprite.
        [1]: The set of all characters used by at least one game for a Drape.
        [2]: The set of all characters used by at least one game's Backdrop.
        [3]: The rows, cols shape of game observations.

  Raises:
    ValueError: The games supplied to the `Story` constructor are incompatible.
  """
  # Convert chapters and croppers to identically-sorted lists.
  chapters = [c for _, c in sorted(chapters.items())]
  croppers = [c for _, c in sorted(croppers.items())]

  # Across all games:
  observation_shapes = set()  # What shapes are observations?
  chars_sprites = set()       # Which characters are used for Sprites?
  chars_drapes = set()        # Which characters are used for Drapes?
  chars_backdrops = set()     # Which characters are used for Backdrops?

  # Instantiate each game and call its_showtime to collect data about shape and
  # character usage.
  for chapter, cropper in zip(chapters, croppers):
    game = chapter()
    cropper.set_engine(game)
    observation, _, _ = game.its_showtime()

    # Save the shape of the current observation.
    observation_shapes.add(tuple(cropper.crop(observation).board.shape))
    # Save the ways that the engine uses characters.
    chars_backdrops.update(game.backdrop.palette)
    for char, thing in six.iteritems(game.things):
      if isinstance(thing, things.Sprite):
        chars_sprites.add(char)
      else:
        chars_drapes.add(char)

  # The checks themselves.
  if len(observation_shapes) != 1: raise ValueError(
      'All pycolab games supplied to the Story constructor should have '
      'observations that are the same shape, either naturally or with the help '
      'of observation croppers. The games provided to the constructor have '
      'diverse shapes: {}.'.format(list(observation_shapes)))
  intersect_sd = chars_sprites.intersection(chars_drapes)
  intersect_sb = chars_sprites.intersection(chars_backdrops)
  intersect_db = chars_drapes.intersection(chars_backdrops)
  if intersect_sd or intersect_sb or intersect_db: raise ValueError(
      'No two pycolab games supplied to the Story constructor should use the '
      'same character in two different ways: if a character is a Sprite in '
      'one game, it shouldn\'t be a Drape in another. Across the games '
      'supplied to this Story, these characters are both a Sprite and a '
      'Drape: [{}]; these are both a Sprite and in a Backdrop: [{}]; and '
      'these are both a Drape and in a Backdrop: [{}].'.format(
          *[''.join(s) for s in (intersect_sd, intersect_sb, intersect_db)]))

  return chars_sprites, chars_drapes, chars_backdrops, observation_shapes.pop()


class _DummySprite(things.Sprite):
  """A Sprite that goes invisible and does nothing.

  This Sprite exists so that the `Story.things` attribute can return a Sprite
  under a Sprite character that isn't being used by the `Story`'s current game.
  It does nothing and its update method should never be called.
  """

  def __init__(self, corner, character):
    super(_DummySprite, self).__init__(
        corner=corner, position=self.Position(0, 0), character=character)
    self._visible = False

  def update(self, *args, **kwargs):
    raise RuntimeError('_DummySprite.update should never be called.')


class _DummyDrape(things.Drape):
  """A Drape that does nothing.

  This Drape exists so that the `Story.things` attribute can return a Drape
  under a Drape character that isn't being used by the `Story`'s current game.
  It does nothing and its update method should never be called.

  There's little practical need for this Drape: the default Drape implementation
  would be fine. It mainly exists to make debugging and inspection easier.
  """

  def update(self, *args, **kwargs):
    raise RuntimeError('_DummyDrape.update should never be called.')
