# coding=utf8

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

""""Prefabricated" `Sprite`s with all kinds of useful behaviour."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from pycolab import things
from pycolab.protocols import scrolling


class MazeWalker(things.Sprite):
  """A base class for "maze walkers" (e.g. Pac-Man, Zelda, Sokoban).

  If your game shows a top-down view of a world where a character can go in all
  directions (not counting walls, etc.), then a `MazeWalker` is a `Sprite` that
  contains much of the functionality you need to build that character. It's up
  to you to make a `MazeWalker` subclass that implements the actual `update`
  method, but the "motion action" helper methods `_north`, `_south`, `_east`,
  `_west`, `_northeast`, `_northwest`, `_southeast`, and `_southwest` will
  hopefully make this easy to do. Call these methods, and your `Sprite` will
  move in that direction---or the method will return a reason why it can't do
  that (read on).

  There is also a `_stay` method which doesn't move the `Sprite` at all.
  Although it may seem useless, *you should consider calling it in your `update`
  method whenever you want your `MazeWalker` to stay put*; if you do this, then
  your `Sprite` will abide by the "scrolling" protocol (see
  `protocols/scrolling.py`) "out of the box".

  ## Obstructions

  On construction, you can tell a `MazeWalker` which characters in the board it
  cannot traverse. If the `MazeWalker` would "step on" one of these characters
  at any time whilst executing any of the motion actions, its position will not
  be updated.

  Attempts to move in any of the four "cardinal directions" will fail if one of
  these "impassable" characters is in the place where the `MazeWalker` is
  attempting to move. For diagonal motions, a motion will fail if two "corners"
  are in the way. By example, if we assume that '#' is an impassable character,
  then if a `MazeWalker` is attempting to move from position A to position B in
  each of the following scenarios:

      Scenario #1:      Scenario #2:      Scenario #3:      Scenario #4:
          +--+              +--+              +--+              +--+
          |A |              |A |              |A#|              |A#|
          | B|              |#B|              | B|              |#B|
          +--+              +--+              +--+              +--+

  the motion will succeed in all of them except #4. Of course, failure will also
  occur if B contains an impassable character.

  If a motion action helper method completes succesfully, it returns None.
  Otherwise, it returns the impassable character (for "cardinal directions")
  or characters (for "diagonal directions"---as a 3-tuple containing the
  impassable character to the left of the motion vector (or None if that
  character is passable), the character at the end of the motion vector
  (likewise), and the character to the right of the motion vector (likewise)).
  Thus you can always determine whether a motion action helper method has failed
  by casting its return value to bool. (If this MazeWalker is not permitted to
  exit the game board, per the `confined_to_board` constructor argument, then
  obstructions that happen to be the impassable edge of the game board will be
  represented as `MazeWalker.EDGE` constants.)

  By default, a `MazeWalker` will happily walk right off the game board if you
  tell it to (or if it gets scrolled off the board; see
  `protocols/scrolling.py`). If it does, it makes itself invisible (unless you
  override that behaviour) and sets its true position (i.e. the one available
  via the `position` property) to `0, 0`.  The `MazeWalker` keeps track of the
  coordinates for where it _would_ have gone, however (its "virtual position",
  available via the `virtual_position` property), and continues to update these
  as directed by the motion action helper methods. If the `MazeWalker` manages
  to "walk back" onto the game board somewhere, its original visibility is
  restored, and its true position is set to that location.

  As far as default `MazeWalker`s are concerned, the world outside of the game
  board is a magical land free from all obstructions. A `MazeWalker` can move in
  any direction out there that it wants.

  ## `MazeWalker`s and scrolling

  If your game does not feature scrolling scenery, you can ignore this section.

  As mentioned above, `MazeWalker`s are built to accommodate the scrolling
  protocol (see `protocols/scrolling.py`) "out of the box"; that is, if a
  game entity (e.g. a `drapes.Scrolly`) commands the game world to shift its
  position on the game board, a `MazeWalker` will obey in accordance with
  whether it is "egocentric". (Provided, of course, that your `MazeWalker`
  calls `self._stay()` on game iterations when it doesn't move.)

  An ordinary `MazeWalker` will simply shift itself so that it remains in the
  same place relative to the game world. An egocentric `MazeWalker` will remain
  at the same place on the game board and allow the world to shift around it.

  Egocentric `MazeWalker`s cannot allow themselves to be scrolled into walls and
  other obstacles, so as part of the scrolling protocol, they automatically
  calculate and inform other protocol participants of the directions they will
  be able to move at the next game iteration. In order for this calculation to
  be accurate, in nearly all circumstances, game entities that control
  obstructing characters for this `MazeWalker` should be in separate and earlier
  update groups, allowing the `MazeWalker` to know what the world will look like
  at the next game iteration.

  _Now for an unfortunate qualification of the two preceding paragraphs._
  Egocentric `MazeWalker`s don't always remain in the same board-relative place
  when the rest of the world scrolls, and sometimes `MazeWalker`s will abide by
  scrolling orders that it did not tell the other protocol participants were
  legal. For details of this unfortunate special case and an example, see the
  section "On the loose interpretation of 'legal' scrolling motions" in
  `protocols/scrolling.py`.

  This permissiveness allows for a more pleasing scrolling experience in concert
  with `Drape`s that derive from `drapes.Scrolly`, but it requires that the
  `Drape` issue the scrolling order, and that the issuing `Drape` and all other
  participating egocentric entities issue the exact same motion action helper
  methods at each game iteration.
  """

  # Used in motion action helper method return values to represent the edge
  # of the game board.
  EDGE = 'edge!'

  # Predefined single-step motions, for internal use only. Positive values in
  # the first field mean move downward; positive values in the second field
  # mean move rightward.
  _NORTH = (-1, 0)
  _NORTHEAST = (-1, 1)
  _EAST = (0, 1)
  _SOUTHEAST = (1, 1)
  _SOUTH = (1, 0)
  _SOUTHWEST = (1, -1)
  _WEST = (0, -1)
  _NORTHWEST = (-1, -1)
  # Not technically a single-step motion.
  _STAY = (0, 0)

  def __init__(self, corner, position, character, impassable,
               confined_to_board=False,
               egocentric_scroller=False,
               scrolling_group=''):
    """Superclass constructor for `MazeWalker`-derived classes.

    `MazeWalker` does not define `Sprite.update`, so this constructor will fail
    if you attempt to build a `MazeWalker` on its own.

    Args:
      corner: required by `Sprite`.
      position: required by `Sprite`.
      character: required by `Sprite`.
      impassable: an indexable of ASCII characters that this `MazeWalker` is not
          able to traverse. A string value containing these characters works.
      confined_to_board: whether this `MazeWalker` is allowed to walk off of
          the game board, or to be scrolled off of the game board.
      egocentric_scroller: whether this `MazeWalker` should behave as an
          egocentric scroller with respect to `scrolling_group` (see
          `protocols/scrolling.py`). If your game does not feature a scrolling
          game board, you don't need to worry about this argument.
      scrolling_group: the scrolling group that this `MazeWalker` should
          participate in, if not the default (`''`). If your game does not
          feature a scrolling game world, you don't need to worry about this
          argument.

    Raises:
      TypeError: `impassable` contains values that are not ASCII characters.
      ValueError: `impassable` contains the character that represents this
          `MazeWalker` on the game board.
    """
    super(MazeWalker, self).__init__(corner, position, character)
    _character_check(impassable, 'impassable', 'the MazeWalker constructor')
    if character in impassable:
      raise ValueError('A MazeWalker must not designate its own character {} '
                       'as impassable.'.format(repr(character)))

    # Save various constructor arguments.
    self._impassable = set(impassable)
    self._confined_to_board = confined_to_board
    self._egocentric_scroller = egocentric_scroller
    self._scrolling_group = scrolling_group

    # These coordinates are always relative to the board's origin at (0, 0), but
    # they are allowed to range beyond the bounds of the board.
    self._virtual_row, self._virtual_col = position

    # When the MazeWalker leaves the board, this will hold the visibility it
    # had just before it left. Unless overridden, the default behaviour is for
    # this visibility to be restored to the MazeWalker if it ever returns to
    # the board.
    self._prior_visible = None

  @property
  def virtual_position(self):
    """This `MazeWalker's "virtual position" (see class docstring)."""
    return self.Position(self._virtual_row, self._virtual_col)

  @property
  def on_the_board(self):
    """True iff the `MazeWalker`'s "virtual position" is on the game board."""
    return self._on_board(self._virtual_row, self._virtual_col)

  @property
  def impassable(self):
    """The set of characters that this `MazeWalker` cannot traverse."""
    return self._impassable

  ### Protected helpers (okay to override) ###

  def _on_board_exit(self):
    """Code to run just before a `MazeWalker` exits the board.

    Whatever is in this method is executed immediately prior to a `MazeWalker`
    exiting the game board, either under its own power or due to scrolling.
    ("Exiting" refers to the `MazeWalker`'s "virtual position"---see class
    docstring---since a `Sprite`'s true position cannot be outside of the game
    board.)

    Note that on certain rare occasions, it's possible for this method to run
    alongside `_on_board_enter` in the same game iteration. On these occasions,
    the `MazeWalker` is scrolled off the board, but then it performs a move in
    the opposite direction (at least in part) that brings it right back on. Or,
    vice versa: the `MazeWalker` gets scrolled onto the board and then walks
    back off.

    By default, this method caches the `MazeWalker`'s previous visibility and
    then makes the `MazeWalker` invisible---a reasonable thing to do, since it
    will be moved to "real" position `(0, 0)` as long as its virtual position
    is not on the game board. If you would like to preserve this behaviour
    but trigger additional actions on board exit, override this method, but be
    sure to call this class's own implementation of it, too. Copy and paste:

        super(MyCoolMazeWalker, self)._on_board_exit()
    """
    self._prior_visible = self._visible
    self._visible = False

  def _on_board_enter(self):
    """Code to run just after a `MazeWalker` enters the board.

    Whatever is in this method is executed immediately after a `MazeWalker`
    enters the game board, either under its own power or due to scrolling.
    ("Entering" refers to the `MazeWalker`'s "virtual position"---see class
    docstring---since a `Sprite`'s true position cannot be outside of the game
    board.)

    Note that on certain rare occasions, it's possible for this method to run
    alongside `_on_board_exit` in the same game iteration. On these occasions,
    the `MazeWalker` is scrolled off the board, but then it performs a move in
    the opposite direction (at least in part) that brings it right back on. Or,
    vice versa: the `MazeWalker` gets scrolled onto the board and then walks
    back off.

    By default, this method restores the `MazeWalker`'s previous visibility as
    cached by `_on_board_exit`. If you would like to preserve this behaviour
    but trigger additional actions on board exit, override this method, but be
    sure to call this class's own implementation of it, too. Copy and paste:

        super(MyCoolMazeWalker, self)._on_board_enter()
    """
    # called just after board entrance
    self._visible = self._prior_visible

  ### Protected helpers (final, do not override) ###

  def _northwest(self, board, the_plot):
    """Try moving one cell upward and leftward. Returns `None` on success."""
    return self._move(board, the_plot, self._NORTHWEST)

  def _north(self, board, the_plot):
    """Try moving one cell upward. Returns `None` on success."""
    return self._move(board, the_plot, self._NORTH)

  def _northeast(self, board, the_plot):
    """Try moving one cell upward and rightward. Returns `None` on success."""
    return self._move(board, the_plot, self._NORTHEAST)

  def _east(self, board, the_plot):
    """Try moving one cell rightward. Returns `None` on success."""
    return self._move(board, the_plot, self._EAST)

  def _southeast(self, board, the_plot):
    """Try moving one cell downward and rightward. Returns `None` on success."""
    return self._move(board, the_plot, self._SOUTHEAST)

  def _south(self, board, the_plot):
    """Try moving one cell downward. Returns `None` on success."""
    return self._move(board, the_plot, self._SOUTH)

  def _southwest(self, board, the_plot):
    """Try moving one cell downward and leftward. Returns `None` on success."""
    return self._move(board, the_plot, self._SOUTHWEST)

  def _west(self, board, the_plot):
    """Try moving one cell leftward. Returns `None` on success."""
    return self._move(board, the_plot, self._WEST)

  def _stay(self, board, the_plot):
    """Remain in place, but account for any scrolling that may have happened."""
    return self._move(board, the_plot, self._STAY)

  def _teleport(self, virtual_position):
    """Set the new virtual position of the agent, applying side-effects.

    This method is a somewhat "low level" method: it doesn't check whether the
    new location has an impassible character in it, nor does it apply any
    scrolling orders that may be current (if called during a game iteration).
    This method is only grudgingly "protected" (and not "private"), mainly to
    allow `MazeWalker` subclasses to initialise their location at a place
    somewhere off the board. Use at your own risk.

    This method does handle entering and exiting the board in the conventional
    way. Virtual positions off of the board yield a true position of `(0, 0)`,
    and `_on_board_exit` and `_on_board_enter` are called as appropriate.

    Args:
      virtual_position: A 2-tuple containing the intended virtual position for
          this `MazeWalker`.
    """
    new_row, new_col = virtual_position
    old_row, old_col = self._virtual_row, self._virtual_col

    # Determine whether either, both, or none of the endpoints are on the board.
    old_on_board = self._on_board(old_row, old_col)
    new_on_board = self._on_board(new_row, new_col)

    # Call the exit handler if we are leaving the board.
    if old_on_board and not new_on_board: self._on_board_exit()

    # If our new virtual location is not on the board, set our true location
    # to 0, 0. Otherwise, true and virtual locations can be the same.
    self._virtual_row, self._virtual_col = new_row, new_col
    if new_on_board:
      self._position = self.Position(new_row, new_col)
    else:
      self._position = self.Position(0, 0)

    # Call the entry handler if we are entering the board.
    if not old_on_board and new_on_board: self._on_board_enter()

  ### Private helpers (do not call; final, do not override) ###

  def _move(self, board, the_plot, motion):
    """Handle all aspects of single-row and/or single-column movement.

    Implements every aspect of moving one step in any of the nine possible
    gridworld directions (includes staying put). This amounts to:

    1. Applying any scrolling orders (see `protocols/scrolling.py`).
    2. Making certain the motion is legal.
    3. If it is, applying the requested motion.
    4. If this is an egocentric `MazeWalker`, calculating which scrolling orders
       will be legal (as far as this `MazeWalker` is concerned) at the next
       iteration.
    5. Returning the success (None) or failure (see class docstring) result.

    Args:
      board: a 2-D numpy array with dtype `uint8` containing the completely
          rendered game board from the last board repaint (which usually means
          the last game iteration; see `Engine` docs for details).
      the_plot: this pycolab game's `Plot` object.
      motion: a 2-tuple whose components will be added to the `MazeWalker`'s
          virtual coordinates (row, column respectively) to obtain its new
          virtual position.

    Returns:
      None if the motion is executed successfully; otherwise, a tuple (for
      diagonal motions) or a single-character ASCII string (for motions in
      "cardinal direction") describing the obstruction blocking the
      `MazeWalker`. See class docstring for details.
    """
    self._obey_scrolling_order(motion, the_plot)
    check_result = self._check_motion(board, motion)
    if not check_result: self._raw_move(motion)
    self._update_scroll_permissions(board, the_plot)
    return check_result

  def _raw_move(self, motion):
    """Apply a dx, dy movement.

    This is the method that `_move` and `_obey_scrolling_order` actually use to
    move the `MazeWalker` on the game board, updating its "true" and "virtual"
    positions (see class docstring). The `_on_board_(enter|exit)` hooks are
    called here as needed. The behaviour whereby `MazeWalker`s that wander or
    fall off the board assume a true position of `(0, 0)` happens here as well.

    This method does not verify that `motion` is a legal move for this
    `MazeWalker`.

    Args:
      motion: a 2-tuple whose components will be added to the `MazeWalker`'s
          virtual coordinates (row, column respectively) to obtain its new
          virtual position.
    """
    # Compute "virtual" endpoints of the motion.
    new_row = self._virtual_row + motion[0]
    new_col = self._virtual_col + motion[1]
    self._teleport((new_row, new_col))

  def _obey_scrolling_order(self, motion, the_plot):
    """Look for a scrolling order in the `Plot` object and apply if present.

    Examines the `Plot` object to see if any entity preceding this `MazeWalker`
    in the update order has issued a scrolling order (see
    `protocols/scrolling.py`). If so, apply the additive inverse of the motion
    in the scrolling order so as to remain "stationary" with respect to the
    moving environment. (We expect that egocentric `MazeWalker`s will apply the
    motion itself soon after we return so that they remain stationary with
    respect to the board.)

    (Egocentric `MazeWalker`s only.) Makes certain that this `MazeWalker` is
    known to scrolling protocol participants as an egocentric entity, and
    verifies that any non-None scrolling order is identical to the motion that
    the `MazeWalker` is expected to perform.

    No effort is made to verify that the world scrolling around an egocentric
    `MazeWalker` will wind up putting the `MazeWalker` in an impossible
    position.

    Args:
      motion: the motion that this `MazeWalker` will execute during this game
          iteration (see docstring for `_move`).
      the_plot: this pycolab game's `Plot` object.

    Raises:
      RuntimeError: this `MazeWalker` is egocentric, and the current non-None
          scrolling order and the `MazeWalker`s motion have no components in
          common.
    """
    if self._egocentric_scroller:
      scrolling.participate_as_egocentric(self, the_plot, self._scrolling_group)

    order = scrolling.get_order(self, the_plot, self._scrolling_group)
    if order is not None:
      self._raw_move((-order[0], -order[1]))
      if (self._egocentric_scroller and
          order[0] != motion[0] and order[1] != motion[1]): raise RuntimeError(
              'An egocentric MazeWalker corresponding to {} received a scroll '
              'order {} that has no component in common with the motion {}, '
              'which the MazeWalker was to carry out during the same game '
              'iteration'.format(repr(self.character), order, motion))

  def _update_scroll_permissions(self, board, the_plot):
    """Compute scrolling motions that will be compatible with this `MazeWalker`.

    (Egocentric `MazeWalker`s only.) After the virtual position of this
    `MazeWalker` has been updated by `_move`, declare which scrolling motions
    will be legal on the next game iteration. (See `protocols/scrolling.py`.)

    Args:
      board: a 2-D numpy array with dtype `uint8` containing the completely
          rendered game board from the last board repaint (which usually means
          the last game iteration; see `Engine` docs for details).
      the_plot: this pycolab game's `Plot` object.
    """
    # to call after our location has been updated
    if not self._egocentric_scroller: return

    legal_motions = [self._STAY]
    for motion in (self._NORTH, self._NORTHEAST, self._EAST, self._SOUTHEAST,
                   self._SOUTH, self._SOUTHWEST, self._WEST, self._NORTHWEST):
      if not self._check_motion(board, motion): legal_motions.append(motion)

    scrolling.permit(self, the_plot, legal_motions, self._scrolling_group)

  def _check_motion(self, board, motion):
    """Deterimine whether `motion` is legal for this `MazeWalker`.

    Computes whether the single-cell motion in `motion` would be legal for
    this `MazeWalker` to execute. Reasons it might not be legal include: a
    pattern of impassable characters is in the way, or for `MazeWalker`s
    confined to the game board, the edge of the game board may be blocking.

    Args:
      board: a 2-D numpy array with dtype `uint8` containing the completely
          rendered game board from the last board repaint (which usually means
          the last game iteration; see `Engine` docs for details).
      motion: A 2-tuple containing the motion as `(δrow, δcol)`.

    Returns:
      None if the motion is executed successfully; otherwise, a tuple (for
      diagonal motions) or a single-character ASCII string (for motions in
      "cardinal direction") describing the obstruction blocking the
      `MazeWalker`. See class docstring for details.
    """

    def at(coords):
      """Report character at egocentric `(row, col)` coordinates."""
      drow, dcol = coords
      new_row = self._virtual_row + drow
      new_col = self._virtual_col + dcol
      if not self._on_board(new_row, new_col): return self.EDGE
      return chr(board[new_row, new_col])

    def is_impassable(char):
      """Return True if `char` is impassable to this `MazeWalker`."""
      return ((self._confined_to_board and (char is self.EDGE)) or
              (char in self._impassable))

    # Investigate all of the board positions that could keep this MazeWalker
    # from executing the desired motion. Math is hard, so we just hard-code
    # relative positions for each type of permissible motion.
    if motion == self._STAY:
      return None  # Moving nowhere is always fine.
    elif motion == self._NORTHWEST:    # ↖
      neighbs = at(self._WEST), at(self._NORTHWEST), at(self._NORTH)
    elif motion == self._NORTH:        # ↑
      neighbs = at(self._NORTH)
    elif motion == self._NORTHEAST:    # ↗
      neighbs = at(self._NORTH), at(self._NORTHEAST), at(self._EAST)
    elif motion == (self._EAST):       # →
      neighbs = at(self._EAST)
    elif motion == (self._SOUTHEAST):  # ↘
      neighbs = at(self._EAST), at(self._SOUTHEAST), at(self._SOUTH)
    elif motion == (self._SOUTH):      # ↓
      neighbs = at(self._SOUTH)
    elif motion == (self._SOUTHWEST):  # ↙
      neighbs = at(self._SOUTH), at(self._SOUTHWEST), at(self._WEST)
    elif motion == (self._WEST):       # ←
      neighbs = at(self._WEST)
    else:
      assert False, 'illegal motion {}'.format(motion)

    # Determine whether there are impassable obstacles in the neighbours. If
    # there are, return the full array of neighbours.
    if all(motion):  # If the motion is diagonal:
      if is_impassable(neighbs[1]): return neighbs
      if is_impassable(neighbs[0]) and is_impassable(neighbs[2]): return neighbs
    else:  # Otherwise, if the motion is "cardinal":
      if is_impassable(neighbs): return neighbs

    # There are no obstacles; we're free to proceed.
    return None

  def _on_board(self, row, col):
    """Returns True iff `row`, `col` are on the game board."""
    return (0 <= row < self.corner.row) and (0 <= col < self.corner.col)


def _character_check(items, argument_name, function_name):
  """Make sure all elements of `items` are single-character ASCII strings.

  Args:
    items: an iterable of things that should be single-character ASCII strings.
    argument_name: if raising a `TypeError` due to finding an illegal value in
        `items`, a name to give `items` in the exception string.
    function_name: if raising a `TypeError` due to finding an illegal value in
        `items`, a name to give the entity that objects to that value.

  Raises:
    TypeError: if anything that's not a single-character ASCII strings turns up
        in `items`; the exception string will say that `function_name` objects
        to finding such things in `argument_name`.
  """
  for item in items:
    try:
      _ = ord(item)
    except TypeError:
      raise TypeError(
          '{} requires all elements in its {} argument to be single-character '
          'ASCII strings, but {} was found inside {}.'.format(
              function_name, argument_name, repr(item), argument_name))
