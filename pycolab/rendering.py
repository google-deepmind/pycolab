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

"""pycolab game board rendering for both humans and machines."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import numpy as np
import six


class Observation(collections.namedtuple('Observation', ['board', 'layers'])):
  """A container for pycolab observations.

  Natively, the pycolab engine renders observations as one of these objects
  (although code in this module and others may help you change them to something
  more palatable to you). There are two properties:

  * `board`: a 2-D numpy array of type uint8. This is, in a sense, an ASCII-art
     diagram, and when a `BaseObservationRenderer` creates an `Observation`, the
     values are the actual ASCII character values that are arranged on different
     parts of the game board by the `Backdrop` and the `Sprite`s and `Drape`s.

  * `layers`: a dict mapping every ASCII character that could possibly appear on
    a game board (that is, according to the configuration of the `Engine`) to
    binary mask numpy arrays. If the `Engine` was constructed with
    `occlusion_in_layers=True`, the mask for a character shows only where that
    character appears in `board`; otherwise, the mask shows all locations where
    the `Backdrop` or the corresponding `Sprite` or `Drape` place that
    character, even if some of those locations are covered by other game
    entities that appear later in the Z-order. It is not uncommon for some masks
    in `layers` to be empty (i.e. all False).

  Here is a quick one-liner for visualising a board (and in python 2.7, you
  don't even need the `.decode('ascii')` part):

      for row in observation.board: print(row.tostring().decode('ascii'))

  Important note 1: the values in this object should be accessed in a
  *read-only* manner exclusively.

  Important note 2: the `ObservationRenderer` makes no guarantees about whether
  the contents of an `Observation` obtained for game iteration `t` will remain
  unchanged in any game iteration `t' > t`.

  If you want to save old information, or you want to scribble on what's here,
  you had better make your own copy.
  """
  __slots__ = ()


class BaseObservationRenderer(object):
  """Renderer of "base" pycolab observations.

  This class renders the most basic form of pycolab observations, which are
  described in some detail in the docstring for `Observation`. Every `Engine`
  will create its observations with an instance of this class.

  A `BaseObservationRenderer` is a stateful object that might be imagined like
  a canvas. Rendering an observation proceeds in the following pattern:

  1. Clear the canvas with the `clear()` method.
  2. Paint `Backdrop`, `Sprite`, and `Drape` data onto the canvas via the
     `paint*` methods, from back to front according to the z-order (`Backdrop`
     first, of course).
  3. Call the `render()` method to obtain the finished observation.
  """

  def __init__(self, rows, cols, characters):
    """Construct a BaseObservationRenderer.

    Args:
      rows: height of the game board.
      cols: width of the game board.
      characters: an iterable of ASCII characters that are allowed to appear
          on the game board. (A string will work as an argument here.)
    """
    self._board = np.zeros((rows, cols), dtype=np.uint8)
    self._layers = {
        char: np.zeros((rows, cols), dtype=np.bool_) for char in characters}

  def clear(self):
    """Reset the "canvas" of this `BaseObservationRenderer`.

    After a `clear()`, a call to `render()` would return an `Observation` whose
    `board` contains only `np.uint8(0)` values and whose layers contain only
    `np.bool_(False)` values.
    """
    self._board.fill(0)

  def paint_all_of(self, curtain):
    """Copy a pattern onto the "canvas" of this `BaseObservationRenderer`.

    Copies all of the characters from `curtain` onto this object's canvas,
    overwriting any data underneath. This method is the usual means by which
    `Backdrop` data is added to an observation.

    Args:
      curtain: a 2-D `np.uint8` array whose dimensions are the same as this
          `BaseObservationRenderer`'s.
    """
    np.copyto(self._board, curtain, casting='no')

  def paint_sprite(self, character, position):
    """Draw a character onto the "canvas" of this `BaseObservationRenderer`.

    Draws `character` at row, column location `position` of this object's
    canvas, overwriting any data underneath. This is the usual means by which
    a `Sprite` is added to an observation.

    Args:
      character: a string of length 1 containing an ASCII character.
      position: a length-2 indexable whose values are the row and column where
          `character` should be drawn on the canvas.

    Raises:
      ValueError: `character` is not a valid character for this game, according
          to the `Engine`'s configuration.
    """
    if character not in self._layers:
      raise ValueError('character {} does not seem to be a valid character for '
                       'this game'.format(str(character)))
    self._board[tuple(position)] = ord(character)

  def paint_drape(self, character, curtain):
    """Fill a masked area on the "canvas" of this `BaseObservationRenderer`.

    Places `character` into all non-False locations in the binary mask
    `curtain`, overwriting any data underneath. This is the usual means by which
    a `Drape` is added to an observation.

    Args:
      character: a string of length 1 containing an ASCII character.
      curtain: a 2-D `np.bool_` array whose dimensions are the same as this
          `BaseObservationRenderer`s.

    Raises:
      ValueError: `character` is not a valid character for this game, according
          to the `Engine`'s configuration.
    """
    if character not in self._layers:
      raise ValueError('character {} does not seem to be a valid character for '
                       'this game'.format(str(character)))
    self._board[curtain] = ord(character)

  def render(self):
    """Derive an `Observation` from this `BaseObservationRenderer`'s "canvas".

    Reminders: the values in the returned `Observation` should be accessed in
    a *read-only* manner exclusively; furthermore, if any
    `BaseObservationRenderer` method is called after `render()`, the contents
    of the `Observation` returned in that `render()` call are *undefined*
    (i.e. not guaranteed to be anything---they could be blank, random garbage,
    whatever).

    Returns:
      An `Observation` whose data members are derived from the information
      presented to this `BaseObservationRenderer` since the last call to its
      `clear()` method.
    """
    for character, layer in six.iteritems(self._layers):
      np.equal(self._board, ord(character), out=layer)
    return Observation(board=self._board, layers=self._layers)

  @property
  def shape(self):
    """The 2-D dimensions of this `BaseObservationRenderer`."""
    return self._board.shape


class BaseUnoccludedObservationRenderer(object):
  """Renderer of "base" pycolab observations.

  Similar to `BaseObservationRenderer` except that multiple layers can have
  a `True` value at any given position. This is different from
  `BaseObservationRenderer` where layers with lower z-ordering can get occluded
  by higher layers.
  """

  def __init__(self, rows, cols, characters):
    """Construct a BaseUnoccludedObservationRenderer.

    Args:
      rows: height of the game board.
      cols: width of the game board.
      characters: an iterable of ASCII characters that are allowed to appear
          on the game board. (A string will work as an argument here.)
    """
    self._board = np.zeros((rows, cols), dtype=np.uint8)
    self._layers = {
        char: np.zeros((rows, cols), dtype=np.bool_) for char in characters}

  def clear(self):
    """Reset the "canvas" of this renderer.

    After a `clear()`, a call to `render()` would return an `Observation` whose
    `board` contains only `np.uint8(0)` values and whose layers contain only
    `np.bool_(False)` values.
    """
    self._board.fill(0)
    for layer in six.itervalues(self._layers):
      layer.fill(False)

  def paint_all_of(self, curtain):
    """Copy a pattern onto the "canvas" of this renderer.

    Copies all of the characters from `curtain` onto this object's canvas.
    This method is the usual means by which `Backdrop` data is added to an
    observation.

    Args:
      curtain: a 2-D `np.uint8` array whose dimensions are the same as this
          renderer's.
    """
    np.copyto(self._board, curtain, casting='no')
    for character, layer in six.iteritems(self._layers):
      np.equal(curtain, ord(character), out=layer)

  def paint_sprite(self, character, position):
    """Draw a character onto the "canvas" of this renderer.

    Draws `character` at row, column location `position` of this object's
    canvas. This is the usual means by which a `Sprite` is added to an
    observation.

    Args:
      character: a string of length 1 containing an ASCII character.
      position: a length-2 indexable whose values are the row and column where
          `character` should be drawn on the canvas.

    Raises:
      ValueError: `character` is not a valid character for this game, according
          to the `Engine`'s configuration.
    """
    if character not in self._layers:
      raise ValueError('character {} does not seem to be a valid character for '
                       'this game'.format(str(character)))
    position = tuple(position)
    self._board[position] = ord(character)
    self._layers[character][position] = True

  def paint_drape(self, character, curtain):
    """Fill a masked area on the "canvas" of this renderer.

    Places `character` into all non-False locations in the binary mask
    `curtain`. This is the usual means by which a `Drape` is added to an
    observation.

    Args:
      character: a string of length 1 containing an ASCII character.
      curtain: a 2-D `np.bool_` array whose dimensions are the same as this
          renderer's.

    Raises:
      ValueError: `character` is not a valid character for this game, according
          to the `Engine`'s configuration.
    """
    if character not in self._layers:
      raise ValueError('character {} does not seem to be a valid character for '
                       'this game'.format(str(character)))
    self._board[curtain] = ord(character)
    np.copyto(self._layers[character], curtain)

  def render(self):
    """Derive an `Observation` from this renderer's "canvas".

    Reminders: the values in the returned `Observation` should be accessed in
    a *read-only* manner exclusively; furthermore, if any renderer method is
    called after `render()`, the contents of the `Observation` returned in that
    `render()` call are *undefined* (i.e. not guaranteed to be anything---they
    could be blank, random garbage, whatever).

    Returns:
      An `Observation` whose data members are derived from the information
      presented to this renderer since the last call to its `clear()` method.
      The `board` is a numpy array where characters overlapping is resolved by
      picking the one with the highest z-ordering. The `layers` show all
      characters, whether or not they have been occluded in the `board`.
    """
    return Observation(board=self._board, layers=self._layers)

  @property
  def shape(self):
    """The 2-D dimensions of this renderer."""
    return self._board.shape


class ObservationCharacterRepainter(object):
  """Repaint an `Observation` with a different set of characters.

  An `Observation` made by `BaseObservationRenderer` will draw each `Sprite`
  and `Drape` with a different character, which itself must be different from
  the characters used by the `Backdrop`. This restriction may not be desirable
  for all games, so this class allows you to create a new `Observation` that
  maps the characters in the original observation to a different character set.
  This mapping need not be one-to-one.
  """

  def __init__(self, character_mapping):
    """Construct an `ObservationCharacterRepainter`.

    Builds a callable that will take `Observation`s and emit new `Observation`s
    whose characters are the characters of the original `Observation` mapped
    through `character_mapping`.

    It's not necessary for `character_mapping` to include entries for all of
    the characters that might appear on a game board---those not listed here
    will be passed through unchanged.

    Args:
      character_mapping: A dict mapping characters (as single-character ASCII
          strings) that might appear in original `Observation`s passed to
          `__call__` to the characters that should be used in `Observation`s
          returned by `__call__`. Do not change this dict after supplying it
          to this constructor.
    """
    # Preserve a local reference to the character mapping.
    self._character_mapping = character_mapping

    # We will use an ObservationToArray object to perform the repainting, which
    # means we will need a mapping where (a) values are numerical ASCII
    # codepoints instead of characters, and (b) we supply identity mappings for
    # all ASCII characters not in character_mapping.
    value_mapping = {chr(x): np.uint8(x) for x in range(128)}
    value_mapping.update(
        {k: np.uint8(ord(v)) for k, v in six.iteritems(character_mapping)})

    # With that, we construct the infrastructure that can repaint the characters
    # used in the observation board.
    self._board_converter = ObservationToArray(value_mapping)

    # This member will hold all of the characters that can appear in the
    # Observations output by this repainter, but we will need to see at least
    # one Observation to know what they are.
    self._output_characters = None

    # This member has the same semantics as its `BaseObservationRenderer`
    # counterpart, but will be constructed lazily, i.e. as soon as we have an
    # Observation to convert.
    self._layers = None

  def __call__(self, original_observation):
    """Applies character remapping to `original_observation`.

    Returns a new `Observation` whose contents are the `original_observation`
    after the character remapping passed to the constructor have been applied
    to all of its characters.

    Note: the values in the returned `Observation` should be accessed in
    a *read-only* manner exclusively; furthermore, if this method is called
    again, the contents of the `Observation` returned in the first call to
    this method are *undefined* (i.e. not guaranteed to be anything---they could
    be blank, random garbage, whatever).

    Args:
      original_observation: an `Observation` from which this method derives a
          a new post-character-mapping `Observation.

    Returns:
      an `Observation` with the character remapping applied, as described.

    Raises:
      RuntimeError: `original_observation` contains a value that is not in the
          character mapping passed to the constructor.
    """
    # If necessary, compute the set of characters that appears in our output.
    if self._output_characters is None:
      self._output_characters = (
          set(original_observation.layers) -
          set(self._character_mapping)).union(self._character_mapping.values())

    # Determine whether we need to (re)allocate the layer storage for this new
    # (possibly differently-shaped) observation. If we do, do it.
    if ((self._layers is None) or
        (next(six.itervalues(self._layers)).shape !=
         original_observation.board.shape)):
      rows, cols = original_observation.board.shape
      self._layers = {char: np.zeros((rows, cols), dtype=np.bool_)
                      for char in self._output_characters}

    # Perform the repaint of the board. If a character not in the character
    # mapping turns up in the original observation, a RuntimeError will obtain.
    board = self._board_converter(original_observation)

    # Compute the mask layers from the newly repainted board.
    for character, layer in six.iteritems(self._layers):
      np.equal(board, ord(character), out=layer)

    # Return the new observation.
    return Observation(board=board, layers=self._layers)


class ObservationToArray(object):
  """Convert an `Observation` to a 2-D or 3-D numpy array.

  This class is a general utility for converting `Observation`s into 2-D or
  3-D numpy arrays. Specific uses of this class include converting
  `Observation`s into RGB images, or "repainting" the characters used in an
  `Observation`'s `board` property into new characters. (This class is used by
  `ObservationCharacterRepainter`, which specifically supports that particular
  application.)
  """

  def __init__(self, value_mapping, dtype=None, permute=None):
    """Construct an `ObservationToArray`.

    Builds a callable that will take `Observation`s and emit a 2-D or 3-D numpy
    array, whose rows and columns contain the values obtained after mapping the
    characters of the original `Observation` through `value_mapping`.

    Args:
      value_mapping: a dict mapping any characters that might appear in the
          original `Observation`s to a scalar or 1-D vector value. All values
          in this dict must be the same type and dimension. Note that strings
          are considered 1-D vectors, not scalar values.
      dtype: numpy dtype for the arrays created by this object. If unspecifed,
          this class will attempt to infer a type from the values of
          value_mapping.
      permute: If not None, a tuple specifying an ordering of the integers
          0 and 1 (if `value_mapping` holds scalars) or 0, 1, and 2 (if
          `value_mapping` holds 1-D vectors). In the first case, returned 2-D
          arrays will have their dimensions permuted so that the row and column
          dimensions (corresponding to the integers 0 and 1 respectively) will
          be ordered to match the ordering of the corresponding integers in the
          tuple. In the second case (3-D arrays), 0, 1, and 2 specify the
          ordering of the "vector", row, and column dimensions respectively.
          *The "right ordering" for our convnet libraries is `(1, 2, 0)`.*

    Raises:
      ValueError: if the `permute` argument isn't a list or tuple containing
          0 and 1 (for 2-D outputs) or 0, 1, and 2 (for 3-D outputs).
    """
    self._value_mapping = value_mapping

    # This array will be constructed lazily, i.e. as soon as we have an
    # Observation to convert. Note that within this object, the array is
    # always 3-D; for 2-D arrays, its first dimension has size 1.
    self._array = None

    # Attempt to infer a dtype for self._array if none is specified.
    self._dtype = (dtype if dtype is not None else
                   np.array(next(six.itervalues(value_mapping))).dtype)

    # Will we create a 2-D or a 3-D array? Only 3-D if the values in the mapping
    # can be an argument to `len()`; if so, that's also the depth of our
    # 3-D array.
    try:
      self._depth = len(next(six.itervalues(value_mapping)))
      self._is_3d = True
    except TypeError:
      self._depth = 1  # Again, the array is always 3-D behind the scenes.
      self._is_3d = False

    # Save and check the permute argument.
    self._permute = tuple(permute) if permute is not None else None
    if permute is not None:
      if self._is_3d and set(permute) != {0, 1, 2}:
        raise ValueError('When the value mapping contains 1-D vectors, the '
                         'permute argument to the ObservationToArray '
                         'constructor must be a list or tuple containing some '
                         'permutation of the integers 0, 1, and 2.')
      elif not self._is_3d and set(permute) != {0, 1}:
        raise ValueError('When the value mapping contains scalars, the permute '
                         'argument to the ObservationToArray constructor must '
                         'be a list or tuple containing some permutation of '
                         'the integers 0 and 1.')

  def __call__(self, observation):
    """Derives an array from an `Observation`.

    Returns a 2-D or 3-D array whose values at each row, column coordinate come
    from applying the value mapping supplied to the constructor to
    `observation`.

    Note: the returned array should be accessed in a *read-only* manner
    exclusively; furthermore, if this method is called again, the contents of
    the array returned in any prior call to this method are *undefined* (i.e.
    not guaranteed to be anything---could be blank, random garbage, whatever).

    Args:
      observation: an `Observation` from which this method derives a
          numpy array.

    Returns:
      a numpy array derived from `observation` as described.

    Raises:
      RuntimeError: `observation` contains a value that is not in the value
          mapping passed to the constructor.
    """
    # Determine whether we need to (re)allocate the array for this new
    # (possibly differently-shaped) observation. If we do, do it.
    if ((self._array is None) or
        (self._array.shape[1:] != observation.board.shape)):
      rows, cols = observation.board.shape
      self._array = np.zeros((self._depth, rows, cols), dtype=self._dtype)

    # Paint the array with mapped values for all of the characters in the
    # observation. If a character not in the value mapping turns up in the
    # original observation, raise a RuntimeError.
    ascii_vals = np.unique(observation.board)
    for ascii_value in ascii_vals:
      try:
        value = self._value_mapping[chr(ascii_value)]
      except KeyError:
        raise RuntimeError(
            'This ObservationToArray only knows array values for the '
            'characters {}, but it received an observation with a character '
            'not in that set'.format(str(''.join(self._value_mapping.keys()))))
      mask = observation.board == ascii_value

      # I was hoping there would be an easier way to do this masking in the
      # full-3D case, but this is the best I have for now.
      if self._is_3d:
        for layer, value_component in enumerate(value):
          self._array[layer, mask] = value_component
      else:
        self._array[:, mask] = value

    # Permute (if specified) and return the new array; note special handling in
    # the 2-D mapping case.
    result = self._array if self._is_3d else self._array[0]
    if self._permute is None:
      return result
    else:
      return np.transpose(result, self._permute)


class ObservationToFeatureArray(object):
  """Convert an `Observation` to a 3-D feature array.

  This class provides a faster implementation of a common observation-to-array
  operation: deriving a binary 3-D feature array from the observation's layers.
  For example, if an `Observation`'s `layers` member is this dict (where `#`
  represents `True` and a space represents `False`:

      ⎧                                                         ⎫
      ⎪       ⎡ ## # ##⎤         ⎡   # #  ⎤         ⎡        ⎤  ⎪
      ⎨  'a': ⎢  ## ## ⎥    'b': ⎢ #     #⎥    'c': ⎢    #   ⎥  ⎬
      ⎪       ⎣        ⎦,        ⎣ #######⎦,        ⎣        ⎦  ⎪
      ⎩                                                         ⎭,

  then an `ObservationToFeatureArray` built with `'bc'` as its `layers` argument
  will convert the `Observation` into a 3-D `float32` array `result` such that
  `result[0,:,:]` is the dict's `b` entry (cast to 0.0 and 1.0 values), and
  `result[1,:,:]` is the dict's 'c' entry.

  If the `layers` argument includes a character that isn't an entry in the
  `Observation`'s `layers` dict, then the corresponding layer of `result` will
  be set to 0.0 throughout.

  There is an additional option to permute the dimensions of the returned array,
  which may be desirable for producing feature arrays that are friendlier to
  convolutional networks or other operations.
  """

  def __init__(self, layers, permute=None):
    """Construct an `ObservationToFeatureArray`.

    Builds a callable that performs the conversion described in the class
    docstring.

    Args:
      layers: An iterable of ASCII characters (a string will do) corresponding
          to entries in the game's `Observation`'s `layer` dicts. Layers in the
          returned 3-D arrays will be arranged in the order specified by this
          iterable. (See the class docstring for a note about characters that
          don't match any entry in the `layer` dicts.)
      permute: If not None, a tuple specifying an ordering of the integers 0, 1,
          and 2. Returned 3-D arrays will have their dimensions permuted so that
          the feature, row, and column dimensions (corresponding to the integers
          0, 1, and 2 respectively) will be ordered to match the ordering of the
          corresponding integers in the tuple. *The "right ordering" for our
          convnet libraries is `(1, 2, 0)`.*

    Raises:
      ValueError: if the `permute` argument isn't a list or tuple containing
          0, 1, and 2.
    """
    self._layers = layers
    self._depth = len(layers)
    self._permute = tuple(permute) if permute is not None else None

    # Check the permute argument.
    if permute is not None and sorted(permute) != [0, 1, 2]:
      raise ValueError('The permute argument to the ObservationToFeatureArray '
                       'constructor must be a list or tuple containing some '
                       'permutation of the integers 0, 1, and 2.')

    # This array will be constructed lazily, i.e. as soon as we have an
    # Observation to convert.
    self._array = None

  def __call__(self, observation):
    """Derives an array from an `Observation`.

    Returns a 3-D `float32` array whose 2-D submatrices, indexed by the major
    index, are the float-cast binary layers of the `Observation` corresponding
    to respective entries in the `layers` constructor argument.

    Note: the returned array should be accessed in a *read-only* manner
    exclusively; furthermore, if this method is called again, the contents of
    the array returned in any prior call to this method are *undefined* (i.e.
    not guaranteed to be anything---could be blank, random garbage, whatever).

    Args:
      observation: an `Observation` from which this method derives a
          numpy array.

    Returns:
      a numpy array derived from `observation` as described.

    Raises:
      RuntimeError: the `layers` constructor argument contains no entries that
          are present in the `layers` member of `observation`.
    """
    # Raise a runtime error if none of the observation will make it into the
    # final distilled feature array.
    if not any(l in observation.layers for l in self._layers):
      raise RuntimeError(
          'The layers argument to this ObservationToFeatureArray, {}, has no '
          'entry that refers to an actual feature in the input observation. '
          'Actual features in the observation are {}.'.format(
              repr(self._layers), repr(''.join(sorted(observation.layers)))))

    # Determine whether we need to (re)allocate the array for this new
    # (possibly differently-shaped) observation. If we do, do it.
    if ((self._array is None) or
        (self._array.shape[1:] != observation.board.shape)):
      rows, cols = observation.board.shape
      self._array = np.zeros((self._depth, rows, cols), dtype=np.float32)

    # Paint the array with the contents of selected layers in the observation.
    # If the game has no layer corresponding to one of the elements of the
    # `layers` argument passed to the constructor, fill that layer with zeros.
    for index, character in enumerate(self._layers):
      try:
        np.copyto(self._array[index], observation.layers[character])
      except KeyError:
        self._array[index] = 0.0

    if self._permute is None:
      return self._array
    else:
      return np.transpose(self._array, self._permute)
