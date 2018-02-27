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

"""Tests for pycolab croppers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import unittest

from pycolab import ascii_art
from pycolab import cropping
from pycolab import things as plab_things
from pycolab.tests import test_things as tt


class CroppingTest(tt.PycolabTestCase):

  def make_engine(self, art, croppers):
    """Every test in this class will use game engines made by this helper.

    Characteristics of the returned engine: there is a single MazeWalker called
    'P' which can't pass through walls marked with '#'. There is also a drape
    called '%' which doesn't do anything at all.

    The `its_showtime` method will be called on the new engine.

    Args:
      art: ASCII-art diagram (a list of strings) of the game.
      croppers: List of croppers that will be applied to the obserations created
          by the engine. This function will "reset" these croppers by calling
          their `set_engine` methods with the new engine and by presenting the
          observation returned by the `its_showtime` call to their `crop`
          methods, emulating the behaviour of the `CursesUi`. The outputs of
          the `crop` calls will not be checked.

    Returns:
      a pycolab game engine, as described.
    """

    class DoNothingDrape(plab_things.Drape):
      """Our Drape that does nothing."""

      def update(self, *args, **kwargs):
        pass

    # Create and start the game engine.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath=' ',
        sprites={'P': ascii_art.Partial(tt.TestMazeWalker, impassable='#')},
        drapes={'%': DoNothingDrape})
    observation, reward, pcontinue = engine.its_showtime()
    del reward, pcontinue  # unused

    # "Reset" the croppers.
    for cropper in croppers:
      cropper.set_engine(engine)
      cropper.crop(observation)

    return engine

  def testDefaultCropper(self):
    """The default cropper passes observations through unchanged."""
    # This test also helps check basic cropper functionality in assertMachinima.

    # Our test takes place in this world.
    art = ['.......',
           '.#####.',
           '.#   #.',
           '.# P #.',
           '.#   #.',
           '.#####.',
           '.......']

    # In a fresh engine, execute a (short!) sequence of motions with two None
    # croppers specified. For these, assertMachinima should use the default
    # cropper, cropping.ObservationCropper, which passes observations through.
    # (We cheat a bit on the croppers arg to MakeEngine in this case: there's
    # no need to "reset" the default cropper.)
    self.assertMachinima(
        engine=self.make_engine(art, []),
        croppers=[None, None],
        frames=[
            ('stay',        # After executing this action...
             [['.......',
               '.#####.',   # ...we expect this from the first cropper...
               '.#   #.',
               '.# P #.',
               '.#   #.',
               '.#####.',
               '.......'],

              ['.......',
               '.#####.',   # ...and this from the second cropper.
               '.#   #.',
               '.# P #.',
               '.#   #.',
               '.#####.',
               '.......']]),
        ],
    )

  def testFixedCropper(self):
    """Fixed croppers crop the designated part of the observation."""
    # All cropping in cropping.py uses the same cropping helper method, so
    # with this text and the next one we try to cover a diverse range of
    # cropping situations.

    # Our test takes place in this world.
    art = ['.......',
           '.#####.',
           '.#   #.',
           '.# P #.',
           '.#   #.',
           '.#####.',
           '.......']

    # Build several fixed croppers focusing on different parts of the board. All
    # have the same size, which lets us use zip to make our art easier to read.
    croppers = [
        # These croppers extend beyond all four corners of the game board,
        # allowing us to test the padding functionality.
        cropping.FixedCropper((-1, -1), rows=4, cols=4, pad_char=' '),
        cropping.FixedCropper((-1, 4), rows=4, cols=4, pad_char=' '),
        cropping.FixedCropper((4, -1), rows=4, cols=4, pad_char=' '),
        cropping.FixedCropper((4, 4), rows=4, cols=4, pad_char=' '),
        # This cropper sits right in the middle and requires no padding.
        cropping.FixedCropper((1, 1), rows=4, cols=4),
    ]

    # In a fresh engine, execute some actions and check for expected crops.
    # pylint: disable=bad-whitespace
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('stay',  # The action, and cropped observations below.
             zip(['    ',   '    ',   ' .# ',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#   '],
                 [' .##',   '##. ',   ' ...',   '... ',   '# P '],
                 [' .# ',   ' #. ',   '    ',   '    ',   '#   '])),

            ('nw',
             zip(['    ',   '    ',   ' .# ',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#P  '],
                 [' .##',   '##. ',   ' ...',   '... ',   '#   '],
                 [' .#P',   ' #. ',   '    ',   '    ',   '#   '])),

            ('e',
             zip(['    ',   '    ',   ' .# ',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '# P '],
                 [' .##',   '##. ',   ' ...',   '... ',   '#   '],
                 [' .# ',   ' #. ',   '    ',   '    ',   '#   '])),

            ('e',
             zip(['    ',   '    ',   ' .# ',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#  P'],
                 [' .##',   '##. ',   ' ...',   '... ',   '#   '],
                 [' .# ',   'P#. ',   '    ',   '    ',   '#   '])),

            ('s',
             zip(['    ',   '    ',   ' .# ',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#   '],
                 [' .##',   '##. ',   ' ...',   '... ',   '#  P'],
                 [' .# ',   ' #. ',   '    ',   '    ',   '#   '])),

            ('s',
             zip(['    ',   '    ',   ' .# ',   'P#. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#   '],
                 [' .##',   '##. ',   ' ...',   '... ',   '#   '],
                 [' .# ',   ' #. ',   '    ',   '    ',   '#  P'])),

            ('w',
             zip(['    ',   '    ',   ' .# ',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#   '],
                 [' .##',   '##. ',   ' ...',   '... ',   '#   '],
                 [' .# ',   ' #. ',   '    ',   '    ',   '# P '])),

            ('w',
             zip(['    ',   '    ',   ' .#P',   ' #. ',   '####'],
                 [' ...',   '... ',   ' .##',   '##. ',   '#   '],
                 [' .##',   '##. ',   ' ...',   '... ',   '#   '],
                 [' .# ',   ' #. ',   '    ',   '    ',   '#P  '])),
        ],
    )
    # pylint: enable=bad-whitespace

  def testWeirdFixedCrops(self):
    """Cropping works even for strange cropping sizes and locations."""
    # All cropping in cropping.py uses the same cropping helper method, so
    # with this text and the prior one we try to cover a diverse range of
    # cropping situations.

    # Our test takes place in this world.
    art = ['.......',
           '.#####.',
           '.#P  #.',
           '.#   #.',
           '.#   #.',
           '.#####.',
           '.......']

    # Build several fixed croppers that crop in assorted odd ways.
    croppers = [
        # Extends beyond the original observation on all sides.
        cropping.FixedCropper((-1, -2), rows=9, cols=11, pad_char=' '),
        # A 1x1 crop right on the agent.
        cropping.FixedCropper((2, 2), rows=1, cols=1),
        # A long, short crop right through the agent.
        cropping.FixedCropper((2, -2), rows=1, cols=11, pad_char=' '),
        # A tall, skinny crop right through the agent.
        cropping.FixedCropper((-2, 2), rows=11, cols=1, pad_char=' '),
        # Altogether ouside of the observation.
        cropping.FixedCropper((-4, -4), rows=2, cols=2, pad_char=' '),
        # This, too
        cropping.FixedCropper((14, 14), rows=2, cols=2, pad_char=' '),
    ]

    # In a fresh engine, execute some actions and check for expected crops.
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('stay',            # After executing this action...
             [['           ',
               '  .......  ',   # ...we expect this from the first cropper...
               '  .#####.  ',
               '  .#P  #.  ',
               '  .#   #.  ',
               '  .#   #.  ',
               '  .#####.  ',
               '  .......  ',
               '           '],

              ['P'],            # ...and this from the second cropper...

              ['  .#P  #.  '],  # ...and this from the third...

              [c for c in '  .#P  #.  '],  # ...and this from the fourth...

              ['  ',            # ...fifth...
               '  '],

              ['  ',            # ...and the sixth.
               '  ']]),
        ],
    )

  def testEgocentricScrolling(self):
    """Basic egocentric scrolling works as advertised."""

    # Our test takes place in this world.
    art = ['#######',
           '# . . #',
           '#. . .#',
           '# .P. #',
           '#. . .#',
           '# . . #',
           '#######']

    # We have two types of egocentric croppers. The first is allowed to crop a
    # region outside the board, while the second is not.
    croppers = [
        # We have two types of egocentric croppers. This one is allowed to have
        # its cropping region extend outside of the game board.
        cropping.ScrollingCropper(
            rows=5, cols=5, to_track=['P'],
            scroll_margins=(None, None), pad_char=' '),
        # This one is not allowed to do that.
        cropping.ScrollingCropper(
            rows=5, cols=5, to_track=['P'],
            scroll_margins=(None, None)),
    ]

    # In a fresh engine, walk northwest and check for expected crops.
    # pylint: disable=bad-whitespace
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('nw',  # The action, and cropped observations below.
             zip(['#####',   '#####'],
                 ['# . .',   '# . .'],
                 ['#.P. ',   '#.P. '],
                 ['# . .',   '# . .'],
                 ['#. . ',   '#. . '])),

            ('nw',
             zip(['     ',   '#####'],
                 [' ####',   '#P. .'],
                 [' #P. ',   '#. . '],
                 [' #. .',   '# . .'],
                 [' # . ',   '#. . '])),
        ],
    )
    # pylint: enable=bad-whitespace

    # In a fresh engine, walk southeast and check for expected crops.
    # pylint: disable=bad-whitespace
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('se',
             zip([' . .#',   ' . .#'],
                 ['. . #',   '. . #'],
                 [' .P.#',   ' .P.#'],
                 ['. . #',   '. . #'],
                 ['#####',   '#####'])),

            ('se',
             zip([' . # ',   ' . .#'],
                 ['. .# ',   '. . #'],
                 [' .P# ',   ' . .#'],
                 ['#### ',   '. .P#'],
                 ['     ',   '#####'])),
        ],
    )
    # pylint: enable=bad-whitespace

  def testScrollingSaccade(self):
    """`ScrollingCropper` can "saccade" correctly between scroll targets."""

    # Our test takes place in this world.
    art = [' . . . ',
           '. . . .',
           ' . . . ',
           '. .P. .',  # The agent...
           ' . .%% ',
           '. .%%%.',  # ...and a blobby drape.
           ' . %%. ']

    # We have two kinds of egocentric croppers: one that can saccade between
    # scroll targets (i.e. if its scroll target moves more than one pixel in any
    # direction, it jumps to follow it) and one that does not. In this test, we
    # name two scrolling targets: the highest priority is the Sprite 'P', and
    # the Drape '%' is the lowest priority. Both can crop a region outside of
    # the game board.
    croppers = [
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P', '%'],
            scroll_margins=(None, None), pad_char=' ', saccade=True),
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P', '%'],
            scroll_margins=(None, None), pad_char=' ', saccade=False),
    ]

    # In a fresh engine, walk the Sprite around; we check for expected crops.
    # pylint: disable=bad-whitespace
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            # The first three steps to the west proceed normally.
            ('w',
             zip([' . . ',   ' . . '],
                 ['. P .',   '. P .'],
                 [' . .%',   ' . .%'])),

            ('w',
             zip(['  . .',   '  . .'],
                 [' .P. ',   ' .P. '],
                 ['  . .',   '  . .'])),

            ('w',
             zip(['   . ',   '   . '],    # So far, so normal. We're now at the
                 ['  P .',   '  P .'],    # western edge of the board.
                 ['   . ',   '   . '])),

            # With this step northwest, the Sprite will "leave the board" and
            # become invisible. The cropper that can saccade will jump straight
            # to the second-priority target, while the cropper that can't
            # saccade will wait patiently in place for a scroll target to drift
            # back into the centre of its window.
            ('nw',
             zip([' .%% ',   '   . '],
                 ['.%%%.',   '  . .'],
                 [' %%. ',   '   . '])),

            # Bringing the Sprite back in two rows above the place where it
            # exited will snap the saccading cropper back into place. But it's
            # still too far away for the non-saccading cropper.
            ('ne',
             zip(['   . ',   '   . '],
                 ['  P .',   '  . .'],
                 ['   . ',   '   . '])),

            # But if the Sprite drops one row, it's within one step---scrolling
            # distance---of the place where the non-saccading cropper was
            # waiting. That's close enough for it to "lock on"!
            ('s',
             zip(['  . .',   '  . .'],
                 ['  P. ',   '  P. '],
                 ['  . .',   '  . .'])),
        ],
    )
    # pylint: enable=bad-whitespace

  def testScrollingMargins(self):
    """Scrolling margins work, interacting with board edges as intended."""

    # Our test takes place in this world.
    art = ['.........',
           '. ; ; ; .',
           '.; , , ;.',
           '. , . , .',
           '.; .P. ;.',
           '. , . , .',
           '.; , , ;.',
           '. ; ; ; .',
           '.........']

    # Our six croppers are the Cartesian product of:
    #   margin is on { vertical edges; horizontal edges; both edges }
    # and
    #   the scrolling window { can; cannot } go beyond the edge of the board.
    # And to be clear, "no margin" means egocentric scrolling---in a sense, the
    # tightest possible margins.
    croppers = [
        cropping.ScrollingCropper(  # Margins on vertical edges,
            rows=5, cols=5, to_track=['P'],  # can overlap the board's edge.
            scroll_margins=(None, 1), pad_char=' '),
        cropping.ScrollingCropper(           # cannot overlap the board's edge.
            rows=5, cols=5, to_track=['P'],
            scroll_margins=(None, 1)),

        cropping.ScrollingCropper(  # Margins on horizontal edges,
            rows=5, cols=5, to_track=['P'],  # can overlap the board's edge.
            scroll_margins=(1, None), pad_char=' '),
        cropping.ScrollingCropper(           # cannot overlap the board's edge.
            rows=5, cols=5, to_track=['P'],
            scroll_margins=(1, None)),

        cropping.ScrollingCropper(  # Margins on both edges,
            rows=5, cols=5, to_track=['P'],  # can overlap the board's edge.
            scroll_margins=(1, 1), pad_char=' '),
        cropping.ScrollingCropper(           # cannot overlap the board's edge.
            rows=5, cols=5, to_track=['P'],
            scroll_margins=(1, 1)),
    ]

    # In a fresh engine, walk the Sprite westward and check for expected crops.
    # pylint: disable=bad-whitespace
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('w',
             zip([' , , ',  ' , , ',  '; , ,',  '; , ,',  ' , , ',  ' , , '],
                 [', . ,',  ', . ,',  ' , . ',  ' , . ',  ', . ,',  ', . ,'],
                 [' P . ',  ' P . ',  '; P .',  '; P .',  ' P . ',  ' P . '],
                 [', . ,',  ', . ,',  ' , . ',  ' , . ',  ', . ,',  ', . ,'],
                 [' , , ',  ' , , ',  '; , ,',  '; , ,',  ' , , ',  ' , , '])),

            ('w',
             zip(['; , ,',  '; , ,',  '.; , ',  '.; , ',  '; , ,',  '; , ,'],
                 [' , . ',  ' , . ',  '. , .',  '. , .',  ' , . ',  ' , . '],
                 [';P. .',  ';P. .',  '.;P. ',  '.;P. ',  ';P. .',  ';P. .'],
                 [' , . ',  ' , . ',  '. , .',  '. , .',  ' , . ',  ' , . '],
                 ['; , ,',  '; , ,',  '.; , ',  '.; , ',  '; , ,',  '; , ,'])),

            ('w',
             zip(['.; , ',  '.; , ',  ' .; ,',  '.; , ',  '.; , ',  '.; , '],
                 ['. , .',  '. , .',  ' . , ',  '. , .',  '. , .',  '. , .'],
                 ['.P . ',  '.P . ',  ' .P .',  '.P . ',  '.P . ',  '.P . '],
                 ['. , .',  '. , .',  ' . , ',  '. , .',  '. , .',  '. , .'],
                 ['.; , ',  '.; , ',  ' .; ,',  '.; , ',  '.; , ',  '.; , '])),

            ('w',
             zip([' .; ,',  '.; , ',  '  .; ',  '.; , ',  ' .; ,',  '.; , '],
                 [' . , ',  '. , .',  '  . ,',  '. , .',  ' . , ',  '. , .'],
                 [' P; .',  'P; . ',  '  P; ',  'P; . ',  ' P; .',  'P; . '],
                 [' . , ',  '. , .',  '  . ,',  '. , .',  ' . , ',  '. , .'],
                 [' .; ,',  '.; , ',  '  .; ',  '.; , ',  ' .; ,',  '.; , '])),
        ],
    )

    # In a fresh engine, walk the Sprite eastward and check for expected crops.
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('e',
             zip([' , , ',  ' , , ',  ', , ;',  ', , ;',  ' , , ',  ' , , '],
                 [', . ,',  ', . ,',  ' . , ',  ' . , ',  ', . ,',  ', . ,'],
                 [' . P ',  ' . P ',  '. P ;',  '. P ;',  ' . P ',  ' . P '],
                 [', . ,',  ', . ,',  ' . , ',  ' . , ',  ', . ,',  ', . ,'],
                 [' , , ',  ' , , ',  ', , ;',  ', , ;',  ' , , ',  ' , , '])),

            ('e',
             zip([', , ;',  ', , ;',  ' , ;.',  ' , ;.',  ', , ;',  ', , ;'],
                 [' . , ',  ' . , ',  '. , .',  '. , .',  ' . , ',  ' . , '],
                 ['. .P;',  '. .P;',  ' .P;.',  ' .P;.',  '. .P;',  '. .P;'],
                 [' . , ',  ' . , ',  '. , .',  '. , .',  ' . , ',  ' . , '],
                 [', , ;',  ', , ;',  ' , ;.',  ' , ;.',  ', , ;',  ', , ;'])),

            ('e',
             zip([' , ;.',  ' , ;.',  ', ;. ',  ' , ;.',  ' , ;.',  ' , ;.'],
                 ['. , .',  '. , .',  ' , . ',  '. , .',  '. , .',  '. , .'],
                 [' . P.',  ' . P.',  '. P. ',  ' . P.',  ' . P.',  ' . P.'],
                 ['. , .',  '. , .',  ' , . ',  '. , .',  '. , .',  '. , .'],
                 [' , ;.',  ' , ;.',  ', ;. ',  ' , ;.',  ' , ;.',  ' , ;.'])),

            ('e',
             zip([', ;. ',  ' , ;.',  ' ;.  ',  ' , ;.',  ', ;. ',  ' , ;.'],
                 [' , . ',  '. , .',  ', .  ',  '. , .',  ' , . ',  '. , .'],
                 ['. ;P ',  ' . ;P',  ' ;P  ',  ' . ;P',  '. ;P ',  ' . ;P'],
                 [' , . ',  '. , .',  ', .  ',  '. , .',  ' , . ',  '. , .'],
                 [', ;. ',  ' , ;.',  ' ;.  ',  ' , ;.',  ', ;. ',  ' , ;.'])),
        ],
    )

    # In a fresh engine, walk the Sprite northward and check for expected crops.
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('n',
             zip(['; ; ;',  '; ; ;',  ' , , ',  ' , , ',  ' , , ',  ' , , '],
                 [' , , ',  ' , , ',  ', P ,',  ', P ,',  ', P ,',  ', P ,'],
                 [', P ,',  ', P ,',  ' . . ',  ' . . ',  ' . . ',  ' . . '],
                 [' . . ',  ' . . ',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 [', . ,',  ', . ,',  ' , , ',  ' , , ',  ' , , ',  ' , , '])),

            ('n',
             zip(['.....',  '.....',  '; ; ;',  '; ; ;',  '; ; ;',  '; ; ;'],
                 ['; ; ;',  '; ; ;',  ' ,P, ',  ' ,P, ',  ' ,P, ',  ' ,P, '],
                 [' ,P, ',  ' ,P, ',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 [', . ,',  ', . ,',  ' . . ',  ' . . ',  ' . . ',  ' . . '],
                 [' . . ',  ' . . ',  ', . ,',  ', . ,',  ', . ,',  ', . ,'])),

            ('n',
             zip(['     ',  '.....',  '.....',  '.....',  '.....',  '.....'],
                 ['.....',  '; P ;',  '; P ;',  '; P ;',  '; P ;',  '; P ;'],
                 ['; P ;',  ' , , ',  ' , , ',  ' , , ',  ' , , ',  ' , , '],
                 [' , , ',  ', . ,',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 [', . ,',  ' . . ',  ' . . ',  ' . . ',  ' . . ',  ' . . '])),

            ('n',
             zip(['     ',  '..P..',  '     ',  '..P..',  '     ',  '..P..'],
                 ['     ',  '; ; ;',  '..P..',  '; ; ;',  '..P..',  '; ; ;'],
                 ['..P..',  ' , , ',  '; ; ;',  ' , , ',  '; ; ;',  ' , , '],
                 ['; ; ;',  ', . ,',  ' , , ',  ', . ,',  ' , , ',  ', . ,'],
                 [' , , ',  ' . . ',  ', . ,',  ' . . ',  ', . ,',  ' . . '])),
        ],
    )

    # In a fresh engine, walk the Sprite southward and check for expected crops.
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('s',
             zip([', . ,',  ', . ,',  ' , , ',  ' , , ',  ' , , ',  ' , , '],
                 [' . . ',  ' . . ',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 [', P ,',  ', P ,',  ' . . ',  ' . . ',  ' . . ',  ' . . '],
                 [' , , ',  ' , , ',  ', P ,',  ', P ,',  ', P ,',  ', P ,'],
                 ['; ; ;',  '; ; ;',  ' , , ',  ' , , ',  ' , , ',  ' , , '])),

            ('s',
             zip([' . . ',  ' . . ',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 [', . ,',  ', . ,',  ' . . ',  ' . . ',  ' . . ',  ' . . '],
                 [' ,P, ',  ' ,P, ',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 ['; ; ;',  '; ; ;',  ' ,P, ',  ' ,P, ',  ' ,P, ',  ' ,P, '],
                 ['.....',  '.....',  '; ; ;',  '; ; ;',  '; ; ;',  '; ; ;'])),

            ('s',
             zip([', . ,',  ' . . ',  ' . . ',  ' . . ',  ' . . ',  ' . . '],
                 [' , , ',  ', . ,',  ', . ,',  ', . ,',  ', . ,',  ', . ,'],
                 ['; P ;',  ' , , ',  ' , , ',  ' , , ',  ' , , ',  ' , , '],
                 ['.....',  '; P ;',  '; P ;',  '; P ;',  '; P ;',  '; P ;'],
                 ['     ',  '.....',  '.....',  '.....',  '.....',  '.....'])),

            ('s',
             zip([' , , ',  ' . . ',  ', . ,',  ' . . ',  ', . ,',  ' . . '],
                 ['; ; ;',  ', . ,',  ' , , ',  ', . ,',  ' , , ',  ', . ,'],
                 ['..P..',  ' , , ',  '; ; ;',  ' , , ',  '; ; ;',  ' , , '],
                 ['     ',  '; ; ;',  '..P..',  '; ; ;',  '..P..',  '; ; ;'],
                 ['     ',  '..P..',  '     ',  '..P..',  '     ',  '..P..'])),
        ],
    )
    # pylint: enable=bad-whitespace

  def testScrollingInitialOffset(self):
    """Initial offsets (for dramatic effect) produce expected crops."""

    # Our test takes place in this world.
    art = ['#######',
           '# . . #',
           '#. . .#',
           '# P . #',
           '#. . .#',
           '# . . #',
           '#######']

    # All croppers have options that interact with the initial_offset
    # parameter in various ways.
    croppers = [
        # The first cropper is an easy case. The offset moves the window a
        # little bit, but the tracked agent is still within the scroll margins
        # (or within one row/column of them).
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P'], scroll_margins=(1, 1),
            initial_offset=(0, -1)),
        # The second cropper shifts the window so that the tracked agent is
        # outside the scroll margins---far enough (i.e. beyond one row/column)
        # that the cropper cannot scroll the agent back into the margins.
        # BUT: saccade is True, so the cropper should just shift to put the
        # agent at the centre.
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P'], scroll_margins=(None, None),
            initial_offset=(-1, -2), saccade=True),
        # The third cropper is like the above, but saccade is False. There will
        # be no shifting the agent back to the centre.
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P'], scroll_margins=(None, None),
            initial_offset=(-1, -2), saccade=False),
        # This cropper would like to shift the window so that it overlaps the
        # left edge of the world. Luckily, it specifies a padding character.
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P'], scroll_margins=(1, 1),
            initial_offset=(0, 1), pad_char=' '),
        # This cropper doesn't, so the window will be confined to the board.
        cropping.ScrollingCropper(
            rows=3, cols=5, to_track=['P'], scroll_margins=(1, 1),
            initial_offset=(0, 1)),
    ]

    # In a fresh engine, execute a "stay" move and check for expected crops.
    # pylint: disable=bad-whitespace
    self.assertMachinima(
        engine=self.make_engine(art, croppers),
        croppers=croppers,
        frames=[
            ('stay',
             zip(['. . .',  '#. . ',  'P . #',  ' #. .',  '#. . '],
                 [' P . ',  '# P .',  ' . .#',  ' # P ',  '# P .'],
                 ['. . .',  '#. . ',  '. . #',  ' #. .',  '#. . ']))
        ],
    )
    # pylint: enable=bad-whitespace


def main(argv=()):
  del argv  # Unused.
  unittest.main()


if __name__ == '__main__':
  main(sys.argv)
