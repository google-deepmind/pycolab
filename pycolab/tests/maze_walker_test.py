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

"""Basic tests of the `MazeWalker` `Sprite`, without scrolling."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import unittest

from pycolab import ascii_art
from pycolab.prefab_parts import sprites as prefab_sprites
from pycolab.tests import test_things as tt


class MazeWalkerTest(tt.PycolabTestCase):

  def testBasicWalking(self):
    """A `MazeWalker` can walk, but not through walls."""
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda

    # Our test takes place in this world...
    art = ['.......',
           '..abcd.',
           '.n   e.',
           '.m P f.',
           '.l   g.',
           '.kjih..',
           '.......']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath=' ',

        # Only P is a Sprite, and it can't walk through any of the walls.
        sprites=dict(P=ascii_art.Partial(tt.TestMazeWalker,
                                         impassable='abcdefghijklmn')))

    # Go ahead and start the game. Nothing should change on the game board;
    # P will stay put.
    engine.its_showtime()

    # Now we execute a sequence of motions, comparing the actual observations
    # against ASCII-art depictions of our expected observations, and also making
    # certain that the MazeWalker's motion action helper methods produce the
    # expected return values (None when a motion succeeds; a description of the
    # obstacle when a motion fails).
    self.assertMachinima(
        engine=engine,
        post_updates=dict(
            # This post-update callable for the Sprite is what checks the return
            # value for correctness.
            P=lambda actions, board, layers, backdrop, things, the_plot: (
                self.assertEqual(the_plot['walk_result_P'],
                                 the_plot['machinima_args'][0]))),
        frames=[
            # Head to the top of the room and try to walk through the wall.
            ('n',                 # After going in this direction...
             ['.......',
              '..abcd.',
              '.n P e.',          # ...we expect to see this board...
              '.m   f.',
              '.l   g.',
              '.kjih..',          # ...and this return value from the motion
              '.......'], None),  # action helper methods.

            ('n',
             ['.......',
              '..abcd.',
              '.n P e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], 'b'),

            ('nw',
             ['.......',
              '..abcd.',
              '.n P e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], (' ', 'a', 'b')),

            ('ne',
             ['.......',
              '..abcd.',
              '.n P e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], ('b', 'c', ' ')),

            # Head to the top right corner of the room and try to escape.
            ('e',
             ['.......',
              '..abcd.',
              '.n  Pe.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('e',
             ['.......',
              '..abcd.',
              '.n  Pe.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], 'e'),

            ('nw',
             ['.......',
              '..abcd.',
              '.n  Pe.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], (' ', 'b', 'c')),

            ('ne',
             ['.......',
              '..abcd.',
              '.n  Pe.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], ('c', 'd', 'e')),

            ('se',
             ['.......',
              '..abcd.',
              '.n  Pe.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], ('e', 'f', ' ')),

            # Head to the bottom right corner of the room and try to escape.
            ('s',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m  Pf.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('s',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.l  Pg.',
              '.kjih..',
              '.......'], None),

            ('s',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.l  Pg.',
              '.kjih..',
              '.......'], 'h'),

            ('ne',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.l  Pg.',
              '.kjih..',
              '.......'], (' ', 'f', 'g')),

            ('se',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.l  Pg.',
              '.kjih..',
              '.......'], ('g', '.', 'h')),

            ('sw',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.l  Pg.',
              '.kjih..',
              '.......'], ('h', 'i', ' ')),

            # Head to the bottom left corner of the room and try to escape.
            ('w',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.l P g.',
              '.kjih..',
              '.......'], None),

            ('w',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.lP  g.',
              '.kjih..',
              '.......'], None),

            ('w',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.lP  g.',
              '.kjih..',
              '.......'], 'l'),

            ('se',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.lP  g.',
              '.kjih..',
              '.......'], (' ', 'i', 'j')),

            ('sw',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.lP  g.',
              '.kjih..',
              '.......'], ('j', 'k', 'l')),

            ('nw',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m   f.',
              '.lP  g.',
              '.kjih..',
              '.......'], ('l', 'm', ' ')),

            # Head to the top left corner of the room and try to escape.
            ('n',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.mP  f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('n',
             ['.......',
              '..abcd.',
              '.nP  e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('n',
             ['.......',
              '..abcd.',
              '.nP  e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], 'a'),

            ('sw',
             ['.......',
              '..abcd.',
              '.nP  e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], (' ', 'm', 'n')),

            ('nw',
             ['.......',
              '..abcd.',
              '.nP  e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], ('n', '.', 'a')),

            ('ne',
             ['.......',
              '..abcd.',
              '.nP  e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], ('a', 'b', ' ')),

            # Make certain that diagonal moves work (so far, they've only been
            # tried in situations where they fail).
            ('se',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m P f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('ne',
             ['.......',
              '..abcd.',
              '.n  Pe.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('sw',
             ['.......',
              '..abcd.',
              '.n   e.',
              '.m P f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),

            ('nw',
             ['.......',
              '..abcd.',
              '.nP  e.',
              '.m   f.',
              '.l   g.',
              '.kjih..',
              '.......'], None),
        ],
    )

  def testNotConfinedToBoard(self):
    """An ordinary MazeWalker disappears if it walks off the board."""

    # Our test takes place in this world...
    art = ['     ',
           '  P  ',
           '     ']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath=' ',

        # P is a MazeWalker.
        sprites=dict(P=ascii_art.Partial(tt.TestMazeWalker, impassable='')))

    # Go ahead and start the game. Nothing should change on the game board;
    # P will stay put.
    engine.its_showtime()

    # Now we execute a sequence of motions, comparing the actual observations
    # against ASCII-art depictions of our expected observations, and also making
    # sure that the MazeWalker's true position and virtual position change in
    # the expected ways. First we define a post-update callable that the Sprite
    # uses to check its true and virtual positions against expectations...
    def check_positions(actions, board, layers, backdrop, things, the_plot):
      del actions, board, layers, backdrop  # Unused.
      self.assertEqual(the_plot['machinima_args'][0],
                       things['P'].position)
      self.assertEqual(the_plot['machinima_args'][1],
                       things['P'].virtual_position)

    # ...and then we execute the sequence.
    self.assertMachinima(
        engine=engine,
        post_updates=dict(P=check_positions),
        frames=[
            ('n',       # After going in this direction...
             ['  P  ',  # ...we expect to see this board,...
              '     ',  # ... ↙ this true position, and...
              '     '], (0, 2), (0, 2)),  # ... ← this virtual position.

            # Exit the board to the north. True position becomes 0, 0 and the
            # Sprite goes invisible there; virtual position carries on as if the
            # board extended infinitely in all directions. So, we walk around
            # outside of the board for a bit...
            ('n',
             ['     ',
              '     ',
              '     '], (0, 0), (-1, 2)),

            ('e',
             ['     ',
              '     ',
              '     '], (0, 0), (-1, 3)),

            ('e',
             ['     ',
              '     ',
              '     '], (0, 0), (-1, 4)),

            # ...and then back onto the board...
            ('sw',
             ['   P ',
              '     ',
              '     '], (0, 3), (0, 3)),

            ('sw',
             ['     ',
              '  P  ',
              '     '], (1, 2), (1, 2)),

            ('sw',
             ['     ',
              '     ',
              ' P   '], (2, 1), (2, 1)),

            # ...and off the board again...
            ('sw',
             ['     ',
              '     ',
              '     '], (0, 0), (3, 0)),

            ('nw',
             ['     ',
              '     ',
              '     '], (0, 0), (2, -1)),

            # ...and we're back again!
            ('e',
             ['     ',
              '     ',
              'P    '], (2, 0), (2, 0)),

            ('e',
             ['     ',
              '     ',
              ' P   '], (2, 1), (2, 1)),

            ('e',
             ['     ',
              '     ',
              '  P  '], (2, 2), (2, 2)),
        ],
    )

  def testConfinedToBoard(self):
    """A confined-to-board MazeWalker can't walk off the board."""
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda

    # Our test takes place in this world...
    art = ['     ',
           '  P  ',
           '     ']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath=' ',

        # P is a MazeWalker, but this time it's confined to the board.
        sprites=dict(P=ascii_art.Partial(tt.TestMazeWalker, impassable='',
                                         confined_to_board=True)))

    # Go ahead and start the game. Nothing should change on the game board;
    # P will stay put.
    engine.its_showtime()

    # We'll abbreviate the symbol that MazeWalkers use to describe the edge of
    # the board in motion action helper method return values.
    EDGE = prefab_sprites.MazeWalker.EDGE  # pylint: disable=invalid-name

    # Now we execute a sequence of motions, comparing the actual observations
    # against ASCII-art depictions of our expected observations, and also making
    # certain that the MazeWalker's motion action helper methods produce the
    # expected return values (None when a motion succeeds; a description of the
    # obstacle when a motion fails).
    self.assertMachinima(
        engine=engine,
        post_updates=dict(
            # This post-update callable for the Sprite is what checks the return
            # value for correctness.
            P=lambda actions, board, layers, backdrop, things, the_plot: (
                self.assertEqual(the_plot['walk_result_P'],
                                 the_plot['machinima_args'][0]))),
        frames=[
            ('n',       # After going in this direction...
             ['  P  ',  # ...we expect to see this board and this...
              '     ',  # ... ↙ return value from motion action helper methods.
              '     '], None),

            # Try to escape the board to the north, northwest, and northeast.
            ('n',
             ['  P  ',
              '     ',
              '     '], EDGE),

            ('nw',
             ['  P  ',
              '     ',
              '     '], (' ', EDGE, EDGE)),

            ('ne',
             ['  P  ',
              '     ',
              '     '], (EDGE, EDGE, ' ')),

            # Bolt for the southwest corner.
            ('sw',
             ['     ',
              ' P   ',
              '     '], None),

            ('sw',
             ['     ',
              '     ',
              'P    '], None),

            ('sw',
             ['     ',
              '     ',
              'P    '], (EDGE, EDGE, EDGE)),

            # Try the southeast corner.
            ('e',
             ['     ',
              '     ',
              ' P   '], None),

            ('e',
             ['     ',
              '     ',
              '  P  '], None),

            ('e',
             ['     ',
              '     ',
              '   P '], None),

            ('e',
             ['     ',
              '     ',
              '    P'], None),

            ('se',
             ['     ',
              '     ',
              '    P'], (EDGE, EDGE, EDGE)),
        ],
    )


def main(argv=()):
  del argv  # Unused.
  unittest.main()


if __name__ == '__main__':
  main(sys.argv)
