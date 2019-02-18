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

"""Tests for the scrolling protocol, Scrolly, and MazeWalker."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import sys
import unittest

from pycolab import ascii_art
from pycolab import plot
from pycolab import things
from pycolab.prefab_parts import drapes as prefab_drapes
from pycolab.protocols import scrolling
from pycolab.tests import test_things as tt

import six


class ScrollingTest(tt.PycolabTestCase):

  def testProtocol(self):
    """Verify correct behaviour of the scrolling protocol helpers."""

    # In this test, we pretend to be an Engine. Here are components we need:
    the_plot = plot.Plot()
    sprite = tt.TestSprite(corner=things.Sprite.Position(11, 10),
                           position=things.Sprite.Position(5, 5),
                           character='P')
    drape = tt.TestDrape(curtain=np.zeros((10, 10), dtype=np.bool),
                         character='X')

    # Registration of scrolling participants, in the default scrolling group.
    scrolling.participate_as_egocentric(sprite, the_plot)
    scrolling.participate_as_egocentric(drape, the_plot)

    self.assertEqual({sprite, drape},
                     set(scrolling.egocentric_participants(sprite, the_plot)))

    # Registration of scrolling participants, in a custom scrolling group.
    the_plot = plot.Plot()  # Use a fresh Plot object.
    scrolling.participate_as_egocentric(sprite, the_plot, scrolling_group='!')
    scrolling.participate_as_egocentric(drape, the_plot, scrolling_group='!')

    self.assertEqual({sprite, drape}, set(scrolling.egocentric_participants(
        sprite, the_plot, scrolling_group='!')))

    # Verify that no scrolling order exists for this scrolling group yet.
    self.assertIsNone(
        scrolling.get_order(sprite, the_plot, scrolling_group='!'))

    # Confirm an exception if an entity requests scrolling information for a
    # scrolling group it doesn't belong to.
    with six.assertRaisesRegex(self, scrolling.Error, 'known to belong'):
      scrolling.get_order(sprite, the_plot, scrolling_group='cantaloupe')

    # Start over with a fresh Plot, and go back to the default scrolling group.
    the_plot = plot.Plot()
    scrolling.participate_as_egocentric(sprite, the_plot)
    scrolling.participate_as_egocentric(drape, the_plot)
    for i in range(101):  # Now let's advance the game a few steps.
      the_plot.frame = i  # There will be an error unless we go one at a time.

    # The Sprite and Drape advertise that they will be able to execute certain
    # sets of motions at the next game iteration.
    scrolling.permit(sprite, the_plot, motions=[(0, 0), (0, 1), (1, 0)])
    scrolling.permit(drape, the_plot, motions=[(0, 0), (1, 1)])

    # But that permission is for the next game iteration. In the current
    # iteration, no scrolling is permitted.
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(0, 0)))
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(0, 1)))
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(1, 0)))
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(1, 1)))

    # Now let's pretend it's the next game iteration and query again. Only the
    # one scrolling direction that's compatible with everyone is permissible.
    the_plot.frame = 101
    self.assertTrue(scrolling.is_possible(drape, the_plot, motion=(0, 0)))
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(0, 1)))
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(1, 0)))
    self.assertFalse(scrolling.is_possible(drape, the_plot, motion=(1, 1)))

    # The Sprite and Drape now advertise where they can scroll at iter. 102.
    scrolling.permit(sprite, the_plot, motions=[(0, 1), (1, 1)])
    scrolling.permit(drape, the_plot, motions=[(0, 0), (1, 0), (1, 1)])

    # We advance to frame 102 and try to have the drape order some scrolling.
    the_plot.frame = 102
    with six.assertRaisesRegex(self, scrolling.Error, 'impossible'):
      scrolling.order(drape, the_plot, motion=(1, 0))  # Illegal for 'P'.
    scrolling.order(drape, the_plot, motion=(1, 1))

    # We confirm that the sprite can receive the order.
    self.assertEqual((1, 1), scrolling.get_order(sprite, the_plot))

  def testScrolly(self):
    """Verify correct interoperation of `Scrolly` and `MazeWalker`."""
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda

    # The test takes place in this scrolling world.
    maze_art = ['########################',
                '#          #       #   #',
                '# # ###### #   ### # # #',
                '# #      #   #   # # # #',
                '######## +#### ### # # #',  # Note top-left corner.
                '# #      #   # #N    # #',  # A non-player character.
                '# # ###### # # #########',
                '#          #P          #',  # The player.
                '# #################### #',
                '#                      #',
                '########################']

    board_art = ['~~~~~',  # The maze art will drape across this board art.
                 '~~~~~',
                 '~~~~~',
                 '~~~~~',
                 '~~~~~']

    # Build and test the helper object that helps us construct a Scrolly object.
    scrolly_info = prefab_drapes.Scrolly.PatternInfo(
        maze_art, board_art,
        board_northwest_corner_mark='+', what_lies_beneath='#')

    self.assertEqual((5, 5), scrolly_info.kwargs('#')['board_shape'])
    self.assertEqual((4, 9), scrolly_info.kwargs('#')['board_northwest_corner'])
    np.testing.assert_array_equal(
        scrolly_info.kwargs('#')['whole_pattern'], np.array(
            [list(row) for row in ['111111111111111111111111',
                                   '100000000001000000010001',
                                   '101011111101000111010101',
                                   '101000000100010001010101',
                                   '111111110111110111010101',
                                   '101000000100010100000101',
                                   '101011111101010111111111',
                                   '100000000001000000000001',
                                   '101111111111111111111101',
                                   '100000000000000000000001',
                                   '111111111111111111111111']]).astype(bool))

    # Here we make the game. In this game, scrolling will only occur if it looks
    # like we are getting to within one pixel of the edge of the game board.
    engine = ascii_art.ascii_art_to_game(
        art=board_art, what_lies_beneath='~',

        # N and P are MazeWalkers, and P is an egocentric scroller.
        sprites=dict(N=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     P=ascii_art.Partial(tt.TestMazeWalker, impassable='#N',
                                         egocentric_scroller=True)),

        # The world itself is a Scrolly drape with narrow margins.
        drapes={'#': ascii_art.Partial(
            tt.TestScrolly, scroll_margins=(1, 1), **scrolly_info.kwargs('#'))},

        # The update schedule is in a separate and later update group from the
        # group containing the pycolab entities that control non-traversable
        # characters (i.e. the wall, '#').
        update_schedule=[['#'], ['N', 'P']])

    # Go ahead and start the game. We will take this opportunity to teleport the
    # two sprites into their proper locations in the scrolling world. This is
    # often something you take care of in your Sprite's constructor, and doing
    # it this way is not encouraged at all.
    tt.pre_update(engine, 'N', thing_to_do=(
        lambda actions, board, layers, backdrop, things, the_plot: (
            things['N']._teleport(scrolly_info.virtual_position('N')))))
    tt.pre_update(engine, 'P', thing_to_do=(
        lambda actions, board, layers, backdrop, things, the_plot: (
            things['P']._teleport(scrolly_info.virtual_position('P')))))
    engine.its_showtime()

    # We will soon want to execute a sequence of motions that the player Sprite
    # P and the moving Scrolly drape # should pay attention to, but the
    # non-player Sprite N should ignore. We can send motion commands just to P
    # and # by using "dict format" actions for TestMazeWalker and TestScrolly.
    go = lambda direction: {'P': direction, '#': direction}

    # Now we execute a sequence of motions, comparing the actual observations
    # against ASCII-art depictions of our expected observations.
    self.assertMachinima(
        engine=engine,
        frames=[
            # Let's start by doing nothing and seeing that the world looks as
            # we expect.
            (None,
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            # Let's try to go in directions that are blocked off and verify that
            # we stay put.
            (go('w'),
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            (go('sw'),
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            (go('s'),
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            # Now let's try to go drive by our friend N.
            (go('e'),
             ['####~',
              '~~~#~',
              '~#~#~',
              '~#~P~',
              '#####']),

            (go('e'),
             ['###~#',
              '~~#~#',
              '#~#~#',
              '#~~P~',
              '#####']),

            (go('e'),
             ['##~##',
              '~#~#N',
              '~#~##',
              '~~~P~',
              '#####']),

            (go('nw'),
             ['##~##',
              '~#~#N',
              '~#P##',
              '~~~~~',
              '#####']),

            (go('n'),
             ['##~##',
              '~#P#N',
              '~#~##',
              '~~~~~',
              '#####']),

            (go('n'),
             ['~#~~~',
              '##P##',
              '~#~#N',
              '~#~##',
              '~~~~~']),

            # And back to our starting place. The 'sw' move in particular is
            # tricky, since it only requires a scroll in one dimension, even
            # though the Sprite is moving in two dimensions at once.
            (go('s'),
             ['~#~~~',
              '##~##',
              '~#P#N',
              '~#~##',
              '~~~~~']),

            (go('s'),
             ['~#~~~',
              '##~##',
              '~#~#N',
              '~#P##',
              '~~~~~']),

            (go('sw'),
             ['##~##',
              '~#~#N',
              '~#~##',
              '~P~~~',
              '#####']),

            (go('w'),
             ['###~#',
              '~~#~#',
              '#~#~#',
              '#P~~~',
              '#####']),

            # Now exercise that same logic again along the horizontal axis (at
            # the "se" move in particular).
            (go('e'),
             ['###~#',
              '~~#~#',
              '#~#~#',
              '#~P~~',
              '#####']),

            (go('ne'),
             ['###~#',
              '~~#~#',
              '#~#P#',
              '#~~~~',
              '#####']),

            (go('se'),
             ['##~##',
              '~#~#N',
              '~#~##',
              '~~~P~',
              '#####']),
        ],
    )

    # Now let's start over with a new game. In this next game, we set no margins
    # at all, so scrolling the world is mandatory at each game iteration.
    engine = ascii_art.ascii_art_to_game(
        art=board_art, what_lies_beneath='~',

        # N and P are MazeWalkers, and P is an egocentric scroller.
        sprites=dict(N=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     P=ascii_art.Partial(tt.TestMazeWalker, impassable='#N',
                                         egocentric_scroller=True)),

        # The world itself is a Scrolly drape with narrow margins.
        drapes={'#': ascii_art.Partial(
            tt.TestScrolly, scroll_margins=None, **scrolly_info.kwargs('#'))},

        # The update schedule is in a separate and later update group from the
        # group containing the pycolab entities that control non-traversable
        # characters (i.e. the wall, '#').
        update_schedule=[['#'], ['N', 'P']])

    # Again we use our start-of-game "teleportation trick", which is not really
    # appropriate for anything but tests, and even then it's pushing it...
    tt.pre_update(engine, 'N', thing_to_do=(
        lambda actions, board, layers, backdrop, things, the_plot: (
            things['N']._teleport(scrolly_info.virtual_position('N')))))
    tt.pre_update(engine, 'P', thing_to_do=(
        lambda actions, board, layers, backdrop, things, the_plot: (
            things['P']._teleport(scrolly_info.virtual_position('P')))))
    engine.its_showtime()

    # Here is a sequence of motions and the observations we expect to see.
    self.assertMachinima(
        engine=engine,
        frames=[
            # Let's start by doing nothing and seeing that the world looks as
            # we expect.
            (None,
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            # As before, let's try to go in directions that are blocked off and
            # verify that we stay put.
            (go('w'),
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            (go('sw'),
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            (go('s'),
             ['#####',
              '#~~~#',
              '#~#~#',
              '~~#P~',
              '#####']),

            # We're going to head for the western edge of the map. First we need
            # to head over this short vertically-oriented wall...
            (go('n'),
             ['#~~~#',
              '#####',
              '#~~~#',
              '#~#P#',
              '~~#~~']),

            (go('nw'),
             ['##~#~',
              '~#~~~',
              '~####',
              '~#~P~',
              '##~#~']),

            (go('sw'),
             ['~~#~~',
              '#~###',
              '~~#~~',
              '###P#',
              '~~~~#']),

            (go('sw'),
             ['##~##',
              '~~~#~',
              '####~',
              '~~~P~',
              '#####']),

            # Now, westward ho! An interesting thing will happen when the
            # scrolling world runs out of scenery---the sprite will actually
            # have to change its location on the game board.
            (go('w'),
             ['###~#',
              '~~~~#',
              '#####',
              '~~~P~',
              '#####']),

            (go('w'),
             ['####~',
              '~~~~~',
              '#####',
              '~~~P~',
              '#####']),

            (go('w'),
             ['#####',
              '~~~~~',
              '~####',
              '~~~P~',
              '#####']),

            (go('w'),
             ['#####',
              '#~~~~',
              '#~###',
              '~~~P~',
              '#####']),

            (go('w'),
             ['#####',
              '~#~~~',
              '~#~##',
              '~~~P~',
              '~####']),

            (go('w'),
             ['#####',
              '#~#~~',
              '#~#~#',
              '#~~P~',
              '#~###']),

            (go('w'),    # Behold: eppur non si muove. The world is stuck, and
             ['#####',   # the Sprite is forced to move around inside if it.
              '#~#~~',
              '#~#~#',
              '#~P~~',
              '#~###']),

            # Now, what happens if we try to go southwest? The board can (and
            # should) scroll vertically to keep the Sprite on the same row, but
            # it still can't scroll horizontally.
            (go('sw'),
             ['#~#~~',
              '#~#~#',
              '#~~~~',
              '#P###',
              '#~~~~']),

            # Now we head up and back east, and then that's about enough. In
            # both of these motions, the world can scroll around the Sprite, so
            # it's back to business as usual.
            (go('ne'),
             ['#####',
              '~#~~~',
              '~#~##',
              '~P~~~',
              '~####']),

            (go('e'),
             ['#####',
              '#~~~~',
              '#~###',
              '~P~~~',
              '#####']),
        ],
    )


def main(argv=()):
  del argv  # Unused.
  unittest.main()


if __name__ == '__main__':
  main(sys.argv)
