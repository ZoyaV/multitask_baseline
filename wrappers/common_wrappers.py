import gym
import os
import logging
import numpy as np
from typing import Generator
from collections import OrderedDict

logger = logging.getLogger(__file__)
IGLU_ENABLE_LOG = os.environ.get('IGLU_ENABLE_LOG', '')


class Wrapper(gym.Wrapper):
    def stack_actions(self):
        if isinstance(self.env, Wrapper):
            return self.env.stack_actions()

    def wrap_observation(self, obs, reward, done, info):
        if hasattr(self.env, 'wrap_observation'):
            return self.env.wrap_observation(obs, reward, done, info)
        else:
            return obs


class ActionsWrapper(Wrapper):
    def wrap_action(self, action) -> Generator:
        raise NotImplementedError

    def stack_actions(self):
        def gen_actions(action):
            for action in self.wrap_action(action):
                wrapped = None
                if hasattr(self.env, 'stack_actions'):
                    wrapped = self.env.stack_actions()
                if wrapped is not None:
                    yield from wrapped(action)
                else:
                    yield action

        return gen_actions

    def step(self, action):
        total_reward = 0
        for a in self.wrap_action(action):
            obs, reward, done, info = super().step(a)
            total_reward += reward
            if done:
                return obs, total_reward, done, info
        return obs, total_reward, done, info


class ObsWrapper(Wrapper):
    def observation(self, obs, reward=None, done=None, info=None):
        raise NotImplementedError

    def wrap_observation(self, obs, reward, done, info):
        new_obs = self.observation(obs, reward, done, info)
        return self.env.wrap_observation(new_obs, reward, done, info)

    def reset(self):
        return self.observation(super().reset())

    def step(self, action):
        obs, reward, done, info = super().step(action)

        info['grid'] = obs['grid']
        info['agentPos'] = obs['agentPos']
        #info['obs'] = obs['obs']
        return self.observation(obs, reward, done, info), reward, done, info


def flat_action_space(action_space):
    if action_space == 'human-level':
        return flat_human_level
    else:
        raise Exception("Action space not found!")


def no_op():
    return OrderedDict([('attack', 0), ('back', 0), ('camera', np.array([0., 0.])),
                        ('forward', 0), ('hotbar', 0), ('jump', 0), ('left', 0), ('right', 0),
                        ('use', 0)])


def flat_human_level(env, camera_delta=5):
    #  print(help(env.action_space))
    binary = ['attack', 'forward', 'back', 'left', 'right', 'jump']
    discretes = [no_op()]
    for op in binary:
        dummy = no_op()
        dummy[op] = 1
        discretes.append(dummy)
    camera_x = no_op()
    camera_x['camera'][0] = camera_delta
    discretes.append(camera_x)
    camera_x = no_op()
    camera_x['camera'][0] = -camera_delta
    discretes.append(camera_x)
    camera_y = no_op()
    camera_y['camera'][1] = camera_delta
    discretes.append(camera_y)
    camera_y = no_op()
    camera_y['camera'][1] = -camera_delta
    discretes.append(camera_y)
    for i in range(6):
        dummy = no_op()
        dummy['hotbar'] = i + 1
        discretes.append(dummy)
    discretes.append(no_op())
    return discretes


class Discretization(ActionsWrapper):
    def __init__(self, env, flatten):
        super().__init__(env)
        camera_delta = 5
        #  print(env.action_space.no_op)
        self.discretes = flatten(env, camera_delta)
        self.action_space = gym.spaces.Discrete(len(self.discretes))
        self.old_action_space = env.action_space
        self.last_action = None

    def wrap_action(self, action=None, raw_action=None):
        if action is not None:
            # raise Exception(action)
            action = self.discretes[action]
        elif raw_action is not None:
            action = raw_action
        yield action

class JumpAfterPlace(ActionsWrapper):
    def __init__(self, env):
        min_inventory_value = 10
        max_inventory_value = 17
        self.act_space = (min_inventory_value, max_inventory_value)
        super().__init__(env)

    def wrap_action(self, action=None):
       if (action>self.act_space[0]) and (action<self.act_space[1])>0:
           yield action
           yield 6
       else:
           yield action


class ColorWrapper(ActionsWrapper):
    def __init__(self, env):
        super().__init__(env)
        min_inventory_value = 10
        max_inventory_value = 17
        self.color_space = (min_inventory_value, max_inventory_value)

    def wrap_action(self, action=None):
        tcolor = np.sum(self.env.task.target_grid)
        if (action>self.color_space[0]) and (action<self.color_space[1]) and tcolor>0:
            action = int(self.color_space[0]+tcolor)
        yield action


class VectorObservationWrapper(ObsWrapper):
    def __init__(self, env, with_obs=False):
        super().__init__(env)
        obs_space ={
            'agentPos': gym.spaces.Box(low=-5000.0, high=5000.0, shape=(5,)),
            'grid': gym.spaces.Box(low=0.0, high=6.0, shape=(9, 11, 11)),
            'inventory': gym.spaces.Box(low=0.0, high=20.0, shape=(6,)),
            'target_grid': gym.spaces.Box(low=0.0, high=6.0, shape=(9, 11, 11)),
        }
        if with_obs:
            obs_space['obs'] = gym.spaces.Box(low=0, high=1, shape=(self.size, self.size, 3), dtype=np.float32)
        self.observation_space = gym.spaces.Dict(obs_space)

    def observation(self, obs, reward=None, done=None, info=None):
        if IGLU_ENABLE_LOG == '1':
            self.check_component(
                obs['agentPos'], 'agentPos', self.observation_space['agentPos'].low,
                self.observation_space['agentPos'].high
            )
            self.check_component(
                obs['inventory'], 'inventory', self.observation_space['inventory'].low,
                self.observation_space['inventory'].high
            )
            self.check_component(
                obs['grid'], 'grid', self.observation_space['grid'].low,
                self.observation_space['grid'].high
            )
        if info is not None:
            if 'target_grid' in info:
                target_grid = self.env.task.target_grid
            else:
                logger.error(f'info: {info}')
                if hasattr(self.unwrapped, 'should_reset'):
                    self.unwrapped.should_reset(True)
                target_grid = self.env.task.target_grid
        else:
            target_grid = self.env.task.target_grid

        obs_ = {
            'agentPos': obs['agentPos'],
            'grid': obs['grid'],
            'inventory': obs['inventory'],
            'target_grid': target_grid,
        }
        if 'obs' in self.observation_space:
            obs_['obs'] = obs['obs']
        return obs_

    def check_component(self, arr, name, low, hi):
        if (arr < low).any():
            logger.info(f'{name} is below level {low}:')
            logger.info((arr < low).nonzero())
            logger.info(arr[arr < low])
        if (arr > hi).any():
            logger.info(f'{name} is above level {hi}:')
            logger.info((arr > hi).nonzero())
            logger.info(arr[arr > hi])
