# coding=utf8

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

"""The pycolab game engine.

Refer to the docstring for `Engine` for details. This module also includes the
`Palette` helper class.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

import numpy as np

from pycolab import plot
from pycolab import rendering
from pycolab import things

import six


class Engine(object):
  """The pycolab game engine.

  Every pycolab game is an instance of `Engine`. These games all have certain
  things in common:

  * They're grid-based! ▦
  * Games proceed in discrete steps: the player calls the `play` method with
      their chosen action, and the `Engine` updates the board in response, which
      then becomes the observation returned to the player.
  * By default, observations are a single 2-D numpy array "board" with dtype
      `uint8`, or, alternatively, a collection of binary masks (see
      `Observation` in `rendering.py`).
  * Values are painted onto the board by instances of `Backdrop`, `Sprite`,
      and `Drape`, which are described in detail in `things.py`. (Now would be
      a fine time to go read more about them. Go ahead--it'll be fun!)
  * Additionally, it is expected that your game logic will be arranged within
      these objects somehow.
  * `Backdrop`, `Sprite`, and `Drape` instances can communicate with each other
      and affect global game state (reward, termination, etc.) through the
      game's `Plot` object. ("Plot" as in "thickens", not as in "Cartesian".)
  * (Now is NOT the best time to read more about the `Plot`; for the time being,
      just remember that it's a global blackboard. :-)

  At each game iteration, the `Engine` instance consults the `Backdrop` and each
  `Sprite` and `Drape` to determine how to update the board. These
  consultations, which happen in a specified, fixed order, are also when the
  game logic within those objects chooses how to react to the things they see on
  the board, the actions from the player(s), and the information stored in the
  game's `Plot`. Once all the updates have been applied, the new board is shown
  to the user, and the `Engine` awaits the next action.

  In the simplest arrangement, the `Engine` collects updates from the `Backdrop`
  and from all `Sprite`s and `Drape`s, then repaints the board all at once.
  This means that all of these objects will base their decision on the state of
  the board as it was when the user chose an action. More complicated
  arrangements are possible. By placing `Sprite`s and `Drape`s in separate
  "update groups", you can force the `Engine` to repaint the board after only
  some of the updates have been collected. For example, if update group 0
  contains

      [sprite_A, drape_B, sprite_C]

  and update group 1 contains

      [drape_D, sprite_E, sprite_F]

  then the `Backdrop`, `sprite_A`, `drape_B`, and `sprite_C` will see the board
  as it was last seen by the user, while `drape_D`, `sprite_E`, and `sprite_F`
  will see the board after the updates from the first four are applied. This
  may simplify your game logic.

  No matter how things are arranged into update groups, the user will only see
  the board after the updates from *all* `Sprite`s, `Drape`s, and the `Backdrop`
  have been applied.

  From here, it's probably best to read the documentation for `Plot` (it's okay
  now!) and then the docstring for the `Engine` constructor.
  """

  def __init__(self, rows, cols, occlusion_in_layers=True):
    """Construct a new pycolab game engine.

    Builds a new pycolab game engine, ready to be populated with a `Backdrop`,
    `Sprite`s, and `Drape`s (see `things.py`). Once set up, an `Engine` will
    manage the rendering and logic of a game for one episode.  (For new
    episodes, make a new `Engine`).

    A newly-constructed `Engine` makes for a really boring game: there is
    nothing to draw on the game board and no game logic. In fact, the `Engine`
    will refuse to work at all without a `Backdrop`.

    Here's what you need to do: after construction, supply the engine with
    a `Backdrop` object to paint the background of the game board (things like
    walls and such), and then `Sprite` and `Drape` objects to move around on top
    of it (see `things.py` for details). These objects can view the game board
    and communicate with each other (usually via a `Plot` object), and the game
    logic is implemented in their interactions.

    Here is an example of a simple game setting up a new `Engine`:

        engine = pycolab.Engine(rows=24, cols=80)
        engine.set_backdrop('#+|-* ', my_game.Mansion, time='1 AM', moon='full')
        engine.add_sprite('C', (22, 77), my_game.Ghost, name='Claudius')
        engine.add_sprite('E', (19, 61), my_game.Ghost, name='Ebenezer')
        engine.add_sprite('I', (11, 48), my_game.Ghost, name='Ichabod')
        engine.add_sprite('!', (23, 18), my_game.Player, hit_points=99)
        engine.add_drape('~', my_game.MistsAndVapours, breeze=1)

        first_obs, first_reward, first_discount = engine.its_showtime()

    The order in which `Sprite` and `Drape` objects are added to the `Engine`
    determines (partially; read on) the order in which they will be consulted
    for game board updates: in this case, after the `Backdrop`, which is always
    consulted first, it's Claudius, Ebenezer, Ichabod, the player, and then a
    `Drape` that paints spooky mists. This ordering cannot change once it is
    set.

    The order of addition is also the initial back-to-front "z-order": the order
    in which the updates are painted onto the board. Although `Backdrop` updates
    are always painted first, the rest of the layers can change their z-order at
    any point in the game (by registering a request with the `Plot` object).
    This may be useful if you ever want Ichabod to float in front of the spooky
    mists. Z-order can also be changed at game set-up time via the `set_z_order`
    method.

    Once the `Backdrop` and all of the `Sprite`s and `Drape`s are ready,
    call `its_showtime()` to start the game. This method "locks" the engine
    (i.e. no new `Sprite`s or `Drape`s can be added) and starts the episode,
    returning the first observation.

    Here is a more elaborate game setting up its `Engine`:

        engine = pycolab.Engine(rows=7, cols=7)
        engine.set_backdrop(sokoban.Warehouse.CHARACTERS, sokoban.Warehouse)

        engine.update_group('2. Player')
        engine.add_sprite('P', (5, 3), sokoban.Player)

        engine.update_group('1. Boxes')
        engine.add_sprite('1', (3, 2), sokoban.Box)
        engine.add_sprite('2', (5, 4), sokoban.Box)
        engine.add_sprite('3', (2, 5), sokoban.Box)

        engine.update_group('3. Judge')
        engine.add_drape('J', sokoban.Judge)

        first_obs, first_reward, first_discount = engine.its_showtime()

    The `Engine`'s order for consulting `Sprite`s and `Drape`s for updates is
    determined first by the sort order of the update group name, then by order
    of addition. Thus, in this Sokoban implementation, the `Engine` will first
    consult box sprites 1, 2, and 3 for board updates, then the player sprite,
    and finally the "Judge".  (The Judge in this game happens to be an invisible
    `Drape` whose `update` method contains the logic that determines whether
    the player has won the game.)

    Nevertheless, the consultation order is different from the initial z-order,
    which starts at the backdrop and proceeds directly in the order in which the
    `Sprite`s and `Drape`s were `add_*`ed. (This structure could allow a player
    to crawl under a box in this Sokoban---or perhaps a box to crush a player!)

    This game has given a name to all of its update groups, which is a good idea
    whenever you have more than one. The default update group is named `''`
    (the empty string).

    And, for one last hyper-technical detail: the `Backdrop` can be thought of
    as belonging to the very first update group, and will always be the first
    `Engine` entity to be consulted for an update in that group. If it is
    desired that all `Sprite`s and `Drape`s be in a separate update group from
    the backdrop, the best way to accomplish this is probably to establish an
    update group that precedes all of your game's real `Sprite`s and `Drape`s,
    and to populate it with an invisible sprite that never does anything.

    Args:
      rows: Height of the game board.
      cols: Width of the game board.
      occlusion_in_layers: If `True` (the default), game entities or `Backdrop`
          characters that occupy the same position on the game board will be
          rendered into the `layers` member of `rendering.Observation`s with
          "occlusion": only the entity that appears latest in the game's Z-order
          will have its `layers` entry at that position set to `True`. If
          `False`, all entities and `Backdrop` characters at that position will
          have `True` in their `layers` entries there.

          This flag does not change the rendering of the "flat" `board` member
          of `Observation`, which always paints game entities on top of each
          other as dictated by the Z-order.

          **NOTE: This flag also determines the occlusion behavior in `layers`
          arguments to all game entities' `update` methods; see docstrings in
          [things.py] for details.**
    """
    self._rows = rows
    self._cols = cols
    self._occlusion_in_layers = occlusion_in_layers

    # This game's Plot object
    self._the_plot = plot.Plot()

    # True iff its_showtime() has been called and the game is underway.
    self._showtime = False
    # True iff the game has terminated. (It's still "showtime", though.)
    self._game_over = False

    # This game's Backdrop object.
    self._backdrop = None

    # This game's collection of Sprites and Drapes. The ordering of this dict
    # is the game's z-order, from back to front.
    self._sprites_and_drapes = collections.OrderedDict()

    # The collection of update groups. Before the its_showtime call, this is a
    # dict keyed by update group name, whose values are lists of Sprites and
    # Drapes in the update group. After the call, this becomes a dict-like list
    # of tuples that freezes the ordering implied by the update-group keys.
    self._update_groups = collections.defaultdict(list)

    # The current update group---used by add(). Will be set to None once the
    # game is underway.
    self._current_update_group = ''

    # This slot will hold the observation renderer once the game is underway.
    self._renderer = None

    # And this slot will hold the last observation rendered by the renderer.
    # It is not intended that this member be available to the user directly.
    # Code should not keep local references to this object or its members.
    self._board = None

  def set_backdrop(self, characters, backdrop_class, *args, **kwargs):
    """Add a `Backdrop` to this `Engine`.

    A `Backdrop` supplies the background scenery to be painted onto the game
    board using the characters specified in `characters`. It is always first
    (rearmost) in the z-order and first consulted by the `Engine` for board
    changes.

    Args:
      characters: A collection of ASCII characters that the `Backdrop` is
          allowed to use. (A string will work as an argument here.)
      backdrop_class: A subclass of `Backdrop` (including `Backdrop` itself)
          that will be constructed by this method.
      *args: Additional positional arguments for the `backdrop_class`
          constructor.
      **kwargs: Additional keyword arguments for the `backdrop_class`
          constructor.

    Returns:
      the newly-created `Backdrop`.

    Raises:
      RuntimeError: if gameplay has already begun, if `set_backdrop` has already
          been called for this engine, or if any characters in `characters` has
          already been claimed by a preceding call to the `add` method.
      TypeError: if `backdrop_class` is not a `Backdrop` subclass.
      ValueError: if `characters` are not ASCII characters.
    """
    self._runtime_error_if_called_during_showtime('set_backdrop')
    return self.set_prefilled_backdrop(
        characters, np.zeros((self._rows, self._cols), dtype=np.uint8),
        backdrop_class, *args, **kwargs)

  def set_prefilled_backdrop(
      self, characters, prefill, backdrop_class, *args, **kwargs):
    """Add a `Backdrop` to this `Engine`, with a custom initial pattern.

    Much the same as `set_backdrop`, this method also allows callers to
    "prefill" the background with an arbitrary pattern. This method is mainly
    intended for use by the `ascii_art` tools; most `Backdrop` subclasses should
    fill their `curtain` on their own in the constructor (or in `update()`).

    This method does NOT check to make certain that `prefill` contains only
    ASCII values corresponding to characters in `characters`; your `Backdrop`
    class should ensure that only valid characters are present in the curtain
    after the first call to its `update` method returns.

    Args:
      characters: A collection of ASCII characters that the `Backdrop` is
          allowed to use. (A string will work as an argument here.)
      prefill: 2-D `uint8` numpy array of the same dimensions as this `Engine`.
          The `Backdrop`'s curtain will be initialised with this pattern.
      backdrop_class: A subclass of `Backdrop` (including `Backdrop` itself)
          that will be constructed by this method.
      *args: Additional positional arguments for the `backdrop_class`
          constructor.
      **kwargs: Additional keyword arguments for the `backdrop_class`
          constructor.

    Returns:
      the newly-created `Backdrop`.

    Raises:
      RuntimeError: if gameplay has already begun, if `set_backdrop` has already
          been called for this engine, or if any characters in `characters` has
          already been claimed by a preceding call to the `add` method.
      TypeError: if `backdrop_class` is not a `Backdrop` subclass.
      ValueError: if `characters` are not ASCII characters.
    """
    self._runtime_error_if_called_during_showtime('set_prefilled_backdrop')
    self._value_error_if_characters_are_bad(characters)
    self._runtime_error_if_characters_claimed_already(characters)
    if self._backdrop:
      raise RuntimeError('A backdrop of type {} has already been supplied to '
                         'this Engine.'.format(type(self._backdrop)))
    if not issubclass(backdrop_class, things.Backdrop):
      raise TypeError('backdrop_class arguments to Engine.set_backdrop must '
                      'either be a Backdrop class or one of its subclasses.')

    # Construct a new curtain and palette for the Backdrop.
    curtain = np.zeros((self._rows, self._cols), dtype=np.uint8)
    palette = Palette(characters)

    # Fill the curtain with the prefill data.
    np.copyto(dst=curtain, src=prefill, casting='equiv')

    # Build and set the Backdrop.
    self._backdrop = backdrop_class(curtain, palette, *args, **kwargs)

    return self._backdrop

  def add_drape(self, character, drape_class, *args, **kwargs):
    """Add a `Drape` to this `Engine`.

    A `Drape` supplies masks that the Engine uses to paint the same character to
    multiple different places on the board.  The positions of a particular
    `Drape` in the painting order (z-order) and the `Engine`'s board change
    consultation order are determined by order of its addition to the `Engine`
    and various other factors; see the `Engine` constructor docstring for
    details.

    Args:
      character: The ASCII character that this `Drape` directs the `Engine`
          to paint on the game board.
      drape_class: A subclass of `Drape` to be constructed by this method.
      *args: Additional positional arguments for the `drape_class` constructor.
      **kwargs: Additional keyword arguments for the `drape_class` constructor.

    Returns:
      the newly-created `Drape`.

    Raises:
      RuntimeError: if gameplay has already begun, or if any characters in
          `characters` has already been claimed by a preceding call to the
          `set_backdrop` or `add` methods.
      TypeError: if `drape_class` is not a `Drape` subclass.
      ValueError: if `character` is not a single ASCII character.
    """
    self._runtime_error_if_called_during_showtime('add_drape')
    return self.add_prefilled_drape(
        character, np.zeros((self._rows, self._cols), dtype=np.bool_),
        drape_class, *args, **kwargs)

  def add_prefilled_drape(
      self, character, prefill, drape_class, *args, **kwargs):
    """Add a `Drape` to this `Engine`, with a custom initial mask.

    Much the same as `add_drape`, this method also allows callers to "prefill"
    the drape's `curtain` with an arbitrary mask. This method is mainly intended
    for use by the `ascii_art` tools; most `Drape` subclasses should fill their
    `curtain` on their own in the constructor (or in `update()`).

    Args:
      character: The ASCII character that this `Drape` directs the `Engine`
          to paint on the game board.
      prefill: 2-D `bool_` numpy array of the same dimensions as this `Engine`.
          The `Drape`'s curtain will be initialised with this pattern.
      drape_class: A subclass of `Drape` to be constructed by this method.
      *args: Additional positional arguments for the `drape_class` constructor.
      **kwargs: Additional keyword arguments for the `drape_class` constructor.

    Returns:
      the newly-created `Drape`.

    Raises:
      RuntimeError: if gameplay has already begun, or if any characters in
          `characters` has already been claimed by a preceding call to the
          `set_backdrop` or `add` methods.
      TypeError: if `drape_class` is not a `Drape` subclass.
      ValueError: if `character` is not a single ASCII character.
    """
    self._runtime_error_if_called_during_showtime('add_prefilled_drape')
    self._value_error_if_characters_are_bad(character, mandatory_len=1)
    self._runtime_error_if_characters_claimed_already(character)
    if not issubclass(drape_class, things.Drape):
      raise TypeError('drape_class arguments to Engine.add_drape must be a '
                      'subclass of Drape')

    # Construct a new curtain for the drape.
    curtain = np.zeros((self._rows, self._cols), dtype=np.bool_)

    # Fill the curtain with the prefill data.
    np.copyto(dst=curtain, src=prefill, casting='equiv')

    # Build and save the drape.
    drape = drape_class(curtain, character, *args, **kwargs)
    self._sprites_and_drapes[character] = drape
    self._update_groups[self._current_update_group].append(drape)

    return drape

  def add_sprite(self, character, position, sprite_class, *args, **kwargs):
    """Add a `Sprite` to this `Engine`.

    A `Sprite` supplies coordinates that the Engine uses to paint a character to
    one place on the board. The positions of a particular `Sprite` in the
    painting order (z-order) and the `Engine`'s board change consultation order
    are determined by order of its addition to the `Engine` and various other
    factors; see the `Engine` constructor docstring for details.

    Args:
      character: The ASCII character that this `Sprite` directs the `Engine`
          to paint on the game board.
      position: A 2-tuple or similar indexable containing the `Sprite`'s
          initial position on the game board.
      sprite_class: A subclass of `Sprite` to be constructed by this method.
      *args: Additional positional arguments for the `sprite_class` constructor.
      **kwargs: Additional keyword arguments for the `sprite_class` constructor.

    Returns:
      the newly-created `Sprite`.

    Raises:
      RuntimeError: if gameplay has already begun, or if any characters in
          `characters` has already been claimed by a preceding call to the
          `set_backdrop` or `add` methods.
      TypeError: if `sprite_class` is not a `Sprite` subclass.
      ValueError: if `character` is not a single ASCII character, or if
          `position` is not a valid game board coordinate.
    """
    self._runtime_error_if_called_during_showtime('add_sprite')
    self._value_error_if_characters_are_bad(character, mandatory_len=1)
    self._runtime_error_if_characters_claimed_already(character)
    if not issubclass(sprite_class, things.Sprite):
      raise TypeError('sprite_class arguments to Engine.add_sprite must be a '
                      'subclass of Sprite')
    if (not 0 <= position[0] < self._rows or
        not 0 <= position[1] < self._cols):
      raise ValueError('Position {} does not fall inside a {}x{} game board.'
                       ''.format(position, self._rows, self._cols))

    # Construct the game board dimensions for the benefit of this sprite.
    corner = things.Sprite.Position(self._rows, self._cols)

    # Construct a new position for the sprite.
    position = things.Sprite.Position(*position)

    # Build and save the drape.
    sprite = sprite_class(corner, position, character, *args, **kwargs)
    self._sprites_and_drapes[character] = sprite
    self._update_groups[self._current_update_group].append(sprite)

    return sprite

  def update_group(self, group_name):
    """Change the update group for subsequent `add_sprite`/`add_drape` calls.

    The `Engine` consults `Sprite`s and `Drape`s for board updates in an order
    determined first by the update group name, then by the order in which the
    `Sprite` or `Drape` was added to the `Engine`. See the `Engine` constructor
    docstring for more details.

    It's fine to return to an update group after leaving it.

    Args:
      group_name: name of the new current update group.

    Raises:
      RuntimeError: if gameplay has already begun.
    """
    self._runtime_error_if_called_during_showtime('update_group')
    self._current_update_group = group_name

  def set_z_order(self, z_order):
    """Set the z-ordering of all `Sprite`s and `Drape`s in this engine.

    Specify the complete order in which all `Sprite`s and `Drape`s should have
    their characters painted onto the game board. This method is available
    during game set-up only.

    Args:
      z_order: an ordered collection of all of the characters corresponding to
          all `Sprite`s and `Drape`s registered with this `Engine`.

    Raises:
      RuntimeError: if gameplay has already begun.
      ValueError: if the set of characters in `z_order` does not match the
          set of characters corresponding to all `Sprite`s and `Drape`s
          registered with this `Engine`.
    """
    self._runtime_error_if_called_during_showtime('set_z_order')
    if (set(z_order) != set(self._sprites_and_drapes.keys()) or
        len(z_order) != len(self._sprites_and_drapes)):
      raise ValueError('The z_order argument {} to Engine.set_z_order is not a '
                       'proper permutation of the characters corresponding to '
                       'Sprites and Drapes in this game, which are {}.'.format(
                           repr(z_order), self._sprites_and_drapes.keys()))
    new_sprites_and_drapes = collections.OrderedDict()
    for character in z_order:
      new_sprites_and_drapes[character] = self._sprites_and_drapes[character]
    self._sprites_and_drapes = new_sprites_and_drapes

  def its_showtime(self):
    """Finalise `Engine` set-up and compute the first observation of the game.

    Switches the `Engine` from set-up mode, where more `Sprite`s and `Drape`s
    can be added, to "play" mode, where gameplay iterates via the `play` method.
    After this permanent modal switch, no further calls to `add_drape` or
    `add_sprite` can be made.

    Once in "play" mode, consults the `Backdrop` and all `Sprite`s and `Drape`s
    for updates, and uses these to compute the episode's first observation.

    Returns:
      A three-tuple with the following members:
        * A `rendering.Observation` object containing single-array and
          multi-array feature-map representations of the game board.
        * An initial reward given to the player (or players) (before it/they
          even gets/get a chance to play!). This reward can be any type---it all
          depends on what the `Backdrop`, `Sprite`s, and `Drape`s have
          communicated to the `Plot`. If none have communicated anything at all,
          this will be None.
        * A reinforcement learning discount factor value. By default, it will be
          1.0 if the game is still ongoing; if the game has just terminated
          (before the player got a chance to do anything!), `discount` will be
          0.0 unless the game has chosen to supply a non-standard value to the
          `Plot`'s `terminate_episode` method.

    Raises:
      RuntimeError: if this method is called more than once, or if no
          `Backdrop` class has ever been provided to the Engine.
    """
    self._runtime_error_if_called_during_showtime('its_showtime')

    # It's showtime!
    self._showtime = True

    # Now that all the Sprites and Drapes are known, convert the update groups
    # to a more efficient structure.
    self._update_groups = [(key, self._update_groups[key])
                           for key in sorted(self._update_groups.keys())]

    # And, I guess we promised to do this:
    self._current_update_group = None

    # Construct the game's observation renderer.
    chars = set(self._sprites_and_drapes.keys()).union(self._backdrop.palette)
    if self._occlusion_in_layers:
      self._renderer = rendering.BaseObservationRenderer(
          self._rows, self._cols, chars)
    else:
      self._renderer = rendering.BaseUnoccludedObservationRenderer(
          self._rows, self._cols, chars)

    # Render a "pre-initial" board rendering from all of the data in the
    # Engine's Backdrop, Sprites, and Drapes. This rendering is only used as
    # input to these entities to collect their updates for the very first frame;
    # as it accesses data members inside the entities directly, it doesn't
    # actually run any of their code (unless implementers ignore notes that say
    # "Final. Do not override.").
    self._render()

    # The behaviour of this method is now identical to play() with None actions.
    return self.play(None)

  def play(self, actions):
    """Perform another game iteration, applying player actions.

    Receives an action (or actions) from the player (or players). Consults the
    `Backdrop` and all `Sprite`s and `Drape`s for updates in response to those
    actions, and derives a new observation from them to show the user. Also
    collects reward(s) for the last action and determines whether the episode
    has terminated.

    Args:
      actions: Actions supplied by the external agent(s) in response to the last
          board. Could be a scalar, could be an arbitrarily nested structure
          of... stuff, it's entirely up to the game you're making. When the game
          begins, however, it is guaranteed to be None. Used for the `update()`
          method of the `Backdrop` and all `Sprite`s and `Layer`s.

    Returns:
      A three-tuple with the following members:
        * A `rendering.Observation` object containing single-array and
          multi-array feature-map representations of the game board.
        * An reward given to the player (or players) for having performed
          `actions` in response to the last observation. This reward can be any
          type---it all depends on what the `Backdrop`, `Sprite`s, and `Drape`s
          have communicated to the `Plot`. If none have communicated anything at
          all, this will be None.
        * A reinforcement learning discount factor value. By default, it will be
          1.0 if the game is still ongoing; if the game has just terminated
          (before the player got a chance to do anything!), `discount` will be
          0.0 unless the game has chosen to supply a non-standard value to the
          `Plot`'s `terminate_episode` method.

    Raises:
      RuntimeError: if this method has been called before the `Engine` has
          been finalised via `its_showtime()`, or if this method has been called
          after the episode has terminated.
    """
    if not self._showtime:
      raise RuntimeError('play() cannot be called until the Engine is placed '
                         'in "play mode" via the its_showtime() method.')
    if self._game_over:
      raise RuntimeError('play() was called after the episode handled by this '
                         'Engine has terminated.')

    # Update Backdrop and all Sprites and Drapes.
    self._update_and_render(actions)

    # Apply all plot directives that the Backdrop, Sprites, and Drapes have
    # submitted to the Plot during the update.
    reward, discount, should_rerender = self._apply_and_clear_plot()

    # If directives in the Plot changed our state in any way that would change
    # the appearance of the observation (e.g. changing the z-order), we'll have
    # to re-render it before we return it.
    if should_rerender: self._render()

    # Return first-frame rendering to the user.
    return self._board, reward, discount

  @property
  def the_plot(self):
    return self._the_plot

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
    """Obtain a copy of the game's current z-order."""
    return list(self._sprites_and_drapes.keys())

  ### Abstraction breakers ###

  @property
  def backdrop(self):
    """Obtain the `Engine`'s `Backdrop`.

    Most pycolab applications don't need to access individual game entities, so
    using this accessor may signal that your design challenges some abstraction
    conventions. The canonical way to communicate with entities, for example, is
    through messages in the Plot. Still, the final choice is yours. We recommend
    you limit yourself to read-only interactions with the returned `Backdrop`.

    Returns:
      The `Engine`'s `Backdrop` object.
    """
    return self._backdrop

  @property
  def things(self):
    """Obtain the `Engine`'s `Sprite`s and `Drape`s.

    Most pycolab applications don't need to access individual game entities, so
    using this accessor may signal that your design challenges some abstraction
    conventions. The canonical way to communicate with entities, for example, is
    through messages in the Plot. Still, the final choice is yours. We recommend
    you limit yourself to read-only interactions with the returned `Sprite`s and
    `Drape`s.

    Returns:
      A dict mapping ASCII characters to the `Sprite` and `Drape` entities that
          paint those characters onto the game board.
    """
    return {k: t for k, t in six.iteritems(self._sprites_and_drapes)}

  ### Private helpers ###

  def _update_and_render(self, actions):
    """Perform all game entity updates and render the next observation.

    This private method is the heart of the `Engine`: as dictated by the update
    order, it consults the `Backdrop` and all `Sprite`s and `Layer`s for
    updates, then renders the game board (`self._board`) based on those updates.

    Args:
      actions: Actions supplied by the external agent(s) in response to the last
          board. Could be a scalar, could be an arbitrarily nested structure
          of... stuff, it's entirely up to the game you're making. When the game
          begins, however, it is guaranteed to be None. Used for the `update()`
          method of the `Backdrop` and all `Sprite`s and `Layer`s.
    """
    assert self._board, (
        '_update_and_render() called without a prior rendering of the board')

    # A new frame begins!
    self._the_plot.frame += 1

    # We start with the backdrop; it doesn't really belong to an update group,
    # or it belongs to the first update group, depending on how you look at it.
    self._the_plot.update_group = None
    self._backdrop.update(actions,
                          self._board.board, self._board.layers,
                          self._sprites_and_drapes, self._the_plot)

    # Now we proceed through each of the update groups in the prescribed order.
    for update_group, entities in self._update_groups:
      # First, consult each item in this update group for updates.
      self._the_plot.update_group = update_group
      for entity in entities:
        entity.update(actions,
                      self._board.board, self._board.layers,
                      self._backdrop, self._sprites_and_drapes, self._the_plot)

      # Next, repaint the board to reflect the updates from this update group.
      self._render()

  def _render(self):
    """Render a new game board.

    Computes a new rendering of the game board, and assigns it to `self._board`,
    based on the current contents of the `Backdrop` and all `Sprite`s and
    `Drape`s. Uses properties of those objects to obtain those contents; no
    computation should be done on their part.

    Each object is "painted" on the board in a prescribed order: the `Backdrop`
    first, then the `Sprite`s and `Drape`s according to the z-order (the order
    in which they appear in `self._sprites_and_drapes`
    """
    self._renderer.clear()
    self._renderer.paint_all_of(self._backdrop.curtain)
    for character, entity in six.iteritems(self._sprites_and_drapes):
      # By now we should have checked fairly carefully that all entities in
      # _sprites_and_drapes are Sprites or Drapes.
      if isinstance(entity, things.Sprite) and entity.visible:
        self._renderer.paint_sprite(character, entity.position)
      elif isinstance(entity, things.Drape):
        self._renderer.paint_drape(character, entity.curtain)
    # Done with all the layers; render the board!
    self._board = self._renderer.render()

  def _apply_and_clear_plot(self):
    """Apply directives to this `Engine` found in its `Plot` object.

    These directives are requests from the `Backdrop` and all `Drape`s and
    `Sprite`s for the engine to alter its global state or its interaction with
    the player (or players). They include requests to alter the z-order,
    terminate the game, or report some kind of reward. For more information on
    these directives, refer to `Plot` object documentation.

    After collecting and applying these directives to the `Engine`s state, all
    are cleared in preparation for the next game iteration.

    Returns:
      A 2-tuple with the following elements:
        * A reward value summed over all of the rewards that the `Backdrop` and
          all `Drape`s and `Sprite`s requested be reported to the player (or
          players), or None if nobody specified a reward. Otherwise, this reward
          can be any type; it all depends on what the `Backdrop`, `Drape`s, and
          `Sprite`s have provided.
        * A boolean value indicating whether the `Engine` should re-render the
          observation before supplying it to the user. This is necessary if any
          of the Plot directives change the `Engine`'s state in ways that would
          change the appearance of the observation, like changing the z-order.

    Raises:
      RuntimeError: a z-order change directive in the Plot refers to a `Sprite`
          or `Drape` that does not exist.
    """
    directives = self._the_plot._get_engine_directives()  # pylint: disable=protected-access

    # So far, there's no reason to re-render the observation.
    should_rerender = False

    # We don't expect to have too many z-order changes, so this slow, simple
    # algorithm will probably do the trick.
    for move_this, in_front_of_that in directives.z_updates:
      # We have a z-order change, so re-rendering is necessary.
      should_rerender = True

      # Make sure that the characters in the z-order change directive correspond
      # to actual `Sprite`s and `Drape`s.
      if move_this not in self._sprites_and_drapes:
        raise RuntimeError(
            'A z-order change directive said to move a Sprite or Drape '
            'corresponding to character {}, but no such Sprite or Drape '
            'exists'.format(repr(move_this)))
      if in_front_of_that is not None:
        if in_front_of_that not in self._sprites_and_drapes:
          raise RuntimeError(
              'A z-order change directive said to move a Sprite or Drape in '
              'front of a Sprite or Drape corresponding to character {}, but '
              'no such Sprite or Drape exists'.format(repr(in_front_of_that)))

      # Each directive means replacing the entire self._sprites_and_drapes dict.
      new_sprites_and_drapes = collections.OrderedDict()

      # Retrieve the Sprite or Drape that we are directed to move.
      moving_sprite_or_drape = self._sprites_and_drapes[move_this]

      # This special case handles circumstances where a Sprite or Drape is moved
      # all the way to the back of the z-order.
      if in_front_of_that is None:
        new_sprites_and_drapes[move_this] = moving_sprite_or_drape

      # Copy all Sprites or Drapes into the new sprites_and_drapes OrderedDict,
      # inserting the moving entity in front of the one it's meant to occulude.
      for character, entity in six.iteritems(self._sprites_and_drapes):
        if character == move_this: continue
        new_sprites_and_drapes[character] = entity
        if character == in_front_of_that:
          new_sprites_and_drapes[move_this] = moving_sprite_or_drape

      # Install the OrderedDict just made as the new z-order and catalogue
      # of Sprites and Drapes.
      self._sprites_and_drapes = new_sprites_and_drapes

    # The Backdrop or one of the Sprites or Drapes may have directed the game
    # to end. Update our game-over flag.
    self._game_over = directives.game_over
    # Collect the sum of all rewards from this latest game iteration, in
    # preparation to return it to the player.
    reward = directives.summed_reward
    # Get the discount value from the latest game iteration.
    discount = directives.discount
    # Reset the Plot for the next game iteration, should there be one.
    self._the_plot._clear_engine_directives()  # pylint: disable=protected-access
    return reward, discount, should_rerender

  ### Helpers for error detection ###

  def _runtime_error_if_called_during_showtime(self, method_name):
    if self._showtime:
      raise RuntimeError('{} should not be called after its_showtime() '
                         'has been called'.format(method_name))

  def _runtime_error_if_characters_claimed_already(self, characters):
    for char in characters:
      if self._backdrop and char in self._backdrop.palette:
        raise RuntimeError('Character {} is already being used by '
                           'the backdrop'.format(repr(char)))
      if char in self._sprites_and_drapes:
        raise RuntimeError('Character {} is already being used by a sprite '
                           'or a drape'.format(repr(char)))

  def _value_error_if_characters_are_bad(self, characters, mandatory_len=None):
    if mandatory_len is not None and len(characters) != mandatory_len:
      raise ValueError(
          '{}, a string of length {}, was used where a string of length {} was '
          'required'.format(repr(characters), len(characters), mandatory_len))
    for char in characters:
      try:               # This test won't catch all non-ASCII characters; if
        ord(char)        # someone uses a unicode string, it'll pass. But that's
      except TypeError:  # hard to do by accident.
        raise ValueError('Character {} is not an ASCII character'.format(char))


class Palette(object):
  """A helper class for turning human-readable characters into numerical values.

  Classes like `Backdrop` need to assign certain `uint8` values to cells in the
  game board. Since these values are typically printable ASCII characters, this
  assignment can be both cumbersome (e.g. `board[r][c] = ord('j')`) and error-
  prone (what if 'j' isn't a valid value for the Backdrop to use?).

  A `Palette` object (which you can give a very short name, like `p`) is
  programmed with all of the valid characters for your Backdrop. Those that are
  valid Python variable names become attributes of the object, whose access
  yields the corresponding ASCII ordinal value (e.g. `p.j == 106`). Characters
  that are not legal Python names, like `#`, can be converted through lookup
  notation (e.g. `p['#'] == 35`). However, any character that was NOT programmed
  into the `Palette` object yields an `AttributeError` or and `IndexError`
  respectively.

  Finally, this class also supports a wide range of aliases for characters that
  are not valid variable names. There is a decent chance that the name you give
  to a symbolic character is there; for example, `p.hash == p['#'] == 35`. If
  it's not there, consider adding it...
  """

  _ALIASES = dict(
      backtick='`', backquote='`', grave='`',
      tilde='~',
      zero='0', one='1', two='2', three='3', four='4',
      five='5', six='6', seven='7', eight='8', nine='9',
      bang='!', exclamation='!', exclamation_point='!', exclamation_pt='!',
      at='@',
      # regrettably, £ is not ASCII.
      hash='#', hashtag='#', octothorpe='#', number_sign='#', pigpen='#',
      pound='#',
      dollar='$', dollar_sign='$', buck='$', mammon='$',
      percent='%', percent_sign='%', food='%',
      carat='^', circumflex='^', trap='^',
      and_sign='&', ampersand='&',
      asterisk='*', star='*', splat='*',
      lbracket='(', left_bracket='(', lparen='(', left_paren='(',
      rbracket=')', right_bracket=')', rparen=')', right_paren=')',
      dash='-', hyphen='-',
      underscore='_',
      plus='+', add='+',
      equal='=', equals='=',
      lsquare='[', left_square_bracket='[',
      rsquare=']', right_square_bracket=']',
      lbrace='{', lcurly='{', left_brace='{', left_curly='{',
      left_curly_brace='{',
      rbrace='}', rcurly='}', right_brace='}', right_curly='}',
      right_curly_brace='}',
      pipe='|', bar='|',
      backslash='\\', back_slash='\\', reverse_solidus='\\',
      semicolon=';',
      colon=':',
      tick='\'', quote='\'', inverted_comma='\'', prime='\'',
      quotes='"', double_inverted_commas='"', quotation_mark='"',
      zed='z',
      comma=',',
      less_than='<', langle='<', left_angle='<', left_angle_bracket='<',
      period='.', full_stop='.',
      greater_than='>', rangle='>', right_angle='>', right_angle_bracket='>',
      question='?', question_mark='?',
      slash='/', solidus='/',
  )

  def __init__(self, legal_characters):
    """Construct a new `Palette` object.

    Args:
      legal_characters: An iterable of characters that users of this `Palette`
          are allowed to use. (A string like "#.o " will work.)

    Raises:
      ValueError: a value inside `legal_characters` is not a single character.
    """
    for char in legal_characters:
      if len(char) != 1:
        raise ValueError('Palette constructor requires legal characters to be '
                         'actual single charaters. "{}" is not.'.format(char))
    self._legal_characters = set(legal_characters)

  def __getattr__(self, name):
    return self._actual_lookup(name, AttributeError)

  def __getitem__(self, key):
    return self._actual_lookup(key, IndexError)

  def __getstate__(self):
    # Because we define __getattr__, we also supply __getstate__ and
    # __setstate__ to avoid recursion during some pickling and copy operations.
    return self._legal_characters

  def __setstate__(self, state):
    self._legal_characters = set(state)

  def __contains__(self, key):
    # It is intentional, but probably not so important (as long as there are no
    # single-character aliases) that we do not do an aliases lookup for key.
    return key in self._legal_characters

  def __iter__(self):
    return iter(self._legal_characters)

  def _actual_lookup(self, key, error):
    """Helper: perform character validation and conversion to numeric value."""
    if key in self._ALIASES: key = self._ALIASES[key]
    if key in self._legal_characters: return ord(key)
    raise error(
        '{} is not a legal character in this Palette; legal characters '
        'are {}.'.format(key, list(self._legal_characters)))
