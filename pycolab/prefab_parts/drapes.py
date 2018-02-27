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

""""Prefabricated" `Drape`s with all kinds of useful behaviour."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np

from pycolab import ascii_art
from pycolab import things
from pycolab.protocols import scrolling


class Scrolly(things.Drape):
  """A base class for scrolling `Drape`s, which usually implement game scenery.

  *Note: This `Drape` subclass is mostly intended for games that implement
  scrolling by having their game entities participate in the scrolling protocol
  (see `protocols/scrolling.py`). If your game doesn't do any scrolling, or if
  it is a game with a finite map where scrolling is more easily accomplished
  using a `ScrollingCropper` (which just slides a moving window over the
  observations produced by a pycolab game, giving the illusion of scrolling),
  you probably don't need the added complication of using a `Scrolly`.*

  If your game shows a top-down view of a world that can "scroll" around a
  character as the character moves around inside of it (e.g. River Raid) then a
  `Scrolly` is a `Drape` that contains much of the functionality that you need
  to make the scrolling world. When used in tandem with `MazeWalker`-derived
  `Sprite`s, very little code is required to obtain the basic elements of this
  gameplay concept. The discussion in this documentation will therefore use that
  arrangement as an example to help describe how `Scrolly`s work, although other
  configurations are surely possible.

  ## Essential background: the scrolling protocol

  A `Scrolly` figures out whether and where to scroll with the help of messages
  in the game's `Plot` object (see `plot.py`) that are transacted according to
  the scrolling protocol (see `protocols/scrolling.py`).

  `Sprite`s and `Drape`s that participate in the protocol can be either of two
  types: "egocentric" and not egocentric. An egocentric entity is one that
  expects the world to scroll around them whilst they remain stationary relative
  to the game board (i.e. the "screen")---like the player-controlled airplane in
  River Raid. The other kind of entity should move whenever the rest of the
  world does---like River Raid's helicopters, boats, and so on.

  Egocentric entities are of particular concern to `Scrolly`s, since the game
  probably should not scroll the scenery in a way that corresponds to these
  entities making an "impossible" move. In a maze game, for example, a careless
  implementation could accidentally scroll the player into a wall! Fortunately,
  at each game iteration, all egocentric participants in the scrolling protocol
  declare which kinds of scrolling moves will be acceptable ones. As long as a
  `Scrolly` heeds these restrictions, it can avoid a catastrophe.

  ## What a `Scrolly` does

  **A `Scrolly` should be told to move (or to consider moving) in the same way
  as your game's egocentric `Sprite`s.** To help with this, `Scrolly`s have
  "motion action helper methods" that are just like `MazeWalker`s: `_north`,
  `_south`, `_east`, `_west` and so on. You call these in `update`, which you
  must implement.

  In the simplest case, a `Scrolly` will always scroll the world in the
  corresponding motion direction *provided that* all egocentric entities have
  said (via the scrolling protocol) that the motion is OK. If even one of them
  considers that motion unacceptable, no scrolling will occur!

  (Scrolling the world in a particular direction means moving the game board
  over the world in that direction. A scroll to the "north" will move the
  `Scrolly`'s scenery in the same way that "scrolling up" moves the text in your
  web browser.)

  `Scrolly` objects also support a less aggressive scrolling behaviour in which
  egocentric `Sprite`s trigger scrolling only when they get close to the edges
  of the game board.

  ## Update order, and who's in charge of scrolling

  **For best results, `Scrolly` instances in charge of making non-traversible
  game scenery should update before `Sprite`s do, in a separate update group.**

  `Scrolly`s generally expect to be in charge of scrolling, or at least they
  hope to have another `Scrolly` be in charge of it. The `Scrolly`'s "motion
  action helper method" will issue a scrolling order (or not; see above), and
  all of the other pycolab entities in the game will obey it. In order for them
  to even have the chance to obey, it's necessary for the `Scrolly` to issue the
  order before they are updated.

  If the egocentric `Sprite`s are `MazeWalker`s, then the `Scrolly` should
  perform its update in its own update group. This ensures that by the time the
  `MazeWalker`s see it, the world will appear as it does _after_ the scrolling
  takes place. This allows these `Sprite`s to compute and express (via the
  scrolling protocol) which scrolling motions will be "legal" in the future.

  It's fine to have more than one `Scrolly` in a pycolab game. Unless you are
  doing something strange, the first one will be the one to issue scrolling
  orders, and the rest will just follow along blindly.

  ## Loose interpration of "legal" scrolling motions

  *It's probably safe to skip this discussion if your 'Sprite's and 'Drape's
  will only ever move vertically or horizontally, never diagonally.*

  Per the discussion under the same heading in the docstring at
  `protocols/scrolling.py` (a recommended read!), a `Scrolly` can issue a
  scrolling order that was not expressly permitted by the other egocentric
  participants in the scrolling protocol. It can do this as long as it believes
  that at the end of the game iteration, none of those participants will have
  wound up in an illegal location, either due to them following the scrolling
  order by itself *or* due to moving in response to the agent action *after*
  following the scrolling order.

  Naturally, this requires the scrolling-order-issuing `Scrolly` to know how
  these other participating entities will behave. For this, it makes two
  assumptions:

  1. It interprets all of the scrolling motions permitted by the entities (i.e.
     the 2-tuples used as `motion` arguments by `scrolling` module functions)
     as actual motions that those entities could execute within the game world.
  2. It assumes that the way that it interprets agent actions is identical to
     the way that all the other participating egocentric entities interpret
     them. So, if this object's `update` method maps action `0` to the `_north`
     motion action helper method, which connotes an upward motion of one row,
     it assumes that all Sprites will do the same.

  Based on these assumptions, the `Scrolly` will predict where `Sprite`s will go
  in response to agent actions and will direct only the most pleasing (i.e.
  minimal) amount of scrolling required to keep the egocentric `Sprite`s within
  the margins. If there are no egocentric `Sprite`s at all, then all the
  `Sprite`s are by definition inside the margins, and no scrolling will ever
  occur. (If scrolling is still desired, it could be that the behaviour evinced
  by specifying `None` for the constructor's `scroll_margins` parameter will
  produce the intended behavior; refer to the constructor docstring.)
  """

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

  class PatternInfo(object):
    """A helper class that interprets ASCII art scrolling patterns.

    This class exists chiefly to make it easier to build constructor arguments
    for `Scrolly` classes from (potentially large) ASCII art diagrams.
    Additional convenience methods are present which may simplify other aspects
    of game setup.

    As with all the utilities in `ascii_art.py`, an ASCII art diagram is a
    list or tuple of equal-length strings. See docstrings in that file for
    example diagrams.
    """

    def __init__(self, whole_pattern_art, board_art_or_shape,
                 board_northwest_corner_mark, what_lies_beneath):
      """Construct a PatternInfo instance.

      Args:
        whole_pattern_art: an ASCII art diagram depicting a game world. This
            should be a list or tuple whose values are all strings containing
            the same number of ASCII characters.
        board_art_or_shape: either another ASCII art diagram depicting the
            game board itself, or a 2-tuple containing the shape of the board
            (the only thing this object cares about).
        board_northwest_corner_mark: an ASCII character whose sole appearance
            in the `whole_pattern_art` marks the intended initial scrolling
            position of the game board (specifically, its top-left corner) with
            respect to the game world diagram.
        what_lies_beneath: the ASCII character that should replace the
            `board_northwest_corner_mark` in the `whole_pattern_art` when using
            the art to create `Scrolly` constructor arguments.

      Raises:
        ValueError: `what_lies_beneath` was not an ASCII character, or any
            dimension of the game board is larger than the corresponding
            dimension of the game world depicted in `whole_pattern_art`.
        RuntimeError: the `whole_pattern_art` diagram does not contain exactly
            one of the `board_northwest_corner_mark` characters.
      """
      # Verify that what_lies_beneath is ASCII.
      if ord(what_lies_beneath) > 127: raise ValueError(
          'The what_lies_beneath value used to build a Scrolly.PatternInfo '
          'must be an ASCII character.')

      # Convert the pattern art into an array of character strings.
      self._whole_pattern_art = ascii_art.ascii_art_to_uint8_nparray(
          whole_pattern_art)
      self._board_northwest_corner = self._whole_pattern_position(
          board_northwest_corner_mark, 'the Scrolly.PatternInfo constructor')
      self._whole_pattern_art[self._board_northwest_corner] = (
          ord(what_lies_beneath))

      # Determine the shape of the game board. We try two ways---the first way
      # assumes that board_art_or_shape is the game board, the second assumes
      # that it is a 2-tuple with the board shape.
      try:
        self._board_shape = len(board_art_or_shape), len(board_art_or_shape[0])
      except TypeError:
        rows, cols = board_art_or_shape  # Enforce a 2-tuple.
        self._board_shape = (rows, cols)

      if (self._board_shape[0] > self._whole_pattern_art.shape[0] or
          self._board_shape[1] > self._whole_pattern_art.shape[1]):
        raise ValueError(
            'The whole_pattern_art value used to build a Scrolly.PatternInfo '
            '(size {}) cannot completely cover the game board (size '
            '{}).'.format(self._whole_pattern_art.shape, self._board_shape))

    def virtual_position(self, character):
      """Find board-relative position of a character in game world ASCII art.

      The location returned by this method is the "virtual position" of the
      character, that is, a location relative to the game board's (not the game
      world's) top left corner. In contrast to a "true position", a virtual
      position may exceed the bounds of the game board in any direction.

      Args:
        character: the character to search for inside the `whole_pattern_art`
            supplied to the constructor. There must be exactly one of these
            characters inside the game world art.

      Returns:
        A 2-tuple containing the row, column board-relative position of
        `character` in the game world art.

      Raises:
        RuntimeError: the `whole_pattern_art` diagram does not contain exactly
            one of the `board_northwest_corner_mark` characters.
      """
      pattern_position = self._whole_pattern_position(
          character, 'Scrolly.PatternInfo.virtual_position()')
      return (pattern_position[0] - self._board_northwest_corner[0],
              pattern_position[1] - self._board_northwest_corner[1])

    def kwargs(self, character):
      """Build some of the keyword arguments for the `Scrolly` constructor.

      Given a character whose pattern inside the game world ASCII art will be
      the scrollable pattern managed by a `Scrolly`, return a dict which can
      be **expanded into the arguments of the `Scrolly` constructor to provide
      values for its `board_shape`, `whole_pattern`, and
      `board_northwest_corner` arguments.

      Args:
        character: character to use to derive a binary mask from the game world
            ASCII art passed to the constructor. This mask will become the
            scrollable pattern managed by a `Scrolly` instance.

      Returns:
        a partial kwargs dictionary for the `Scrolly` constructor.
      """
      # some (not all) kwargs that you can pass on to Scrolly.__init__.
      return {'board_shape': self._board_shape,
              'whole_pattern': self._whole_pattern_art == ord(character),
              'board_northwest_corner': self._board_northwest_corner}

    def _whole_pattern_position(self, character, error_name):
      """Find the absolute location of `character` in game world ASCII art."""
      pos = list(np.argwhere(self._whole_pattern_art == ord(character)))
      if not pos: raise RuntimeError(
          '{} found no instances of {} in the pattern art used to build this '
          'PatternInfo object.'.format(error_name, repr(character)))
      if len(pos) > 1: raise RuntimeError(
          '{} found multiple instances of {} in the pattern art used to build '
          'this PatternInfo object.'.format(error_name, repr(character)))
      return tuple(pos[0])

  def __init__(self, curtain, character, board_shape,
               whole_pattern, board_northwest_corner,
               scroll_margins=(2, 3), scrolling_group=''):
    """Superclass constructor for `Scrolly`-derived classes.

    `Scrolly` does not define `Drape.update`, so this constructor will fail
    if you attempt to build a `Scrolly` on its own.

    Args:
      curtain: required by `Drape`.
      character: required by `Drape`.
      board_shape: 2-tuple containing the row, column dimensions of the game
          board.
      whole_pattern: a 2-D numpy array with dtype `bool_`, which will be "owned"
          by this `Drape` and made accessible at `self.whole_pattern`.
          Game-board-shaped regions of this array will be used to update this
          `Drape`'s curtain, depending on where the game board has been
          scrolled relative to the pattern.
      board_northwest_corner: a row, column 2-tuple specifying the initial
          scrolling position of the game board relative to the `whole_pattern`.
      scroll_margins: either None, which means that the `Scrolly` should
          scroll whenever all egocentric entities permit it (and as long as it
          hasn't run out of pattern in the scrolling direction), or a 2-tuple
          that controls the `Scrolly`'s "less aggressive" scrolling behaviour
          (see class docstring). In this latter case, the `Scrolly` will only
          attempt to scroll if an egocentric `Sprite` approaches within
          `scroll_margins[0]` rows of the top or bottom of the board, or within
          `scroll_margins[1]` columns of the left or right edges of the board.
          Note that in this case, if there are no egocentric `Sprite`s, no
          scrolling will ever occur!
      scrolling_group: the scrolling group that this `Scrolly` should
          participate in, if not the default (`''`).

    Raises:
      ValueError: any dimension of `board_shape` is larger than the
          corresponding dimension of `whole_pattern`, or either of the margins
          specified in `scroll_margins` so large that it overlaps more than
          half of the game board.
    """
    super(Scrolly, self).__init__(curtain, character)

    # Local copies of certain arguments.
    self._board_shape = board_shape
    self._northwest_corner = board_northwest_corner
    self._scrolling_group = scrolling_group
    # We own this pattern now, and nobody should change our reference to it.
    self._w_h_o_l_e_p_a_t_t_e_r_n = whole_pattern

    # Top-left corner of the board must never exceed these limits.
    self._northwest_corner_limit = (whole_pattern.shape[0] - board_shape[0],
                                    whole_pattern.shape[1] - board_shape[1])
    if any(lim < 0 for lim in self._northwest_corner_limit):
      raise ValueError(
          'The whole_pattern provided to the `Scrolly` constructor (size {}) '
          'cannot completely cover the game board (size {}).'.format(
              whole_pattern.shape, board_shape))

    # If the user has supplied scrolling margins, figure out where they are.
    self._have_margins = scroll_margins is not None
    if self._have_margins:
      # If a visible, egocentric Sprite will move into or beyond any of these
      # bounds, then the Scrolly should scroll those bounds out of the way.
      self._margin_north = scroll_margins[0] - 1
      self._margin_south = board_shape[0] - scroll_margins[0]
      self._margin_west = scroll_margins[1] - 1
      self._margin_east = board_shape[1] - scroll_margins[1]
      if (self._margin_west >= self._margin_east or
          self._margin_north >= self._margin_south):
        raise ValueError(
            'The scrolling margins provided to the `Scrolly` constructor, {}, '
            'are so large that a margin would overlap more than half of the '
            'board.'.format(scroll_margins))

    # Initialise the curtain with the portion of the pattern visible on the
    # game board.
    self._update_curtain()

    # Keep track of the last frame index where which we considered executing a
    # scrolling motion. The pattern_position_* methods use this information to
    # provide consistent information before and after scrolling.
    self._last_maybe_move_frame = -float('inf')
    # Also for the pattern_position_* methods, we save the location of the game
    # board prior to any game iteration's scrolling motion.
    self._prescroll_northwest_corner = self._northwest_corner

  def pattern_position_prescroll(self, virtual_position, the_plot):
    """Get "pattern coordinates" of a pre-scrolling `virtual_position`.

    Most `Sprite`s and other game entities reason about "screen location" in
    game-board-relative coordinates, but some may also need to know their
    "absolute" location---their position with respect to the game scenery. For
    scrolling games that use `Scrolly`s to implement a moving game world, the
    `pattern_position_*` methods provide a way to translate a "virtual position"
    (which is just a game-board-relative position that is allowed to extend
    beyond the game board) to an "absolute" position: to coordinates relative to
    the scrolling pattern managed by this `Scrolly`.

    As the game board's scrolling location can change during a game iteration,
    callers of these methods have to be specific about whether the virtual
    position that they want to translate is a virtual position from before the
    game board moved in the world (i.e. before scrolling) or after. For the
    former, use this method; for the latter, use `pattern_position_postscroll`.

    Args:
      virtual_position: virtual position (as a row, column 2-tuple) to translate
          into (pre-scroll) coordinates relative to this `Scrolly`'s pattern.
      the_plot: this pycolab game's `Plot` object.

    Returns:
      A row, column 2-tuple containing the (pre-scroll) pattern-relative
      translation of `virtual_position` into "absolute" coordinates.
    """
    # This if statement replicates logic from _maybe_move, since this method
    # could be called before _maybe_move does.
    if self._last_maybe_move_frame < the_plot.frame:
      self._prescroll_northwest_corner = self._northwest_corner
    return things.Sprite.Position(
        row=virtual_position[0] + self._prescroll_northwest_corner[0],
        col=virtual_position[1] + self._prescroll_northwest_corner[1])

  def pattern_position_postscroll(self, virtual_position, the_plot):
    """Get "pattern coordinates" of a post-scrolling `virtual_position`.

    The discussion from `pattern_position_prescroll` applies here as well,
    except this method translates `virtual_position` into coordinates relative
    to the pattern after any scrolling has occurred.

    Args:
      virtual_position: virtual position (as a row, column 2-tuple) to translate
          into (post-scroll) coordinates relative to this `Scrolly`'s pattern.
      the_plot: this pycolab game's `Plot` object.

    Returns:
      A row, column 2-tuple containing the (post-scroll) pattern-relative
      translation of `virtual_position` into "absolute" coordinates.

    Raises:
      RuntimeError: this `Scrolly` has not had any of its motion action helper
          methods called in this game iteration, so it hasn't had a chance to
          decide whether and where to scroll yet.
    """
    if self._last_maybe_move_frame < the_plot.frame: raise RuntimeError(
        'The pattern_position_postscroll method was called on a Scrolly '
        'instance before that instance had a chance to decide whether or where '
        'it would scroll.')
    return things.Sprite.Position(
        row=virtual_position[0] + self._northwest_corner[0],
        col=virtual_position[1] + self._northwest_corner[1])

  @property
  def whole_pattern(self):
    """Retrieve the scrolling game world pattern managed by this `Scrolly`."""
    return self._w_h_o_l_e_p_a_t_t_e_r_n

  ### Protected helpers (final, do not override) ###

  def _northwest(self, the_plot):
    """Scroll one row upward and one column leftward, if necessary."""
    return self._maybe_move(the_plot, self._NORTHWEST)

  def _north(self, the_plot):
    """Scroll one row upward, if necessary."""
    return self._maybe_move(the_plot, self._NORTH)

  def _northeast(self, the_plot):
    """Scroll one row upward and one column rightward, if necessary."""
    return self._maybe_move(the_plot, self._NORTHEAST)

  def _east(self, the_plot):
    """Scroll one column rightward, if necessary."""
    return self._maybe_move(the_plot, self._EAST)

  def _southeast(self, the_plot):
    """Scroll one row downward and one column rightward, if necessary."""
    return self._maybe_move(the_plot, self._SOUTHEAST)

  def _south(self, the_plot):
    """Scroll one row downward, if necessary."""
    return self._maybe_move(the_plot, self._SOUTH)

  def _southwest(self, the_plot):
    """Scroll one row downward and one column leftward, if necessary."""
    return self._maybe_move(the_plot, self._SOUTHWEST)

  def _west(self, the_plot):
    """Scroll one column leftward, if necessary."""
    return self._maybe_move(the_plot, self._WEST)

  def _stay(self, the_plot):
    """Remain in place, but apply any other scrolling that may have happened."""
    return self._maybe_move(the_plot, self._STAY)

  ### Private helpers (do not call; final, do not override) ###

  def _maybe_move(self, the_plot, motion):
    """Handle all aspects of single-row and/or single-column scrolling.

    Implements every aspect of deciding whether to scroll one step in any of the
    nine possible gridworld directions (includes staying put). This amounts to:

    1. Checking for scrolling orders from other entities (see
       `protocols/scrolling.py`), and, if present, applying them
       indiscriminately and returning.
    2. Determining whether this `Scrolly` should scroll (e.g. one of the
       sprites is encroaching on the board margins). If not, returning.
    3. Determining whether this `Scrolly` can scroll---that is, it's not
       constrained by egocentric entities, it wouldn't wind up scrolling the
       board off of the pattern, and so on. If not, returning.
    4. Issuing a scrolling order for the scroll, and updating the curtain from
       the pattern.

    Args:
      the_plot: this pycolab game's `Plot` object.
      motion: a 2-tuple indicating the number of rows and columns that the
          game board should move over the pattern if scrolling is both
          appropriate and possible. See class docstring for more details.

    Raises:
      scrolling.Error: another game entity has issued a scrolling order which
          does not have any component in common with `motion`.
    """
    # Save our last board location for pattern_position_prescroll.
    if self._last_maybe_move_frame < the_plot.frame:
      self._last_maybe_move_frame = the_plot.frame
      self._prescroll_northwest_corner = self._northwest_corner

    # First, was a scrolling order already issued by some other entity in this
    # scrolling group? If so, verify that it was the same motion as `motion` in
    # at least one dimension; if it was, apply it without doing any other
    # checking. Otherwise, die.
    scrolling_order = scrolling.get_order(self, the_plot, self._scrolling_group)
    if scrolling_order:
      if motion[0] != scrolling_order[0] and motion[1] != scrolling_order[1]:
        raise scrolling.Error(
            'The Scrolly corresponding to character {} received a fresh '
            'scrolling order, {}, which has no component in common with the'
            'current action-selected motion, which is {}.'.format(
                self.character, scrolling_order, motion))
      self._northwest_corner = things.Sprite.Position(
          row=scrolling_order[0] + self._northwest_corner[0],
          col=scrolling_order[1] + self._northwest_corner[1])
      self._update_curtain()
      return

    # Short-circuit: nothing to do here if instructions say "stay put". But just
    # in case the whole pattern itself has been changed, we update the curtain.
    if motion == self._STAY:
      self._update_curtain()
      return

    # If here, the decision to scroll is ours! The rest of this (long) method
    # is divided into handling the two cases we need to consider:

    #############
    # Case 1: The user made scrolling mandatory (i.e. whenever possible).
    #############

    if not self._have_margins:
      # The main complication in this case has to do with circumstances where
      # only one component of the scrolling motions is possible. The user made
      # scrolling *mandatory*, so we want to scroll as much as we can.

      # The first thing we do is check for the legality of the motion itself.
      # Any scrolling order we issue is issued to accommodate the motion that
      # we expect egocentric entities to take. If they won't all do that motion,
      # there's no good reasson to accommodate it.
      if scrolling.is_possible(self, the_plot, motion, self._scrolling_group):
        # The motion is legal, so now we determine where on the pattern the
        # motion would move the northwest corner of the game board. From this,
        # determine whether and which components of the motion would scroll the
        # game board off of the pattern.
        possible_board_edge_north = self._northwest_corner[0] + motion[0]
        possible_board_edge_west = self._northwest_corner[1] + motion[1]
        can_scroll_vertically = (
            0 <= possible_board_edge_north <= self._northwest_corner_limit[0])
        can_scroll_horizontally = (
            0 <= possible_board_edge_west <= self._northwest_corner_limit[1])

        # The scrolling order that we'll issue and execute will only contain
        # the components of the motion that will *not* scroll the game board
        # off of the pattern. This may mean that we issue a scrolling order that
        # was not expressly by other egocentric game entities. See the "loose
        # interpretation of 'legal' scrolling motions" discussion in the class
        # docstring and elsewhere.
        scrolling_order = (motion[0] if can_scroll_vertically else 0,
                           motion[1] if can_scroll_horizontally else 0)
        self._northwest_corner = things.Sprite.Position(
            row=scrolling_order[0] + self._northwest_corner[0],
            col=scrolling_order[1] + self._northwest_corner[1])
        scrolling.order(self, the_plot, scrolling_order, self._scrolling_group,
                        check_possible=False)

      # Whether we've scrolled or not, update the curtain just in case the whole
      # pattern itself has been changed.
      self._update_curtain()
      return

    #############
    # Case 2: We'll only consider scrolling if one of the visible egocentric
    # sprites will move from the centre region of the board into the margins.
    #############

    action_demands_vertical_scrolling = False
    action_demands_horizontal_scrolling = False

    egocentric_participants = scrolling.egocentric_participants(
        self, the_plot, self._scrolling_group)
    for entity in egocentric_participants:
      # Short-circuit if we already know we're scrolling both ways.
      if (action_demands_vertical_scrolling and
          action_demands_horizontal_scrolling): break

      # See if this entity adds to the axes along which we should scroll because
      # it threatens to enter or move more deeply into a margin. Here we assume
      # that our motion argument is also a motion that this egocentric game
      # entity expects it should attempt to make, relative to the whole world
      # scenery. (This may mean no motion relative to the game board itself,
      # because it's an egocentric entity, after all.)
      if not isinstance(entity, things.Sprite): continue
      burrowing_vertical, burrowing_horizontal = (
          self._sprite_burrows_into_a_margin(entity, motion))
      action_demands_vertical_scrolling |= burrowing_vertical
      action_demands_horizontal_scrolling |= burrowing_horizontal

    # If we don't need to scroll, then we won't do it, and we can stop right
    # here! But just in case the whole pattern itself has been changed, we
    # update the curtain first.
    if not (action_demands_vertical_scrolling or
            action_demands_horizontal_scrolling):
      self._update_curtain()
      return

    # We know we should scroll, now to see what we'd actually do and where we'd
    # wind up (i.e. where the northwest corner of the board would lie on the
    # whole pattern) if we did it. Note here that we might be concocting a
    # scrolling order that may not have been expressly permitted by other
    # egocentric game entities. See the "loose interpretation of 'legal'
    # scrolling motions" discussion in the class docstring and elsewhere.
    scrolling_order = (motion[0] if action_demands_vertical_scrolling else 0,
                       motion[1] if action_demands_horizontal_scrolling else 0)
    possible_northwest_corner = things.Sprite.Position(
        row=scrolling_order[0] + self._northwest_corner[0],
        col=scrolling_order[1] + self._northwest_corner[1])

    # We know we should scroll, now to see whether we can. If we can, do it,
    # and order all other participants in this scrolling group to do it as well.
    we_can_actually_scroll = (
        0 <= possible_northwest_corner[0] <= self._northwest_corner_limit[0])
    we_can_actually_scroll &= (
        0 <= possible_northwest_corner[1] <= self._northwest_corner_limit[1])
    # Note how this test checks for the legality of the *motion*, not the
    # scrolling order itself. This check also lies at the heart of the "loose
    # interpretation of 'legal' scrolling motions" described in the class
    # docstring and elsewhere. The scrolling order we derived just above is
    # meant to accommodate this motion on the part of all of the egocentric
    # entities, but if the motion itself is illegal for them, we won't scroll
    # anywhere at all.
    we_can_actually_scroll &= (
        scrolling.is_possible(self, the_plot, motion, self._scrolling_group))
    if we_can_actually_scroll:
      self._northwest_corner = possible_northwest_corner
      scrolling.order(self, the_plot, scrolling_order, self._scrolling_group,
                      check_possible=False)

    # Whether we've scrolled or not, update the curtain just in case the whole
    # pattern itself has been changed.
    self._update_curtain()

  def _sprite_burrows_into_a_margin(self, sprite, motion):
    """Would `motion` would move `sprite` (deeper) into either margin?

    Args:
      sprite: a `Sprite` instance present in this pycolab game.
      motion: a 2-tuple indicating the number of rows and columns that the
          sprite should add to its current position.

    Returns:
      a 2-tuple whose members are:
      - True iff `sprite` would enter or move deeper into the left or right
        margin.
      - True iff `sprite` would enter or move deeper into the top or bottom
        margin.
    """
    sprite_old_row, sprite_old_col = sprite.position
    sprite_new_row = sprite_old_row + motion[0]
    sprite_new_col = sprite_old_col + motion[1]
    return (
        ((sprite_old_row > sprite_new_row) and  # Moving north into a margin, or
         (sprite_new_row <= self._margin_north)) or
        ((sprite_old_row < sprite_new_row) and  # ...moving south into a margin?
         (sprite_new_row >= self._margin_south)),
        ((sprite_old_col > sprite_new_col) and  # Moving west into a margin, or
         (sprite_new_col <= self._margin_west)) or
        ((sprite_old_col < sprite_new_col) and  # ...moving east into a margin?
         (sprite_new_col >= self._margin_east)))

  def _update_curtain(self):
    """Update this `Scrolly`'s curtain by copying data from the pattern."""
    rows = slice(self._northwest_corner[0],
                 self._northwest_corner[0] + self._board_shape[0])
    cols = slice(self._northwest_corner[1],
                 self._northwest_corner[1] + self._board_shape[1])
    np.copyto(self.curtain, self.whole_pattern[rows, cols])
