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

"""pycolab game board cropping (and a useful way to scroll)."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy

import numpy as np

from pycolab import rendering

import six


class ObservationCropper(object):
  """Crop an `Observation` to a subwindow.

  This class is a superclass for mechanisms that derive "subwindow"
  `Observation`s from the `Observation`s that emerge from the game engine.
  Cropping is a straightforward way to achieve things like scrolling,
  partially-observable games on finite maps.

  Subclasses of `ObservationCropper` must implement the `crop` method and the
  `rows` and `cols` properties. The default implementation in this class simply
  leaves the observation unmodified, "cropping" the entire window.

  The basic usage instructions for `ObservationCropper`s are:

  1. Construct `ObservationCropper` instance(s).
  2. Prepare a pycolab game engine.
  3. Pass the engine to `set_engine()` method of each `ObservationCropper`
     instance.
  4. Use the engine's `its_showtime()` and `play()` methods as usual, passing
     all returned observations to the `crop()` method of each
     `ObservationCropper` to obtain cropped observations.

  Some pycolab infrastructure, like the `CursesUi`, takes care of some of these
  steps automatically.
  """

  def __init__(self):
    self._set_engine_root_impl(None)

  def set_engine(self, engine):
    """Inform the `ObservationCropper` where observations are coming from.

    `ObservationCropper` objects may outlive the games they are applied to.
    Whether they do or not, they are allowed access to `Engine` objects in
    order to determine how and where to crop observations. This method tells
    an `ObservationCropper` which game engine creates the observations being
    passed to its `crop` method.

    Subclasses may include certain kinds of error checking in overrides of this
    method; check their own docstrings to see what they care about.

    For implementers: in general, all overrides of this method should call this
    superclass method, and for best results should change no state (like
    performing an internal reset) if the `engine` argument is the same as
    `self._engine`.

    Args:
      engine: the pycolab game engine that will generate the next observation
          passed to `crop`, and all following observations until the next time
          `set_engine` is called.
    """
    self._set_engine_root_impl(engine)

  def crop(self, observation):
    """Crop the observation.

    Args:
      observation: observation to crop, a `rendering.Observation`.

    Returns:
      a cropped `rendering.Observation`.
    """
    return observation

  @property
  def rows(self):
    """The height of the subwindow."""
    return self._engine.rows

  @property
  def cols(self):
    """The width of the subwindow."""
    return self._engine.cols

  ### Private helpers ###

  def _set_engine_root_impl(self, engine):
    # This method is the core of what set_engine does, but it's also helpful for
    # the constructor, so we keep it outside of set_engine so that __init__ can
    # call it without worrying about overrides.
    self._engine = engine
    # Padding characters known to be OK for the current game engine.
    self._valid_pad_chars = set(
        [] if self._engine is None else
        list(self._engine.things) + list(self._engine.backdrop.palette))
    # Pre-allocated observation, for speed.
    self._cropped = None

  def _do_crop(self, observation,
               top_row, left_col, bottom_row_exclusive, right_col_exclusive,
               pad_char=None):
    """Helper for `ObservationCropper` subclasses: crop an observation.

    `ObservationCropper` may not do any cropping, but its subclasses might. If
    so, this helper can do the actual work: given an observation and the bounds
    of a rectangle, it computes a view of the observation cropped by that
    rectangle. The rectangle may extend beyond the bounds of the observation, in
    which case the character in `pad_char` will fill spaces in the overhang.
    `pad_char` must be one of the characters associated with the game's
    `Sprite`s, `Drape`s, or `Backdrop`.

    For speed, the cropped observation is computed by manipulating the
    instance variable `self._cropped`; thus, this method is not thread-safe.
    One workaround for applications that need thread safety would be to call
    `_do_crop` under a lock, then copy its result before releasing the lock.

    Args:
      observation: `Observation` to crop.
      top_row: Top row of the cropping window (inclusive).
      left_col: Left column of the cropping window (inclusive).
      bottom_row_exclusive: Bottom row of the cropping window (exclusive).
      right_col_exclusive: Right column of the cropping window (exclusive).
      pad_char: ASCII fill character to use when the cropping window extends
          beyond the bounds of `observation`, or None if the cropping window
          should always remain in bounds (in which case a `RuntimeError` is
          raised if it does not).

    Returns:
      an observation cropped as described. You must copy this observation if
      you need it to last longer than the next call to `_do_crop`.

    Raises:
      ValueError: `pad_char` is not a character used by `Sprite`s, `Drape`s, or
          the `Backdrop` in the current game engine.
      RuntimeError: the cropping window extends beyond the bounds of
          `observation`, and `pad_char` was None.
    """
    crop_rows = bottom_row_exclusive - top_row
    crop_cols = right_col_exclusive - left_col
    obs_rows, obs_cols = observation.board.shape

    ### 1. Prepare the observation that recevies the crop. ###

    # See whether we need to allocate a new cropped observation. This is a
    # superficial check; it doesn't detect rare cases where the types of
    # characters in an observation have changed. We have a backup plan for that,
    # though; look for the KeyError exception handler below.
    if (self._cropped is None or
        self._cropped.board.shape != (crop_rows, crop_cols) or
        len(self._cropped.layers) != len(observation.layers)):
      self._cropped = rendering.Observation(
          board=np.zeros((crop_rows, crop_cols), dtype=observation.board.dtype),
          layers={c: np.zeros((crop_rows, crop_cols), dtype=bool)
                  for c in observation.layers})

    if self._pad_char is None:
      # If there is no padding, verify that the cropping window does not extend
      # outside of the observation.
      if (top_row < 0 or left_col < 0 or
          bottom_row_exclusive > obs_rows or right_col_exclusive > obs_cols):
        raise RuntimeError(
            'An ObservationCropper attempted to crop a region that extends '
            'beyond the observation without specifying a character to fill the '
            'void that exists out there.')
    else:
      # Otherwise, pre-fill the observation with the padding character.
      if self._pad_char not in self._valid_pad_chars: raise ValueError(
          'An `ObservationCropper` tried to fill empty space with a character '
          'that isn\'t used by the current game engine.')
      self._cropped.board.fill(ord(self._pad_char))
      for char, layer in six.iteritems(self._cropped.layers):
        layer.fill(self._pad_char == char)

    ### 2. Compute the slices of data that we will copy. ###

    # Figure out the portion of the observation covered by the cropping window.
    from_tr = max(0, top_row)
    from_lc = max(0, left_col)
    from_bre = max(0, min(obs_rows, bottom_row_exclusive))
    from_rce = max(0, min(obs_cols, right_col_exclusive))
    from_slice = np.s_[from_tr:from_bre, from_lc:from_rce]

    # Figure out where that portion will be placed in the cropped observation.
    to_tr = max(0, -top_row)
    to_lc = max(0, -left_col)
    to_bre = min(crop_rows, max(0, obs_rows - top_row))
    to_rce = min(crop_cols, max(0, obs_cols - left_col))
    to_slice = np.s_[to_tr:to_bre, to_lc:to_rce]

    ### 3. Attempt to copy the data into the cropped observation. ###

    self._cropped.board[to_slice] = observation.board[from_slice]
    # It's here in the copy where we might discover that we need to allocate a
    # new cropped observation after all---it happens when a layer we'd like to
    # copy turns out not to exist in the observation. We abandon the
    # pre-allocated observation and start all over again. Fairly inefficient,
    # but it should happen only very rarely.
    try:
      for char, layer in six.iteritems(self._cropped.layers):
        layer[to_slice] = observation.layers[char][from_slice]
    except KeyError:
      self._cropped = None
      return self._do_crop(
          observation,
          top_row, left_col, bottom_row_exclusive, right_col_exclusive,
          pad_char)

    return self._cropped


class FixedCropper(ObservationCropper):
  """A cropper that cuts a fixed subwindow from an `Observation`."""

  def __init__(self, top_left_corner, rows, cols, pad_char=None):
    """Initialise a `FixedCropper`.

    A `FixedCropper` crops out a fixed subwindow of the observation.

    Args:
      top_left_corner: Cropping window top-left `(row, column)` (inclusive).
      rows: Height of the cropping window.
      cols: Width of the cropping window.
      pad_char: ASCII fill character to use when the cropping window extends
          beyond the bounds of `observation`, or None if the cropping window
          will always remain in bounds (in which case a `RuntimeError` is
          raised if it does not).
    """
    super(FixedCropper, self).__init__()
    self._top_row, self._left_col = top_left_corner
    self._rows = rows
    self._cols = cols
    self._pad_char = pad_char
    self._bottom_row_exclusive = self._top_row + self._rows
    self._right_col_exclusive = self._left_col + self._cols

  def crop(self, observation):
    return self._do_crop(
        observation,
        self._top_row, self._left_col,
        self._bottom_row_exclusive, self._right_col_exclusive,
        self._pad_char)

  @property
  def rows(self):
    return self._rows

  @property
  def cols(self):
    return self._cols


class ScrollingCropper(ObservationCropper):
  """A cropper that scrolls to track moving game entities."""

  def __init__(self, rows, cols, to_track, pad_char=None,
               scroll_margins=(2, 3), initial_offset=None, saccade=True):
    """Initialise a `ScrollingCropper`.

    A `ScrollingCropper` does its best to slide fixed-size cropping windows
    around the game board in a way that keeps one of several designated
    `Sprite`s or `Drape`s in view. The resulting observation appears to
    pan around the game board, tracking one of the game's entities.

    Args:
      rows: number of rows in the scrolling window.
      cols: number of columns in the scrolling window.
      to_track: a list of ASCII characters indicating, in order, which `Sprite`
          or `Drape` to track about the game board. If the `ScrollingCropper`
          can't derive a location for `to_track[0]` (e.g. because it's a
          `Sprite` that made itself invisible, or a `Drape` with an empty
          curtain), then it attempts to find a location for `to_track[1]`, and
          so on. (If it can't find a location for any trackable entity, the
          `ScrollingCropper` will remain in its current location.) If you think
          you'll have lots of game entities that alternate between being visible
          and invisible, it may be useful to read the documentation for the last
          three arguments.
      pad_char: either None to indicate that no part of the scrolling window
          should extend beyond the game board, or an ASCII character to fill the
          out-of-bounds part of the scrolling window if it does. The character
          must be one that is already used by the `Backdrop` or one of the
          `Sprite`s or `Drape`s. If None, the need to retain the window on the
          board will override any other scrolling constraint.
      scroll_margins: a 2-tuple `(r, c)`. `ScrollingCropper` will attempt to
          keep tracked `Sprite`s and `Drape`s no fewer than `r` rows
          (`c` columns) away from the edge of the scrolling window. If `r` (`c`)
          is None, `ScrollingCropper` will try to scroll so that the tracked
          entity is in the very centre row (column); in this case, though, the
          `rows` (`cols`) argument must be odd. (Finally... if `initial_offset`
          would initialise a window so that the tracked entity is outside of the
          bounds implied by `scroll margins`, well, you find yourself in a bit
          of a flowchart situation:
             * If the entity is just one row or column outside of bounds, then
               the `ScrollingCropper` will just scroll smoothly so that the
               entity is back in bounds.
             * Otherwise, if the entity is even further out of bounds:
               - If `saccade` is True, the `ScrollingCropper` will "jump" so
                 that the entity is centred.
               - Otherwise, the entity will just have to wander back inside the
                 bounds for scrolling to begin.)
      initial_offset: if None; the `ScrollingCropper` will initialise
          scrolling windows so that tracked entities are right in the middle;
          otherwise, a 2-tuple `(dr, dc)` that shifts the entity `dr` rows
          downward and `dc` columns rightward at the very first frame of the
          game. (Do see note about this at `scroll_margins`.)
      saccade: if True, then if the current trackable entity is ever outside of
          the bounds implied by `scroll_margins`, the scrolling window will
          "jump" so that the entity is centred. Note that this could lead to
          very jumpy behaviour if entities mentioned in `to_track` frequently
          appear and disappear or change size. Also, see note on interactions
          with `initial_offset` and `scroll_margins` in the documentation for
          `scroll_margins`.

    Raises:
      ValueError: some input arguments are misconfigured; scroll margins
          touch or overlap each other in the middle of the window or a None
          scroll margin is specified for an even-sized dimension.
    """
    super(ScrollingCropper, self).__init__()
    self._rows = rows
    self._cols = cols
    self._to_track = copy.copy(to_track)
    self._pad_char = pad_char

    if ((scroll_margins[0] is None and (rows % 2 == 0)) or
        (scroll_margins[1] is None and (cols % 2 == 0))):
      raise ValueError(
          'A ScrollingCropper can\'t perform perfectly-egocentric scrolling '
          'with a window that has an even number of rows or columns. Either '
          'specify looser scroll margins or use a window with odd dimensions.')
    scroll_margins = (
        (rows // 2) if scroll_margins[0] is None else scroll_margins[0],
        (cols // 2) if scroll_margins[1] is None else scroll_margins[1])

    if (2 * scroll_margins[0]) >= rows or (2 * scroll_margins[1]) >= cols:
      raise ValueError(
          'A ScrollingCropper can\'t use scroll margins which extend to or '
          'beyond the very centre of the scrolling window. (Note that if you '
          'haven\'t specified scroll margins and your window is very small or '
          'thin, the default scroll_margins argument might be too big!)')
    self._scroll_margins = scroll_margins

    self._initial_offset = (
        initial_offset if initial_offset is not None else (0, 0))
    self._saccade = saccade
    # The location of the top-left corner of the scrolling window is
    # uninitialised at first.
    self._corner = None

  def set_engine(self, engine):
    """Overrides `set_engine` to do checks and an internal reset.

    Args:
      engine: see `ObservationCropper.set_engine`.

    Raises:
      ValueError: the engine's board is smaller than the scrolling window, and
          no pad character was specified to the constructor.
    """
    prior_engine = self._engine  # So we can test whether to reset, below.
    super(ScrollingCropper, self).set_engine(engine)
    # If we're actually switching the engine whose observations we're cropping,
    # do an internal reset.
    if engine is not prior_engine:
      if ((self._engine.rows < self._rows or self._engine.cols < self._cols)
          and self._pad_char is None): raise ValueError(
              'A ScrollingCropper with a size of {} and no pad character '
              'can\'t be used with a pycolab engine that produces smaller '
              'observations in any dimension (in this case, {})'.format(
                  (self._rows, self._cols),
                  (self._engine.rows, self._engine.cols)))
      # Force crop to reinitialise the window.
      self._corner = None

  def crop(self, observation):
    # Identify the location we should track.
    centroid = self._centroid_to_track()

    # Compute the new location of the scrolling window.
    # First, if there is no window yet, place it for the first time.
    if self._corner is None:
      init_row, init_col = self._initial_offset
      self._initialise(centroid, (self._rows // 2 + init_row,
                                  self._cols // 2 + init_col))

    # Otherwise, if there's something to track, update the window's location.
    elif centroid is not None:
      # The trackable thing is visible inside the window (or just outside if
      # we have a 0 margin). Smoothly pan if needed to keep it in view.
      if self._can_pan_to(centroid):
        self._pan_to(centroid)

      # The trackable thing is well outside of the window! If we're allowed to
      # jump over to where it is, do so, and centre the trackable thing in the
      # window if possible.
      elif self._saccade:
        self._initialise(centroid, (self._rows // 2, self._cols // 2))

      # Otherwise do no update at all. Wait for a trackable thing to wander back
      # into the window so that we can start tracking it again.

    # Crop out the scrolling window.
    tlr, tlc = self._corner  # pylint: disable=unpacking-non-sequence
    return self._do_crop(
        observation,
        tlr, tlc,
        tlr + self._rows, tlc + self._cols,
        self._pad_char)

  @property
  def rows(self):
    return self._rows

  @property
  def cols(self):
    return self._cols

  ### Private helpers ###

  def _initialise(self, centroid, offset):
    """Set the top-left corner of the scrolling window for the first time.

    Args:
      centroid: centroid of an item to track in the scrolling window, offset
          from the top-left corner by `offset`. If None, the window will be
          placed at the top-left corner of the game board.
      offset: a 2-tuple `(r, c)`; if centroid is not None, then the contents
          of the scrolling window will be shifted `r` rows downward and `c`
          rows rightward.
    """
    if centroid is None:
      self._corner = (0, 0)
      return

    # We have a centroid. The top-left corner of the scrolling window is
    # displaced from it by the initial scrolling offset.
    self._corner = (centroid[0] - offset[0], centroid[1] - offset[1])

    # Keep the window inside the observation, if necessary.
    if self._pad_char is None: self._rectify()

  def _can_pan_to(self, centroid):
    """Determine whether the scrolling window can smoothly pan to `centroid`.

    A scrolling window can smoothly pan to `centroid` if `centroid` is either
    within the margin-padded region inset within the window, or one row/column
    outside of that region. Note that "can pan" doesn't mean "needs to pan";
    even a perfectly-centred centroid makes `_can_pan_to` return True. Also,
    there are some relaxations of this requirement if the window is butting
    up against (and not allowed to extend outside of) the game board.

    Args:
      centroid: a (row, column) tuple.

    Returns:
      True iff the scrolling window can smoothly pan to `centroid`.
    """
    # pylint: disable=unpacking-non-sequence
    crow, ccol = centroid              # C as in Centroid.
    wrow, wcol = self._corner          # W as in Window.
    mrow, mcol = self._scroll_margins  # M as in Margins.
    # pylint: enable=unpacking-non-sequence

    # Check whether we can pan vertically. We first test the typical case,
    # where the window is not bumping up against the edge of the game board.
    can_vert = (mrow - 1) <= (crow - wrow) <= (self._rows - mrow)

    # Check whether we can pan horzontally. We test the typical case here, too.
    can_horiz = (mcol - 1) <= (ccol - wcol) <= (self._cols - mcol)

    # Can't pan normally? Maybe we can work out an excuse having to do with the
    # window being up against an edge of the game board.
    if self._pad_char is None:
      # Can't scroll vertically?
      if not can_vert:
        if wrow <= 0:  # See if we're stuck on the top.
          can_vert = crow <= mrow
        elif wrow >= (self._engine.rows - self._rows):  # Or on the bottom.
          can_vert = crow >= (wrow + self._rows - mrow)

      # Can't scroll horizontally?
      elif not can_horiz:  # Don't bother if we can't pan vertically...
        if wcol <= 0:  # See if we're stuck on the left.
          can_horiz = ccol <= mcol
        elif wcol >= (self._engine.cols - self._cols):  # Or on the right.
          can_horiz = ccol >= (wcol + self._cols - mcol)

    return can_vert and can_horiz

  def _pan_to(self, centroid):
    """Smoothly pan the scrolling window to cover `centroid`.

    Shifts the location of the scrolling window the minimum distance required
    in order for `centroid` to be inside the margin-padded region inset within
    the window.

    Args:
      centroid: a (row, column) tuple.
    """
    # pylint: disable=unpacking-non-sequence
    crow, ccol = centroid              # C as in Centroid.
    wrow, wcol = self._corner          # W as in Window.
    mrow, mcol = self._scroll_margins  # M as in Margins.
    # pylint: enable=unpacking-non-sequence

    # For panning the scrolling window up or leftward, if necessary.
    drow = min(0, crow - wrow - mrow)
    dcol = min(0, ccol - wcol - mcol)

    # For panning the scrolling window down or rightward, if necessary.
    if drow == 0: drow += max(0, crow - wrow - self._rows + mrow + 1)
    if dcol == 0: dcol += max(0, ccol - wcol - self._cols + mcol + 1)

    # Apply the pan, but keep the window inside the game board if necessary.
    self._corner = (wrow + drow, wcol + dcol)
    if self._pad_char is None: self._rectify()

  def _rectify(self):
    """Force the scrolling window to remain inside the observation."""
    # This method assumes that the game board is larger than the window.
    tlr, tlc = self._corner  # pylint: disable=unpacking-non-sequence
    tlr = max(0, tlr) - max(0, tlr + self._rows - self._engine.rows)
    tlc = max(0, tlc) - max(0, tlc + self._cols - self._engine.cols)
    self._corner = (tlr, tlc)

  def _centroid_to_track(self):
    """Obtain the central location of the game entity we should track.

    This method tries to derive centroids for game entities in the priority
    ordering specified by the `to_track` constructor argument.

    Returns:
      either a 2-tuple `(row, col)` centroid to track, or None if the method
      could find no trackable centroid.
    """
    # We search in the priority ordering specified by self._to_track.
    for entity in self._to_track:
      centroid = self._centroid(entity)
      if centroid is not None: return centroid
    return None  # Can't find a centroid for anything we want to track!

  def _centroid(self, entity):
    """Obtain the central location of a `Sprite` or `Drape`.

    This method works by inspecting `Sprite`s and `Drape`s within the game
    engine and not via analysing observations.

    Args:
      entity: ASCII character designating the game entity whose centroid we
          should attempt to find.

    Returns:
      either a 2-tuple `(row, col)` centroid for `entity`, or None if the game
      entity has no centroid (if a sprite, it's not visible; if a drape, the
      drape's entire curtain is False).

    Raises:
      RuntimeError: `entity` corresponds to no game entity.
    """
    # Obtain the item we're trying to track.
    try:
      sprite_or_drape = self._engine.things[entity]
    except KeyError:
      raise RuntimeError(
          'ScrollingCropper was told to track a nonexistent game entity '
          '{!r}.'.format(entity))

    # Hope it's a Sprite and try to get its position. An invisible sprite has
    # no position at all.
    try:
      if not sprite_or_drape.visible: return None
      return tuple(sprite_or_drape.position)
    except AttributeError:
      pass

    # If here, it's a Drape, not a Sprite. Compute the centroid of its
    # curtain and return that. An empty Drape has no centroid.
    curtain = sprite_or_drape.curtain
    if not curtain.any(): return None
    return tuple(int(np.median(dim)) for dim in curtain.nonzero())
