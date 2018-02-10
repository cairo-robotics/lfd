import json
from collections import OrderedDict
from lfd_processor.constraints import UprightConstraint, HeightConstraint
from lfd_processor.items import SawyerRobot


def import_configuration(filepath):
    with open(filepath) as json_data:
        return json.load(json_data, object_pairs_hook=OrderedDict)


class Environment(object):

    def __init__(self, items, robot, constraints):
        self.items = items
        self.robot = robot
        self.constraints = constraints

    def get_robot_state(self):
        return self.robot.get_state()

    def get_robot_info(self):
        return self.robot.get_info()

    def get_item_states(self):
        item_states = []
        if self.items is not None:
            for item in self.items:
                item_states.append(item.get_state())
        return item_states

    def get_item_info(self):
        item_info = []
        if self.items is not None:
            for item in self.items:
                item_info.append(item.get_info())
        return item_info

    def get_constraint_by_id(self, constraint_id):
        return [constraint for constraint in self.constraints if constraint.id == constraint_id][0]

    def check_constraint_triggers(self):
        triggered_constraints = []
        for constraint in self.constraints:
            result = constraint.check_trigger()
            if result is not 0:
                triggered_constraints.append(constraint.id)
        return triggered_constraints


class Demonstration(object):

    def __init__(self, observations, aligned_observation=None):
        self.observations = observations
        self.aligned_observation = aligned_observation

    def get_observation_by_index(self, idx):
        return self.observations[idx]

    def get_applied_constraint_order(self):
        constraint_order = []
        curr = []
        for ob in self.aligned_observations:
            if curr != ob.data["applied_constraints"]:
                constraint_order.append(ob.data["applied_constraints"])
                curr = ob.data["applied_constraints"]
        return constraint_order


class Observation(object):
    def __init__(self, observation_data):
        self.data = observation_data

    def get_timestamp(self):
        return self.data["time"]

    def get_robot_data(self):
        return self.data["robot"]

    def get_item_data(self, item_id):
        for item in self.data["items"]:
            # return first occurance, should only be one
            if item["id"] is item_id:
                return item

    def get_triggered_constraint_data(self):
        return self.data["triggered_constraints"]

    def get_applied_constraint_data(self):
        if "applied_constraints" in self.data.keys():
            return self.data["applied_constraints"]
        else:
            return None


class RobotFactory(object):

    def __init__(self, robot_configs):
        self.configs = robot_configs
        self.classes = {
            "SawyerRobot": SawyerRobot,
        }

    def generate_robots(self):
        robots = []
        for config in self.configs:
            robots.append(self.classes[config["class"]](*tuple(config["init_args"].values())))
        return robots


class ConstraintFactory(object):

    def __init__(self, constraint_configs):
        self.configs = constraint_configs
        self.classes = {
            "UprightConstraint": UprightConstraint,
            "HeightConstraint": HeightConstraint
        }

    def generate_constraints(self):
        constraints = []
        for config in self.configs:
            constraints.append(self.classes[config["class"]](*tuple(config["init_args"].values())))
        return constraints
