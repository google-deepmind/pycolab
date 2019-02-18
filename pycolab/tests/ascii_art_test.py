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

"""Basic tests for the ascii_art module.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import unittest

from pycolab import ascii_art

import six


class AsciiArtTest(unittest.TestCase):

  def testRaiseErrors(self):
    """Checks how `ascii_art_to_uint8_nparray` handles incorrect input."""
    # Correct input.
    art = ['ab', 'ba']
    _ = ascii_art.ascii_art_to_uint8_nparray(art)

    # Incorrect input: not all the same length.
    art = ['ab', 'bab']
    with six.assertRaisesRegex(
        self,
        ValueError, 'except for the concatenation axis must match exactly'):
      _ = ascii_art.ascii_art_to_uint8_nparray(art)

    # Incorrect input: not all strings.
    art = ['a', 2]
    with six.assertRaisesRegex(
        self,
        TypeError, 'the argument to ascii_art_to_uint8_nparray must be a list'):
      _ = ascii_art.ascii_art_to_uint8_nparray(art)

    # Incorrect input: list of list (special case of the above).
    art = [['a', 'b'], ['b', 'a']]
    with six.assertRaisesRegex(
        self,
        TypeError, 'Did you pass a list of list of single characters?'):
      _ = ascii_art.ascii_art_to_uint8_nparray(art)


def main(argv=()):
  del argv  # Unused.
  unittest.main()


if __name__ == '__main__':
  main(sys.argv)
