# Box-World environment

Box-World is a perceptually simple but combinatorially complex environment that
requires abstract relational reasoning and planning. It consists of a
fully-observable pixel grid representing a room with keys and boxes randomly
scattered. The agent, represented by a single dark gray pixel, is randomly
placed in this room and can move in four directions: _up_, _down_, _left_,
_right_. Keys are represented by a single colored pixel. The agent can pick up a
loose key (i.e., one not adjacent to any other colored pixel) by walking over
it. Boxes are represented by two adjacent colored pixels - the pixel on the
right represents the box's lock and its color indicates which key can be used to
open that lock; the pixel on the left indicates the content of the box which is
inaccessible while the box is locked. To collect the content of a box the agent
must first collect the key that opens the box (the one that matches the lock's
color) and walk over the lock, making the lock disappear. At this point the
content of the box becomes accessible and can be picked up by the agent. Most
boxes contain keys that, if made accessible, can be used to open other boxes.
One of the boxes contains a gem, represented by a single white pixel. The goal
of the agent is to collect the gem. Keys in the agent's possession are depicted
as a pixel in the top-left corner.

In each level there is a unique sequence of boxes that need to be opened in
order to reach the gem. Opening one wrong box (a distractor box) leads to a
dead-end where the gem cannot be reached and the level becomes unsolvable. There
are three user-controlled parameters that contribute to the difficulty of the
level: (1) the number of boxes in the path to the goal (solution length); (2)
the number of distractor branches; (3) the length of the distractor branches. In
general, the task is difficult for a few reasons. First, a key can only be used
once, so the agent must be able to reason about whether a particular box is
along a distractor branch or along the solution path. Second, keys and boxes
appear in random locations in the room, emphasising a capacity to reason about
keys and boxes based on their abstract relations, rather than based on their
spatial positions.

Each level in Box-World is procedurally generated. We start by generating a
random graph (a tree) that defines the correct path to the goal - i.e., the
sequence of boxes that need to be opened to reach the gem. This graph also
defines multiple distractor branches - boxes that lead to dead-ends. The agent,
keys and boxes, including the one containing the gem, are positioned randomly in
the room, assuring that there is enough space for the agent to navigate between
boxes. There is a total of 20 keys and 20 locks that are randomly sampled to
produce the level. An agent receives a reward of +10 for collecting the gem, +1
for opening a box in the solution path and -1 for opening a distractor box. A
level terminates immediately after the gem is collected, a distractor box is
opened, or a maximum number of steps is reached (default is 120 steps). The
generation process produces a very large number of possible trees, making it
extremely unlikely that the agent will face the same level twice.

This environment was first introduced in the following paper:
[https://arxiv.org/abs/1806.01830](https://arxiv.org/abs/1806.01830)
