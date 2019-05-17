# Copyright 2018 The trfl Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Deterministic Policy Gradient (DPG) ops.

These ops support training a value based agent on control problems with
continuous action spaces. The agent's actions are assumed to be continuous
vectors of size `action_dimension`.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections

# Dependency imports
import tensorflow as tf
from trfl import base_ops

DPGExtra = collections.namedtuple("dpg_extra", ["q_max", "a_max", "dqda"])


def dpg(q_max, a_max, dqda_clipping=None, clip_norm=False, name="DpgLearning"):
  """Implements the Deterministic Policy Gradient (DPG) loss as a TensorFlow Op.

  This op implements the loss for the `actor`, the `critic` can instead be
  updated by minimizing the `value_ops.td_learning` loss.

  See "Deterministic Policy Gradient Algorithms" by Silver, Lever, Heess,
  Degris, Wierstra, Riedmiller (http://proceedings.mlr.press/v32/silver14.pdf).

  Args:
    q_max: Tensor holding Q-values generated by Q network with the input of
      (state, a_max) pair, shape `[B]`.
    a_max: Tensor holding the optimal action, shape `[B, action_dimension]`.
    dqda_clipping: `int` or `float`, clips the gradient dqda element-wise
      between `[-dqda_clipping, dqda_clipping]`.
    clip_norm: Whether to perform dqda clipping on the vector norm of the last
      dimension, or component wise (default).
    name: name to prefix ops created within this op.

  Returns:
    A namedtuple with fields:

    * `loss`: a tensor containing the batch of losses, shape `[B]`.
    * `extra`: a namedtuple with fields:
        * `q_max`: Tensor holding the optimal Q values, `[B]`.
        * `a_max`: Tensor holding the optimal action, `[B, action_dimension]`.
        * `dqda`: Tensor holding the derivative dq/da, `[B, action_dimension]`.

  Raises:
    ValueError: If `q_max` doesn't depend on `a_max` or if `dqda_clipping <= 0`.
  """

  # DPG op.
  with tf.name_scope(name, values=[q_max, a_max]):

    # Calculate the gradient dq/da.
    dqda = tf.gradients([q_max], [a_max])[0]

    # Check that `q_max` depends on `a_max`.
    if dqda is None:
      raise ValueError("q_max needs to be a function of a_max")

    # Clipping the gradient dq/da.
    if dqda_clipping is not None:
      if dqda_clipping <= 0:
        raise ValueError("dqda_clipping should be bigger than 0, {} found"
                         .format(dqda_clipping))
      if clip_norm:
        dqda = tf.clip_by_norm(dqda, dqda_clipping, axes=-1)
      else:
        dqda = tf.clip_by_value(dqda, -1. * dqda_clipping, dqda_clipping)

    # Target_a ensures correct gradient calculated during backprop.
    target_a = dqda + a_max
    # Stop the gradient going through Q network when backprop.
    target_a = tf.stop_gradient(target_a)
    # Gradient only go through actor network.
    loss = 0.5 * tf.reduce_sum(tf.square(target_a - a_max), axis=-1)
    return base_ops.LossOutput(
        loss, DPGExtra(q_max=q_max, a_max=a_max, dqda=dqda))
