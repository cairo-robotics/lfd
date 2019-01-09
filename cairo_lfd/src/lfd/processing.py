"""
The processing.py module contains classes and methods for manipulating data/objects into difference forms.
"""
import numpy as np
from geometry_msgs.msg import Pose
from environment import Observation


def convert_data_to_pose(position, orientation):
    """
    Converts raw position and orientation data to a ROS message Pose object.

    Parameters
    ----------
    position : list
        List of numerical values representing x,y,z position.

    orientation : list
        List of numerical values representing the x,y,z,w values of a quaternion.

    normalize_quaternion : bool
        Flag indicating whether to normalize the values of the quaternion entries.

    Returns
    -------
    pose: geometry_msgs.msgs.Pose
        The Pose object
    """
    pose = Pose()
    pose.position.x = position[0]
    pose.position.y = position[1]
    pose.position.z = position[2]
    pose.orientation.x = orientation[0]
    pose.orientation.y = orientation[1]
    pose.orientation.z = orientation[2]
    pose.orientation.w = orientation[3]
    return pose


class SawyerSampleConverter(object):

    def __init__(self, interface):
        self.interface = interface

    def convert(self, sample, run_fk=False, normalize_quaternion=False):
        """


        Parameters
        ----------
        sample : list
            Raw sample to convert. Either joint configuration or pose [x,y,z,x,y,z,w] as a list.

        run_fk : bool
            Flag indicating whether to run foward kinematrics or not.

        normalize_quaternion : bool
            Flag indicating whether to normalize the values of the quaternion entries.

        Returns
        -------
        obsv : lfd.environment.Observation
            Observation object constructed from the converted sample.
        """

        if run_fk is True:
            sample = self._run_foward_kinematics(sample)
        if normalize_quaternion:
            # Normalize the quaternion values otherwise they will not be valid. This may be needed if FK is done
            # using MoveIt's FK server. However, generally this is not needed if using Intera.
            sample[3], sample[4], sample[5], sample[6] = self._normalize_quaternion(sample[3], sample[4], sample[5], sample[6])

        if len(sample) > 7:
            # If length > 7, we know there must be joint data, so creat Obs w/ joints.
            obsv = Observation.init_samples(sample[0:3], sample[3:7], sample[7:14])
        else:
            obsv = Observation.init_samples(sample[0:3], sample[3:7], None)
        return obsv

    def _run_foward_kinematics(self, sample):
        pose = self.interface.get_FK_pose(sample)
        if pose is not None:
            sample = np.insert(sample, 0, pose.orientation.w, axis=0)
            sample = np.insert(sample, 0, pose.orientation.z, axis=0)
            sample = np.insert(sample, 0, pose.orientation.y, axis=0)
            sample = np.insert(sample, 0, pose.orientation.x, axis=0)
            sample = np.insert(sample, 0, pose.position.z, axis=0)
            sample = np.insert(sample, 0, pose.position.y, axis=0)
            sample = np.insert(sample, 0, pose.position.x, axis=0)
        return sample

    def _normalize_quaternion(self, x, y, z, w):

        normalize = np.sqrt(x**2 + y**2 +
                            z**2 + w**2)
        x = x / normalize
        y = y / normalize
        z = z / normalize
        w = w / normalize
        return x, y, z, w