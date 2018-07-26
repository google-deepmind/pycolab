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

"""Base classes for all of the "stuff" that makes up the world.

A pycolab board is organised like a theatre stage, so for some useful
background, refer first to the [wikipedia article on theatrical scenery](
https://en.wikipedia.org/wiki/Theatrical_scenery#Types_of_scenery).
Seriously! It's short.

Now, welcome back. In pycolab, these things get to paint on the board:

* Backdrop: This is the background scenery, and there is only ever one Backdrop
    per game. A Backdrop paints onto the board first, and it can paint
    arbitrary characters (from a predefined set) at any location.
* Sprite: Sprites are "actors": they paint a single, fixed character onto the
    board. Their API is very much in keeping with being a little moving dot:
    mainly, all sprites have a row/column board location.
* Drape: A Drape is a binary mask which causes portions of the board to be
    painted with a single, fixed character.

As mentioned, a Backdrop paints first. Sprites and Drapes come next, using an
ordering you specify. (You can change this ordering in the game: maybe your
Sprite walks in front of a Drape.)

All Backdrops, Sprites, and Drapes that you implement *must* be deep-copyable.

Besides capturing the objects and scenery of the game, Backdrops, Sprites, and
Drapes also hold the game's logic, which is usually distributed among these
things in an object-oriented fashion. In each game iteration, a game's Backdrop
and all of its Sprites and Drapes are consulted by the game engine for updates
to the game's internal state, and to their own appearance and internal state
as well. Once everyone has been consulted, the engine renders the game board
and applies any requested state changes. See `Engine` documentation for details.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import abc
import collections
import six


class Backdrop(object):
  """Background scenery for a pycolab game board.

  A `Backdrop` paints the "background scenery" for a pycolab game: it fills an
  array with arbitrary characters (from its predefined `Palette`) which get
  painted onto the board before any `Sprite` or `Drape` is added there.
  """

  def __init__(self, curtain, palette):
    """Construct a `Backdrop`.

    Whatever arguments your `Backdrop` subclass takes, its first two should be
    the same `curtain` and `palette` arguments taken here.

    Unless you really know what you're doing, your `Backdrop` subclass should
    be certain to call this `__init__` method before doing anything else in its
    own constructor. Here's example code to copy and paste:

        super(MyCoolBackdrop, self).__init__(curtain, palette)

    Args:
      curtain: A 2-D numpy array with dtype `uint8`, which will be "owned" by
          this `Backdrop` and made accessible at `self.curtain`. Values in this
          array will be painted onto the game board first at each gameplay
          iteration. Subclasses of `Backdrop` will update the backdrop by
          changing the data inside `self.curtain`. May already have items in
          it before it gets received by `__init__` (for example, it may have
          been populated from an ASCII-art diagram).
      palette: A handy mapping from characters to the corresponding `uint8`
          values that you should use to update `self.curtain`. Characters that
          are legal Python names can be accessed using property notation, (e.g.
          `self.palette.M`); for others, you'll need to do dict-style lookups
          (e.g. `self.palette['~']`). (A few characters have special property
          names -- for example, `self.palette.space` is sugar for
          `self.palette[' ']`. See `Palette` docs for details.) This mapping
          will be "owned" by this `Backdrop` and made accessible at
          `self.palette`, but you may wish to abbreviate it in your methods
          (`p = self.palette`). Finally, note that if a character appears not
          to exist as a property or dict entry in the palette, it's not legal
          for you to use. (No peeking at an ASCII chart to get around this!)
    """
    # Direct access is highly discouraged. Use the properties instead.
    self._c_u_r_t_a_i_n = curtain
    self._p_a_l_e_t_t_e = palette

  def update(self, actions, board, layers, things, the_plot):
    """Update this `Backdrop`'s curtain in response to the rest of the world.

    This method is called once per game iteration and can perform arbitrary
    updates to the values inside `self.curtain` (using legal palette characters,
    of course). Upon completion, and after all other "things" have had a chance
    to update as well, `self.curtain` will be the first layer painted onto the
    next iteration of the board.

    This method _promises_ not to alter any of its arguments except `the_plot`.
    Saving non-temporary local references to any of the arguments is probably
    also a bad idea.

    Args:
      actions: Actions supplied by the external agent(s) in response to the last
          board. Could be a scalar, could be an arbitrarily nested structure
          of... stuff, it's entirely up to the game you're making. When the game
          begins, however, it is guaranteed to be None; the update that this
          Sprite produces then will be combined updates from other Things to
          generate the first observation of the game.
      board: A 2-D numpy array with dtype `uint8` containing the completely
          rendered game board from the last board repaint (which usually means
          the last game iteration; see `Engine` docs for details). Recall that
          Python's `chr` method can turn `uint8` values into single-character
          strings.
      layers: A feature-map representation of all game entities (current to
          the last board repaint); specifically, a dict mapping all characters
          known to the game's `Engine` to `bool_` numpy arrays indicating
          where those characters are found (if anywhere---these can be empty).
          Note that if the game's `Engine` was constructed with
          `occlusion_in_layers=True`, things that are "occluded" on `board` by
          overlapping Sprites and Drapes will not be visible in these feature
          maps, nor will Sprites and Drapes that are invisible.
      things: The complete inventory of Sprites and Drapes in this game, as a
          dict keyed by the characters they paint onto the board. These are NOT
          guaranteed to be current to the last repaint; they are current to the
          last time they were updated, which is dictated by the update ordering
          specified in the game's `Engine`. Some may have been updated since
          the last repaint (i.e. they get updated before this `Backdrop`),
          others not.
      the_plot: A global blackboard for marking events that should be shared
          between Sprites, Drapes, the Backdrop, and the game's `Engine`.
          There's a lot of neat stuff in here; refer to `Plot` docs for details.
    """
    # A default backdrop never changes, so there's nothing to update.
    pass

  @property
  def curtain(self):
    # Final. Do not override.
    return self._c_u_r_t_a_i_n

  @property
  def palette(self):
    # Final. Do not override.
    return self._p_a_l_e_t_t_e


@six.add_metaclass(abc.ABCMeta)
class Drape(object):
  """A shape that "drapes" over parts of a pycolab game board.

  A `Drape` is a binary mask associated with a particular character. When the
  `Drape` is rendered onto the game board, any portion of the board covered by
  the mask will be filled with the character.
  """

  def __init__(self, curtain, character):
    """Construct a `Drape`.

    Whatever arguments your `Drape` subclass takes, its first two should be the
    same `curtain` and `character` arguments taken here.

    Unless you really know what you're doing, your `Drape` subclass should be
    certain to call this `__init__` method before doing anything else in its own
    constructor. Here's example code to copy and paste:

        super(MyCoolDrape, self).__init__(curtain, character)

    A `Drape` object that does not wish to be visible after construction should
    have its constructor assign `self._visible = False` after calling its
    superclass constructor.

    Args:
      curtain: A 2-D numpy array with dtype `bool_`, which will be "owned" by
          this `Drape` and made accessible at `self.curtain`. Values in this
          array will be used as a mask for painting `character` onto the
          game board, at whatever time is dictated by this game's `Engine`'s
          z-ordering. Subclasses of `Drape` will update the mask by changing
          the data inside `self.curtain`.
      character: The character that this `Drape` paints onto the board.
          Subclasses will not paint this character directly; it's here for
          the object's reference when examining the arguments to `update`.
    """
    # Direct access is highly discouraged. Use the properties instead.
    self._c_u_r_t_a_i_n = curtain
    self._c_h_a_r_a_c_t_e_r = character

  @abc.abstractmethod
  def update(self, actions, board, layers, backdrop, things, the_plot):
    """Update this `Drape`'s curtain in response to the rest of the world.

    This method is called once per game iteration and can perform arbitrary
    updates to the values inside `self.curtain` (using bool values, of course).
    Upon completion, and after the backdrop and all other "things" have had a
    chance to update as well, `self.curtain` will be used as a mask for painting
    `self.character` on the game board, at whatever time is dictated by this
    game's `Engine`'s z-ordering.

    This method _promises_ not to alter any of its arguments except `the_plot`.
    Saving non-temporary local references to any of the arguments is probably
    also a bad idea.

    Args:
      actions: Actions supplied by the external agent(s) in response to the last
          board. Could be a scalar, could be an arbitrarily nested structure
          of... stuff, it's entirely up to the game you're making. When the game
          begins, however, it is guaranteed to be None; the update that this
          Sprite produces then will be combined updates from other Things to
          generate the first observation of the game.
      board: A 2-D numpy array with dtype `uint8` containing the completely
          rendered game board from the last board repaint (which usually means
          the last game iteration; see `Engine` docs for details). Recall that
          Python's `chr` method can turn `uint8` values into single-character
          strings.
      layers: A feature-map representation of all game entities (current to
          the last board repaint); specifically, a dict mapping all characters
          known to the game's `Engine` to `bool_` numpy arrays indicating where
          those characters are found (if anywhere---these can be empty). Note
          that if the game's `Engine` was constructed with
          `occlusion_in_layers=True`, things that are "occluded" on `board` by
          overlapping Sprites and Drapes will not be visible in these feature
          maps, nor will Sprites and Drapes that are invisible.
      backdrop: The `Backdrop` for this game. This is NOT guaranteed to be
          current to the last repaint; it is current to the last time it was
          updated, which is dictated by the update ordering specified in this
          game's `Engine`. It may or may not have been updated since the last
          repaint.
      things: The complete inventory of Sprites and Drapes in this game, as a
          dict keyed by the characters they paint onto the board. These are NOT
          guaranteed to be current to the last repaint; they are current to the
          last time they were updated, which is dictated by the update ordering
          specified in the game's `Engine`. Some may have been updated since
          the last repaint (i.e. they get updated before this `Drape`), others
          not. (Note that `things[self.character] == self`.)
      the_plot: A global blackboard for marking events that should be shared
          between Sprites, Drapes, the Backdrop, and the game's `Engine`.
          There's a lot of neat stuff in here; refer to `Plot` docs for details.
    """
    pass

  @property
  def character(self):
    # Final. Do not override.
    return self._c_h_a_r_a_c_t_e_r

  @property
  def curtain(self):
    # Final. Do not override.
    return self._c_u_r_t_a_i_n


@six.add_metaclass(abc.ABCMeta)
class Sprite(object):
  """A single-cell organism that moves around a pycolab game board.

  A `Sprite` is a row-column location associated with a particular character
  (in all senses of the word). When the `Sprite` is rendered onto the game
  board, the character will be placed in its row-column location.
  """

  class Position(collections.namedtuple('Position', ['row', 'col'])):
    """Position container for `Sprite`s.

    Member properties are `row` and `col`, respectively the row and column
    location of the `Sprite` on the board.
    """
    __slots__ = ()

  def __init__(self, corner, position, character):
    """Construct a `Sprite`.

    Whatever arguments your `Sprite` subclass takes, its first three should be
    the same `corner`, `position`, and `character` arguments taken here.

    Unless you really know what you're doing, your `Sprite` subclass should be
    certain to call this `__init__` method before doing anything else in its own
    constructor. Here's example code to copy and paste:

        super(MyCoolSprite, self).__init__(corner, position, character)

    A `Sprite` object that does not wish to be visible after construction should
    have its constructor assign `self._visible = False` after calling its
    superclass constructor.

    Args:
      corner: A `self.Position` instance whose `row` member is the height of the
          game board and whose `col` member is the width of the game board.
          These values should always be larger than the `row` and `col` position
          of this sprite respectively.
      position: A `self.Position` instance encoding the initial position of
          this sprite.
      character: The character that this `Sprite` paints onto the board.
          Subclasses will not paint this character directly; it's here for
          the object's reference when examining the arguments to `update`.
    """
    # The corner member is not to be accessed directly.
    self._c_o_r_n_e_r = corner
    # The character member is not to be accessed directly.
    self._c_h_a_r_a_c_t_e_r = character
    # The position member is fine for internal access, but external callers
    # must use the property. Note that the use of a namedtuple means that
    # positions are always passed (and updated) by value.
    self._position = position
    # By default, we have a simple flag that determines whether this Sprite is
    # visible. It's fine for subclasses to access and mutate this flag directly,
    # or to override the self.visible property function altogether.
    self._visible = True

  @abc.abstractmethod
  def update(self, actions, board, layers, backdrop, things, the_plot):
    """Update this `Sprite`'s position in response to the rest of the world.

    This method is called once per game iteration and can replace the value of
    `self.position` (though the new position ought to fall within `board`).
    Upon completion, and after the backdrop and all other "things" have had a
    chance to update as well, a single `self.character` will be painted on the
    game board at `self.position`, at whatever time is dictated by this game's
    `Engine`'s z-ordering.

    This method _promises_ not to alter any of its arguments except `the_plot`.
    Saving non-temporary local references to any of the arguments is probably
    also a bad idea.

    Args:
      actions: Actions supplied by the external agent(s) in response to the last
          board. Could be a scalar, could be an arbitrarily nested structure
          of... stuff, it's entirely up to the game you're making. When the game
          begins, however, it is guaranteed to be None; the update that this
          Sprite produces then will be combined updates from other Things to
          generate the first observation of the game.
      board: A 2-D numpy array with dtype `uint8` containing the completely
          rendered game board from the last board repaint (which usually means
          the last game iteration; see `Engine` docs for details). Recall that
          Python's `chr` method can turn `uint8` values into single-character
          strings.
      layers: A feature-map representation of all game entities (current to
          the last board repaint); specifically, a dict mapping all characters
          known to the game's `Engine` to `bool_` numpy arrays indicating
          where those characters are found (if anywhere---these can be empty).
          Note that if the game's `Engine` was constructed with
          `occlusion_in_layers=True`, things that are "occluded" on `board` by
          overlapping Sprites and Drapes will not be visible in these feature
          maps, nor will Sprites and Drapes that are invisible.
      backdrop: The `Backdrop` for this game. This is NOT guaranteed to be
          current to the last repaint; it is current to the last time it was
          updated, which is dictated by the update ordering specified in this
          game's `Engine`. It may or may not have been updated since the last
          repaint.
      things: The complete inventory of Sprites and Drapes in this game, as a
          dict keyed by the characters they paint onto the board. These are NOT
          guaranteed to be current to the last repaint; they are current to the
          last time they were updated, which is dictated by the update ordering
          specified in the game's `Engine`. Some may have been updated since
          the last repaint (i.e. they get updated before this `Drape`), others
          not. (Note that `things[self.character] == self`.)
      the_plot: A global blackboard for marking events that should be shared
          between Sprites, Drapes, the Backdrop, and the game's `Engine`.
          There's a lot of neat stuff in here; refer to `Plot` docs for details.
    """
    pass

  @property
  def character(self):
    # Final. Do not override.
    return self._c_h_a_r_a_c_t_e_r

  @property
  def corner(self):
    # Final. Do not override.
    return self._c_o_r_n_e_r

  @property
  def position(self):
    # Final. Do not override.
    return self._position

  @property
  def visible(self):
    return self._visible
