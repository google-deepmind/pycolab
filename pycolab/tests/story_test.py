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

"""Tests of the "Story" framework for making big games out of smaller ones."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import unittest

from pycolab import ascii_art
from pycolab import cropping
from pycolab import storytelling
from pycolab import things as plab_things
from pycolab.prefab_parts import sprites as prefab_sprites
from pycolab.tests import test_things as tt

import six


class StoryTest(tt.PycolabTestCase):

  ### Helpers ###

  class _DieRightward(prefab_sprites.MazeWalker):
    """A boring Sprite that pauses, walks one step rightward, and terminates.

    Some additional functions are present to support other tests:
    - If the_plot['chapter_names'] is a list, then when this Sprite terminates
      a game, it will pop that list and assign the resulting value to
      the_plot.next_chapter, directing which chapter should follow.
    """

    def __init__(self, corner, position, character):
      super(StoryTest._DieRightward, self).__init__(
          corner, position, character, impassable='', confined_to_board=True)

    def update(self, actions, board, layers, backdrop, things, the_plot):
      if the_plot.frame == 1:
        self._east(board, the_plot)
        the_plot.terminate_episode()
        if 'chapter_names' in the_plot:
          the_plot.next_chapter = the_plot['chapter_names'].pop(0)

  class _IdleDrape(plab_things.Drape):
    """An even more boring Drape that does nothing at all."""

    def update(self, *args, **kwargs):
      pass

  def _make_game(self, art):
    """Make a game with one _DieRightward sprite. Valid chars are [P.]."""
    return ascii_art.ascii_art_to_game(
        art, what_lies_beneath='.', sprites={'P': self._DieRightward})

  ### Tests ###

  def testSequenceOfGames(self):
    """A `Story` will play through a sequence of games automatically."""

    # The four games in the sequence use these four worlds.
    arts = list(zip(['P..', '...', '...', '...'],
                    ['...', '...', 'P..', '...'],
                    ['...', 'P..', '...', '.P.']))

    # Create and start the story.
    story = storytelling.Story(
        [lambda art=a: self._make_game(art) for a in arts])
    observation, reward, pcontinue = story.its_showtime()
    del reward, pcontinue  # unused

    # The first frame is the first game's first frame.
    self.assertBoard(observation.board, arts[0])

    # This should set us up to get the following sequence of observations.
    self.assertMachinima(
        engine=story,
        frames=[
            # The second frame is the second game's first frame. The terminal
            # frame from the first game is discarded, so we never get to see
            # the Sprite move rightward. (None was the action just prior to the
            # second frame. Actions are not used in this test.)
            (None, arts[1]),

            # The third frame is the third game's first frame. Same reasoning.
            (None, arts[2]),

            # The fourth frame is the fourth game's first frame.
            (None, arts[3]),

            # The fifth frame is the fourth game's last frame. In a Story, you
            # always see the terminal frame of the very last game (and you see
            # no other game's terminal frame).
            (None, ['...',
                    '...',
                    '..P'])
        ],
    )

  def testDictOfGames(self):
    """A `Story` will run as directed through a dict of games."""

    # The two games in this dict will use these two worlds.
    arts = {'one': ['P..',
                    '...',
                    '...'],
            'two': ['...',
                    '.P.',
                    '...']}

    # Create and start the story. Note how we inject a value into the first
    # game's Plot that _DieRightward uses to tell Story how to advance through
    # the various subgames. A bit roundabout, but it has the side-effect of also
    # testing that Plot contents persist between games.
    story = storytelling.Story(
        {k: lambda art=v: self._make_game(art) for k, v in arts.items()},
        first_chapter='one')
    story.current_game.the_plot['chapter_names'] = ['two', 'one', 'one', None]
    observation, reward, pcontinue = story.its_showtime()
    del reward, pcontinue  # unused

    # For better narration of these observation comparisons, read through
    # testSequenceOfGames.
    self.assertBoard(observation.board, arts['one'])  # First frame.
    self.assertMachinima(engine=story, frames=[(None, arts['two']),
                                               (None, arts['one']),
                                               (None, arts['one']),
                                               (None, ['.P.',
                                                       '...',
                                                       '...'])])

  def testCropping(self):
    """Observations from subgames can be cropped for mutual compatibility."""

    # The games will use these worlds.
    arts = [
        ['P..',
         '...',
         '...'],

        ['...............',
         '...............',
         '.......P.......',
         '...............',
         '...............'],

        ['...',
         '...',
         'P..'],
    ]

    # But these croppers will ensure that they all have a reasonable size.
    croppers = [
        None,
        cropping.FixedCropper(top_left_corner=(1, 6), rows=3, cols=3),
        cropping.FixedCropper(top_left_corner=(0, 0), rows=3, cols=3),
    ]

    # Create and start the story.
    story = storytelling.Story(
        chapters=[lambda art=a: self._make_game(art) for a in arts],
        croppers=croppers)
    observation, reward, pcontinue = story.its_showtime()
    del reward, pcontinue  # unused

    # For better narration of these observation comparisons, read through
    # testSequenceOfGames.
    self.assertBoard(observation.board, arts[0])
    self.assertMachinima(engine=story, frames=[(None, ['...',
                                                       '.P.',
                                                       '...']),
                                               (None, arts[2]),
                                               (None, ['...',
                                                       '...',
                                                       '.P.'])])

  def testInterGameRewardAccumulation(self):
    """Inter-game terminal rewards are carried into the next game."""

    class GenerousQuitterDrape(plab_things.Drape):
      """This Drape gives a reward of 5 and quits immediately."""

      def update(self, actions, board, layers, backdrop, things, the_plot):
        the_plot.add_reward(5.0)
        the_plot.terminate_episode()

    # Create a new Story with all subgames using the usual art.
    art = ['P..',
           '...',
           '...']
    story = storytelling.Story([
        # this is perfectly readable :-P
        # pylint: disable=g-long-lambda

        # We should see the initial observation from this first game, but not
        # the second, terminal observation. The agent receives no reward.
        lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                            sprites={'P': self._DieRightward}),

        # We should see no observations from the next three games, since they
        # all terminate immediately (courtesy of GenerousQuitterDrape). However,
        # they also each contribute an additional 5.0 to the summed reward the
        # agent will eventually see...
        lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                            sprites={'P': self._DieRightward},
                                            drapes={'Q': GenerousQuitterDrape}),
        lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                            sprites={'P': self._DieRightward},
                                            drapes={'Q': GenerousQuitterDrape}),
        lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                            sprites={'P': self._DieRightward},
                                            drapes={'Q': GenerousQuitterDrape}),

        # ...when it sees the first observation of this game here. The second,
        # terminal observation is dropped, but then...
        lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                            sprites={'P': self._DieRightward}),

        # ...we finally see an observation from a game involving a
        # GenerousQuitterDrape when we see its first and terminal step, as the
        # terminal step of the story. We also receive another 5.0 reward.
        lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                            sprites={'P': self._DieRightward},
                                            drapes={'Q': GenerousQuitterDrape}),
        # pylint: enable=g-long-lambda
    ])

    # Now to see if our predictions are true.
    observation, reward, pcontinue = story.its_showtime()  # First step.
    self.assertBoard(observation.board, art)
    self.assertIsNone(reward)  # Nobody assigned any reward in this step.
    self.assertEqual(pcontinue, 1.0)

    observation, reward, pcontinue = story.play(None)  # Second step.
    self.assertBoard(observation.board, art)  # First obs. of penultimate game.
    self.assertEqual(reward, 15.0)  # Summed across final steps of games 2-4.
    self.assertEqual(pcontinue, 1.0)

    observation, reward, pcontinue = story.play(None)  # Third, final step.
    self.assertBoard(observation.board, art)  # Terminal obs. of final game.
    self.assertEqual(reward, 5.0)  # From the GenerousQuitterDrape.
    self.assertEqual(pcontinue, 0.0)

  def testStandIns(self):
    """The "abstraction breakers" in `Story` are suitably simulated."""

    # The games will use these worlds.
    arts = list(zip(['P~~', '..S'],
                    ['~~~', '..D'],
                    ['www', '###']))

    # Create the story.
    story = storytelling.Story([
        # this is perfectly readable :-P
        # pylint: disable=g-long-lambda
        lambda: ascii_art.ascii_art_to_game(arts[0], what_lies_beneath='~',
                                            sprites={'P': self._DieRightward},
                                            drapes={'w': self._IdleDrape}),
        lambda: ascii_art.ascii_art_to_game(arts[1], what_lies_beneath='.',
                                            sprites={'S': self._DieRightward},
                                            drapes={'D': self._IdleDrape})
        # pylint: enable=g-long-lambda
    ])

    # The "abstraction breaker" methods should fake the same sorts of results
    # that you would get if the Story were actually implemented by a single
    # Engine. Sprites and Drapes should contain an entry for any character
    # associated with a Sprite or a Drape across all the games, and the
    # contrived Backdrop's palette should have all the backdrop characters
    # from anywhere in the story.
    self.assertEqual(sorted(story.backdrop.palette), ['#', '.', '~'])
    self.assertEqual(sorted(story.things), ['D', 'P', 'S', 'w'])

    # The only real Sprites and Drapes in story.things are the ones from the
    # current game; the others are dummies. Here we test the module function
    # that identifies dummies.
    self.assertTrue(storytelling.is_fictional(story.things['D']))
    self.assertFalse(storytelling.is_fictional(story.things['P']))
    self.assertTrue(storytelling.is_fictional(story.things['S']))
    self.assertFalse(storytelling.is_fictional(story.things['w']))

  def testCompatibilityChecking(self):
    """The `Story` constructor spots compatibility problems between games."""

    # The first Story will fail because these game worlds have different sizes,
    # and there are no croppers in use.
    arts = [
        ['P..',
         '...',
         '...'],

        ['...............',
         '...............',
         '.......P.......',
         '...............',
         '...............'],
    ]

    with six.assertRaisesRegex(self, ValueError,
                               'observations that are the same'):
      _ = storytelling.Story([lambda art=a: self._make_game(art) for a in arts])

    # This next Story will fail because characters are shared between Sprites,
    # Drapes, and at least one Backdrop.
    art = ['1..',
           '.2.',
           '..3']

    error_regexp = (r'.*same character in two different ways'
                    r'.*both a Sprite and a Drape: \[2\];'
                    r'.*both a Sprite and in a Backdrop: \[1\];'
                    r'.*both a Drape and in a Backdrop: \[3\].*')
    with six.assertRaisesRegex(self, ValueError, error_regexp):
      _ = storytelling.Story([
          # pylint: disable=g-long-lambda
          lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                              sprites={'1': self._DieRightward},
                                              drapes={'2': self._IdleDrape}),
          lambda: ascii_art.ascii_art_to_game(art, what_lies_beneath='.',
                                              sprites={'2': self._DieRightward},
                                              drapes={'3': self._IdleDrape}),
          # pylint: enable=g-long-lambda
      ])


def main(argv=()):
  del argv  # Unused.
  unittest.main()


if __name__ == '__main__':
  main(sys.argv)
