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

"""Basic tests of the pycolab engine.

Tests in this file evaluate the several core components of pycolab, not just
`engine.py`.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np
import sys
import unittest

from pycolab import ascii_art
from pycolab import rendering
from pycolab import things as plab_things
from pycolab.tests import test_things as tt


class EngineTest(tt.PycolabTestCase):

  def testUpdateScheduleAndZOrder(self):
    """The engine abides by the update schedule and the Z-ordering."""

    # Our test takes place in this 3x5 world...
    art = ['.acb.',
           '..c..',
           '.dce.']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath='.',

        # a, b, c, and d are sprites.
        sprites=dict(a=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     b=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     d=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     e=ascii_art.Partial(tt.TestMazeWalker, impassable='')),

        # c is a drape that just sits there; Z is an invisible drape that
        # also just sits there.
        drapes=dict(c=tt.TestDrape,
                    Z=tt.TestDrape),

        # This update schedule means that in a single game iteration:
        # 1. the Backdrop, a, and b all update, then the board is re-rendered,
        # 2. c updates, then the board is re-rendered,
        # 3. d and e update, then the board is re-rendered,
        # 4. Z updates, then the board is re-rendered.
        update_schedule=[['a', 'b'], ['c'], ['d', 'e'], ['Z']],

        # The Z-ordering says to render the entities in this order, from
        # back to front.
        z_order='Zabcde')

    ### GAME ITERATION #0. During the first update sweep, since none of the
    ### Sprites change their locations and none of the Drapes change their
    ### curtains, all entities will see the initial rendering of the board.

    tt.pre_update(engine, 'a', self.expectBoard(art, err_msg='a @ 0'))
    tt.pre_update(engine, 'b', self.expectBoard(art, err_msg='b @ 0'))
    tt.pre_update(engine, 'c', self.expectBoard(art, err_msg='c @ 0'))
    tt.pre_update(engine, 'd', self.expectBoard(art, err_msg='d @ 0'))
    tt.pre_update(engine, 'e', self.expectBoard(art, err_msg='e @ 0'))
    tt.pre_update(engine, 'Z', self.expectBoard(art, err_msg='Z @ 0'))

    observation, unused_reward, discount = engine.its_showtime()

    # Check that the observation is right and that discount is 1.
    self.assertBoard(observation.board, art, err_msg='obs @ 0')
    self.assertEqual(discount, 1.0)

    # Check that miscellaneous properties work.
    self.assertEqual(engine.rows, 3)
    self.assertEqual(engine.cols, 5)
    self.assertEqual(engine.z_order, ['Z', 'a', 'b', 'c', 'd', 'e'])
    self.assertSetEqual(set(engine.things.keys()),
                        {'a', 'b', 'c', 'd', 'e', 'Z'})
    self.assertIn('.', engine.backdrop.palette)

    ### GAME ITERATION #1. All sprites take a step to the right. As the
    ### update sweep takes place, the segmented update schedule causes
    ### different entities to see the board in different configurations.

    # a and b see the board as it was rendered after the last iteration.
    tt.pre_update(engine, 'a', self.expectBoard(art, err_msg='a @ 1'))
    tt.pre_update(engine, 'b', self.expectBoard(art, err_msg='b @ 1'))

    # c sees the board after a and b have moved right, but not d and e. Note
    # the Z-ordering determining how c and d overlap.
    tt.pre_update(engine, 'c', self.expectBoard(['..c.b',
                                                 '..c..',
                                                 '.dce.'], err_msg='c @ 1'))

    ## d and e see the board after c's update, but of course c didn't change...
    tt.pre_update(engine, 'd', self.expectBoard(['..c.b',
                                                 '..c..',
                                                 '.dce.'], err_msg='d @ 1'))
    tt.pre_update(engine, 'e', self.expectBoard(['..c.b',
                                                 '..c..',
                                                 '.dce.'], err_msg='e @ 1'))

    # Z sees the board after everyone else has moved.
    tt.pre_update(engine, 'Z', self.expectBoard(['..c.b',
                                                 '..c..',
                                                 '..d.e'], err_msg='Z @ 1'))

    observation, unused_reward, unused_discount = engine.play('e')

    # Check that the observation is right and that discount is 1.
    self.assertBoard(observation.board, ['..c.b',
                                         '..c..',
                                         '..d.e'], err_msg='obs @ 1')
    self.assertEqual(discount, 1.0)

    ### GAME ITERATION #2. All sprites take a step to the left. We'll trust
    ### that this took place in the expected order and just check that the
    ### observation is correct.

    observation, unused_reward, unused_discount = engine.play('w')
    self.assertBoard(observation.board, art, err_msg='obs @ 2')
    self.assertEqual(discount, 1.0)

    ### GAME ITERATION #3. All sprites take another step to the left. We
    ### check everything again, this time.

    # First update group.
    tt.pre_update(engine, 'a', self.expectBoard(art, err_msg='a @ 3'))
    tt.pre_update(engine, 'b', self.expectBoard(art, err_msg='b @ 3'))

    # Second update group.
    tt.pre_update(engine, 'c', self.expectBoard(['a.c..',
                                                 '..c..',
                                                 '.dce.'], err_msg='c @ 3'))

    # Second update group.
    tt.pre_update(engine, 'd', self.expectBoard(['a.c..',
                                                 '..c..',
                                                 '.dce.'], err_msg='d @ 3'))
    tt.pre_update(engine, 'e', self.expectBoard(['a.c..',
                                                 '..c..',
                                                 '.dce.'], err_msg='e @ 3'))

    observation, unused_reward, unused_discount = engine.play('w')

    # Check that the observation is right and that discount is 1.
    self.assertBoard(observation.board, ['a.c..',
                                         '..c..',
                                         'd.e..'], err_msg='obs @ 3')
    self.assertEqual(discount, 1.0)

  def testRewardAndEpisodeEndWithDefaultDiscount(self):
    """Game entities can assign reward, terminate game with default discount."""
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda
    self._do_test_reward_and_episode_end(expected_discount=0.0, q_pre_update=(
        lambda actions, board, layers, backdrop, things, the_plot: (
            the_plot.terminate_episode())))

  def testRewardAndEpisodeEndWithCustomDiscount(self):
    """Game entities can assign reward, terminate game with custom discount."""
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda
    self._do_test_reward_and_episode_end(expected_discount=0.5, q_pre_update=(
        lambda actions, board, layers, backdrop, things, the_plot: (
            the_plot.terminate_episode(0.5))))

  def _do_test_reward_and_episode_end(self, q_pre_update, expected_discount):
    """Core implementation of `testRewardAndEpisodeEndWith*Discount` tests.

    Args:
      q_pre_update: Pre-`update` code to inject for the Q sprite.
      expected_discount: `discount` we expect to observe after the final
          game step.
    """
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda

    # Our test takes place in this tiny world:
    art = ['.........',
           '...Q.R...',
           '.........']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath='.',
        # Q and R are sprites.
        sprites=dict(Q=tt.TestSprite, R=tt.TestSprite),
        # We set a fixed update schedule for deterministic tests.
        update_schedule='QR')

    ### GAME ITERATION #0. Nothing happens. No entity has issued a reward, so
    ### the reward is None.

    unused_observation, reward, discount = engine.its_showtime()
    self.assertIsNone(reward)
    self.assertEqual(discount, 1.0)
    self.assertFalse(engine.game_over)

    ### GAME ITERATION #1. Have the sprites credit us with some reward. Note
    ### how reward is accumulated across all entities.

    tt.pre_update(engine, 'Q',
                  lambda actions, board, layers, backdrop, things, the_plot: (
                      the_plot.add_reward('pyco')))
    tt.pre_update(engine, 'R',
                  lambda actions, board, layers, backdrop, things, the_plot: (
                      the_plot.add_reward('lab!')))

    unused_observation, reward, discount = engine.play('mound of beans')
    self.assertEqual(reward, 'pycolab!')
    self.assertEqual(discount, 1.0)
    self.assertFalse(engine.game_over)

    ### GAME ITERATION #2. Have Q call the whole thing off.

    tt.pre_update(engine, 'Q', q_pre_update)
    tt.pre_update(engine, 'R',
                  lambda actions, board, layers, backdrop, things, the_plot: (
                      the_plot.add_reward('trousers')))

    unused_observation, reward, discount = engine.play('mound of beans')
    self.assertEqual(reward, 'trousers')
    self.assertEqual(discount, expected_discount)
    self.assertTrue(engine.game_over)

  def testChangingZOrdering(self):
    """Game entities can change the Z-ordering."""
    # Not helpful in this test, since argument lists are long:
    # pylint: disable=g-long-lambda

    # Our test takes place in this very tiny world:
    art = ['.abc.']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath='.',
        # a, b, and c are sprites.
        sprites=dict(a=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     b=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                     c=ascii_art.Partial(tt.TestMazeWalker, impassable='')),
        # Note this initial z-ordering.
        z_order='abc')

    ### GAME ITERATION #0. Nothing happens; we just get the game started.

    engine.its_showtime()

    ### GAME ITERATION #1. All of our sprites move to stand on top of one
    ### another. No Z-order change yet.

    observation, unused_reward, unused_discount = engine.play(
        {'a': 'e', 'c': 'w'})
    self.assertBoard(observation.board, ['..c..'])

    ### GAME ITERATION #2. b moves in front of c. Z-ordering should be 'acb'.

    tt.pre_update(engine, 'b',
                  lambda actions, board, layers, backdrop, things, the_plot: (
                      the_plot.change_z_order('b', 'c')))
    observation, unused_reward, unused_discount = engine.play(None)
    self.assertBoard(observation.board, ['..b..'])

    ### GAME ITERATION #2. c moves to the back. Z-ordering should be 'cab'.

    tt.pre_update(engine, 'c',
                  lambda actions, board, layers, backdrop, things, the_plot: (
                      the_plot.change_z_order('c', None)))
    observation, unused_reward, unused_discount = engine.play(None)
    self.assertBoard(observation.board, ['..b..'])

    ### GAME ITERATION #3. b moves to the back. Z-ordering should be 'bca'.

    tt.pre_update(engine, 'b',
                  lambda actions, board, layers, backdrop, things, the_plot: (
                      the_plot.change_z_order('b', None)))
    observation, unused_reward, unused_discount = engine.play(None)
    self.assertBoard(observation.board, ['..a..'])

  def testPlotStateVariables(self):
    """State variables inside the Plot are updated correctly."""

    # Our test takes place in this very tiny world:
    art = ['.abc.']

    # Here we make the game.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath='.',
        # a, b, and c are sprites.
        sprites=dict(a=tt.TestSprite,
                     b=tt.TestSprite,
                     c=tt.TestSprite),
        # We will test to see that these update groups are reflected in the
        # update_group property of the Plot. The ascii_art_to_game function
        # comes up with its own names for update groups, though, and those are
        # off limits to us, so we can't just check values directly...
        update_schedule=[['a', 'b'], ['c']])

    # ...so, we will store game iterations and update group values in this
    # dict, and check that all is as expected.
    state_info = []
    def add_state_info(actions, board, layers, backdrop, things, the_plot):
      del actions, board, layers, backdrop, things  # Unused.
      state_info.append((the_plot.frame, the_plot.update_group))

    ### GAME ITERATION #0.

    tt.pre_update(engine, 'a', add_state_info)
    tt.pre_update(engine, 'b', add_state_info)
    tt.pre_update(engine, 'c', add_state_info)

    engine.its_showtime()

    [(a_frame, a_update_group),
     (b_frame, b_update_group),
     (c_frame, c_update_group)] = state_info[:]

    self.assertEqual([0, 0, 0], [a_frame, b_frame, c_frame])
    self.assertEqual(a_update_group, b_update_group)
    self.assertNotEqual(a_update_group, c_update_group)

    ### GAME ITERATION #1.

    tt.pre_update(engine, 'a', add_state_info)
    tt.pre_update(engine, 'b', add_state_info)
    tt.pre_update(engine, 'c', add_state_info)

    engine.play('↑↑↓↓←→←→BA★')

    [(a_frame, a_new_update_group),
     (b_frame, b_new_update_group),
     (c_frame, c_new_update_group)] = state_info[3:]  # note 3:

    self.assertEqual([1, 1, 1], [a_frame, b_frame, c_frame])
    self.assertEqual(a_update_group, a_new_update_group)
    self.assertEqual(b_update_group, b_new_update_group)
    self.assertEqual(c_update_group, c_new_update_group)

  def testRenderingWithOcclusion(self):
    """Test rendering of non-overlapping game entities (occlusion enabled).

    Note: although this test specifies that the engine should render overlapping
    game entities in a particular way, it does not test this rendering
    behaviour, focusing instead on non-overlapping game entities (which should
    look identical in all renderings). Specific tests of occlusion behaviour
    appear in `testOcclusionInLayers`.
    """
    self._testRendering(occlusion_in_layers=True)

  def testRenderingWithoutOcclusion(self):
    """Test rendering of non-overlapping game entities (occlusion disabled).

    Note: although this test specifies that the engine should render overlapping
    game entities in a particular way, it does not test this rendering
    behaviour, focusing instead on non-overlapping game entities (which should
    look identical in all renderings). Specific tests of occlusion behaviour
    appear in `testOcclusionInLayers`.
    """
    self._testRendering(occlusion_in_layers=False)

  def _testRendering(self, occlusion_in_layers):
    """Test rendering of non-overlapping game entities."""

    # Our test concerns renderings of this game world.
    art = ['..H..H..o..',
           '..HHHH..i..',
           '..H..H..i..']

    # Here we make the game. Note specification of Q, an empty Drape.
    engine = ascii_art.ascii_art_to_game(
        art=art, what_lies_beneath='.',
        drapes=dict(
            Q=tt.TestDrape),
        occlusion_in_layers=occlusion_in_layers)

    ### GAME ITERATION 0. We just run it to get an observation.

    observation, unused_reward, unused_discount = engine.its_showtime()

    ### Evaluate the observation's binary feature masks.

    # The observation's layer member should have an entry for all characters
    # that could be on the board, including ones for invisible Drapes.
    self.assertEqual(sorted(observation.layers.keys()),
                     sorted(list('.HioQ')))

    # Check that all the layer masks have the right contents.
    self._assertMask(observation.layers['.'], ['11011011011',
                                               '11000011011',
                                               '11011011011'])

    self._assertMask(observation.layers['H'], ['00100100000',
                                               '00111100000',
                                               '00100100000'])

    self._assertMask(observation.layers['i'], ['00000000000',
                                               '00000000100',
                                               '00000000100'])

    self._assertMask(observation.layers['o'], ['00000000100',
                                               '00000000000',
                                               '00000000000'])

    self._assertMask(observation.layers['Q'], ['00000000000',
                                               '00000000000',
                                               '00000000000'])

    ### Test correct operation of ObservationCharacterRepainter.

    repainter = rendering.ObservationCharacterRepainter(
        dict(H='J', i='J', Q='M'))
    repainted = repainter(observation)

    # Check that the repainted board looks correct.
    self.assertBoard(repainted.board, ['..J..J..o..',
                                       '..JJJJ..J..',
                                       '..J..J..J..'])

    # The repainted board should have these binary feature masks:
    self.assertEqual(sorted(repainted.layers.keys()),
                     sorted(list('.JoM')))

    # The binary feature masks should have these contents:
    self._assertMask(repainted.layers['.'], ['11011011011',
                                             '11000011011',
                                             '11011011011'])

    self._assertMask(repainted.layers['J'], ['00100100000',
                                             '00111100100',
                                             '00100100100'])

    self._assertMask(repainted.layers['o'], ['00000000100',
                                             '00000000000',
                                             '00000000000'])

    self._assertMask(repainted.layers['M'], ['00000000000',
                                             '00000000000',
                                             '00000000000'])

    ### Test correct operation of ObservationToArray for 2-D and 3-D arrays.

    # For the 2-D conversion, we'll do our own "homebrew" repainter, but just
    # for the Observation.board representation. Recall that the board member of
    # an Observation is a 2-D array of uint8s.
    converter = rendering.ObservationToArray({'.': ord(' '),
                                              'J': ord('#'),
                                              'o': ord('*'),
                                              'M': ord('?')}, dtype=np.uint8)
    converted = converter(repainted)
    self.assertBoard(converted, ['  #  #  *  ',
                                 '  ####  #  ',
                                 '  #  #  #  '])

    # Test that layer permutation happens correctly for the 2-D case.

    converter = rendering.ObservationToArray({'.': ord(' '),
                                              'J': ord('#'),
                                              'o': ord('*'),
                                              'M': ord('?')},
                                             dtype=np.uint8, permute=(1, 0))
    converted = converter(repainted)
    self.assertBoard(converted, ['   ',
                                 '   ',
                                 '###',
                                 ' # ',
                                 ' # ',
                                 '###',
                                 '   ',
                                 '   ',
                                 '*##',
                                 '   ',
                                 '   '])

    # For the 3-D conversion, we'll create a 3-D feature array that's a lot like
    # our feature masks.
    converter = rendering.ObservationToArray({'.': (1, 0, 0, 0),
                                              'J': (0, 1, 0, 0),
                                              'o': (0, 0, 1, 0),
                                              'M': (0, 0, 0, 1)}, dtype=bool)
    converted = converter(repainted)
    self.assertEqual(converted.shape, (4, 3, 11))

    self._assertMask(converted[0, :], ['11011011011',
                                       '11000011011',
                                       '11011011011'])

    self._assertMask(converted[1, :], ['00100100000',
                                       '00111100100',
                                       '00100100100'])

    self._assertMask(converted[2, :], ['00000000100',
                                       '00000000000',
                                       '00000000000'])

    self._assertMask(converted[3, :], ['00000000000',
                                       '00000000000',
                                       '00000000000'])

    # And another layer permutation test for the 3-D case.
    converter = rendering.ObservationToArray({'.': (1, 0, 0, 0),
                                              'J': (0, 1, 0, 0),
                                              'o': (0, 0, 1, 0),
                                              'M': (0, 0, 0, 1)},
                                             dtype=bool, permute=(1, 2, 0))
    converted = converter(repainted)
    self.assertEqual(converted.shape, (3, 11, 4))

    self._assertMask(converted[..., 0], ['11011011011',
                                         '11000011011',
                                         '11011011011'])

    self._assertMask(converted[..., 1], ['00100100000',
                                         '00111100100',
                                         '00100100100'])

    self._assertMask(converted[..., 2], ['00000000100',
                                         '00000000000',
                                         '00000000000'])

    self._assertMask(converted[..., 3], ['00000000000',
                                         '00000000000',
                                         '00000000000'])

    ### Test ObservationToFeatureArray, which creates 3-D feature arrays faster.

    converter = rendering.ObservationToFeatureArray('.JoM')
    converted = converter(repainted)
    self.assertEqual(converted.shape, (4, 3, 11))

    self._assertMask(converted[0, :], ['11011011011',
                                       '11000011011',
                                       '11011011011'])

    self._assertMask(converted[1, :], ['00100100000',
                                       '00111100100',
                                       '00100100100'])

    self._assertMask(converted[2, :], ['00000000100',
                                       '00000000000',
                                       '00000000000'])

    self._assertMask(converted[3, :], ['00000000000',
                                       '00000000000',
                                       '00000000000'])

    ### Test ObservationToFeatureArray's layer permutation capability.

    converter = rendering.ObservationToFeatureArray('.J', permute=(1, 0, 2))
    converted = converter(repainted)
    self.assertEqual(converted.shape, (3, 2, 11))

    self._assertMask(converted[0, :], ['11011011011',
                                       '00100100000'])

    self._assertMask(converted[1, :], ['11000011011',
                                       '00111100100'])

    self._assertMask(converted[2, :], ['11011011011',
                                       '00100100100'])

  def testOcclusionInLayers(self):
    """Test rendering of overlapping game entities."""

    class FullOnDrape(plab_things.Drape):
      """A `Drape` class that fills its curtain immediately on construction."""

      def __init__(self, curtain, character):
        curtain.fill(True)
        super(FullOnDrape, self).__init__(curtain, character)

      def update(self, actions, board, layers, backdrop, things, the_plot):
        """Does nothing."""
        pass

    def build_engine(occlusion_in_layers):
      # Our test concerns renderings of this game world.
      art = ['..',
             '..']

      # Here we make the game. The sprite `a` will cover a Drape element `b` ,
      # which covers another Sprite `c`. If `occlusion_in_layers` is False, we
      # should still be able to see them in the layers, otherwise we should not.
      # In the flat `board`, occlusion stil occurs regardless and we should only
      # see those entities with higher z-order.
      engine = ascii_art.ascii_art_to_game(
          art=art, what_lies_beneath='.',
          # Note: since a and c do not appear in the game art, these sprites
          # are placed in the top-left corner (0, 0).
          sprites=dict(a=ascii_art.Partial(tt.TestMazeWalker, impassable=''),
                       c=ascii_art.Partial(tt.TestMazeWalker, impassable='')),
          drapes=dict(b=FullOnDrape),
          occlusion_in_layers=occlusion_in_layers,
          z_order='abc')
      return engine

    # Test occlusion disabled in layers
    engine = build_engine(False)
    observation, unused_reward, unused_discount = engine.its_showtime()
    self._assertMask(observation.layers['.'], ['11',
                                               '11'])
    self._assertMask(observation.layers['a'], ['10',
                                               '00'])
    self._assertMask(observation.layers['b'], ['11',
                                               '11'])
    self._assertMask(observation.layers['c'], ['10',
                                               '00'])
    # Note that occlusion still occurs in the flat `board`.
    self.assertBoard(observation.board, ['cb',
                                         'bb'])

    # Test occlusion enabled in layers
    engine = build_engine(True)
    observation, unused_reward, unused_discount = engine.its_showtime()
    self._assertMask(observation.layers['.'], ['00',
                                               '00'])
    self._assertMask(observation.layers['a'], ['00',
                                               '00'])
    self._assertMask(observation.layers['b'], ['01',
                                               '11'])
    self._assertMask(observation.layers['c'], ['10',
                                               '00'])
    self.assertBoard(observation.board, ['cb',
                                         'bb'])

  def _assertMask(self, actual_mask, mask_art, err_msg=''):  # pylint: disable=invalid-name
    """Compares numpy bool_ arrays with "art" drawn as lists of '0' and '1'."""
    np.testing.assert_array_equal(
        actual_mask,
        np.array([list(row) for row in mask_art]).astype(bool),
        err_msg)


def main(argv=()):
  del argv  # Unused.
  unittest.main()


if __name__ == '__main__':
  main(sys.argv)
