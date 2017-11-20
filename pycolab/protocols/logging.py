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

"""Simple message logging for pycolab game entities.

The interactive nature of pycolab games makes it difficult to do useful things
like "printf debugging"---if you're using an interface like the Curses UI, you
won't be able to see printed strings. This protocol allows game entities to log
messages to the Plot object. User interfaces can query this object and display
accumulated messages to the user in whatever way is best.

Most game implementations will not need to import this protocol directly---
logging is so fundamental that the Plot object expresses a `log` method that's
syntactic sugar for the log function in this file.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


def log(the_plot, message):
  """Log a message for eventual disposal by the game engine user.

  Here, "game engine user" means a user interface or an environment interface,
  for example. (Clients are not required to deal with messages, but if they do,
  this is how to get a message to them.)

  Most game implementations will not need to call this function directly---
  logging is so fundamental that the Plot object expresses a `log` method that's
  syntactic sugar for this function.

  Args:
    the_plot: the pycolab game's `Plot` object.
    message: A string message to convey to the game engine user.
  """
  the_plot.setdefault('log_messages', []).append(message)


def consume(the_plot):
  """Obtain messages logged by game entities since the last call to `consume`.

  This function is meant to be called by "game engine users" (user interfaces,
  environment interfaces, etc.) to obtain the latest set of log messages
  emitted by the game entities. These systems can then dispose of these messages
  in whatever manner is the most appropriate.

  Args:
    the_plot: the pycolab game's `Plot` object.

  Returns:
    The list of all log messages supplied by the `log` method since the last
    time `consume` was called (or ever, if `consume` has never been called).
  """
  messages = the_plot.setdefault('log_messages', [])
  # Hand off the current messages to a new list that we return.
  our_messages = messages[:]
  del messages[:]
  return our_messages
