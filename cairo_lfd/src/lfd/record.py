"""
The record.py module contains classes and methods for recording data during live demonstrations.
"""
import rospy
from lfd.environment import Observation, Demonstration


class SawyerRecorder(object):
    """
    Class to record state data from the ReThink Robotics Sawyer robot for capturing demonstrated data for 
    LfD experimentation.

    Attributes
    ----------
    _raw_rate : int
        The rate at which to capture state data.
    _rate : int
        The ROScore rate.
    _start_time : float
        Current time in ROScore.
    _done : bool
        Termination flag.
    """
    def __init__(self, rate):
        """
        Parameters
        ----------
        rate : int
            The rate at which to capture state data.
        """
        self._raw_rate = rate
        self._rate = rospy.Rate(rate)
        self._start_time = rospy.get_time()
        self._done = False

    def _time_stamp(self):
        """
        Captures time difference from start time to current time.

        Returns
        ----------
         : float
            Current time passed so far.
        """
        return rospy.get_time() - self._start_time

    def stop(self):
        """
        Stop recording by setting _done flag to True.
        """
        self._done = True

    def done(self):
        """
        Return whether or not recording is done.

        Returns
        : bool
            The _done attribute.
        """
        if rospy.is_shutdown():
            self.stop()
        return self._done

    def record_demonstrations(self, environment):
        """
        Records the current joint positions to a csv file if outputFilename was
        provided at construction this function will record the latest set of
        joint angles in a csv format.

        If a file exists, the function will overwrite existing file.

        Parameters
        ----------
        environment: Environment
            The Environment object of the current LfD experiment.

        Returns
        -------
        demosntrations : list
            List of Demonstration objects each of which captures Observations during user demonstrations.
        """
        robot = environment.robot

        demonstrations = []

        while not self.done():
            user_input = raw_input("Press 'r' to record or 'q' to quit.\n")
            while user_input != 'q':
                if user_input == "r":
                    observations = []
                    rospy.loginfo("RECORDING.")
                    while True:
                        if robot._gripper:
                            if robot._cuff.upper_button():
                                robot._gripper.open()
                            elif robot._cuff.lower_button():
                                robot._gripper.close()
                        data = {
                            "time": self._time_stamp(),
                            "robot": environment.get_robot_state(),
                            "items": environment.get_item_states(),
                            "triggered_constraints": environment.check_constraint_triggers()
                        } 
                        observation = Observation(data)
                        observations.append(observation)
                        self._rate.sleep()
                        if environment.robot._navigator.get_button_state("right_button_ok") == 1:
                            demonstrations.append(Demonstration(observations))
                            rospy.loginfo("~~~CAPTURED~~~")
                            break
                user_input = raw_input("Demostration captured!\n Press 'r' to record again or 'q' to end the session.\n")
            if user_input == 'q':
                self.stop()

        return demonstrations