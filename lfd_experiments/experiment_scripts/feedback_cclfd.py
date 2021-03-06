#!/usr/bin/env python
import os
import argparse
from functools import partial

import rospy

import intera_interface
from intera_interface import CHECK_VERSION

from robot_interface.moveit_interface import SawyerMoveitInterface
from cairo_lfd.core.record import SawyerDemonstrationRecorder, SawyerDemonstrationLabeler
from cairo_lfd.core.environment import Environment, Observation, Demonstration
from cairo_lfd.core.items import ItemFactory
from cairo_lfd.core.robots import RobotFactory
from cairo_lfd.data.io import load_json_files, load_lfd_configuration
from cairo_lfd.data.vectorization import vectorize_demonstration, get_observation_joint_vector
from cairo_lfd.data.alignment import DemonstrationAlignment
from cairo_lfd.data.processing import DataProcessingPipeline, RelativeKinematicsProcessor, RelativePositionProcessor, InContactProcessor, SphereOfInfluenceProcessor, WithinPerimeterProcessor
from cairo_lfd.constraints.concept_constraints import ConstraintFactory
from cairo_lfd.constraints.triggers import TriggerFactory
from cairo_lfd.core.lfd import CC_LFD
from cairo_lfd.controllers.study_controllers import FeedbackLfDStudyController


def main():
    arg_fmt = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=arg_fmt,
                                     description=main.__doc__)
    required = parser.add_argument_group('required arguments')

    required.add_argument(
        '-c', '--config', dest='config', required=True,
        help='the file path of the demonstration '
    )

    required.add_argument(
        '-i', '--input_directory', dest='input_directory', required=True,
        help='the directory from which to input prior poor/broken demonstration .json files'
    )

    required.add_argument(
        '-o', '--output_directory', dest='output_directory', required=True,
        help='the directory to save the given subjects .json files data'
    )

    args = parser.parse_args(rospy.myargv()[1:])

    ############################
    #  ROS Node Initialization #
    ############################

    print("Initializing node... ")
    rospy.init_node("feedback_cclfd")
    print("Getting robot state... ")
    robot_state = intera_interface.RobotEnable(CHECK_VERSION)
    print("Enabling robot... ")
    robot_state.enable()

    ########################
    # Import Configuration #
    ########################

    config_filepath = args.config
    configs = load_lfd_configuration(config_filepath)

    #################################
    # Configure the LFD class model #
    #################################

    model_settings = configs["settings"]["modeling_settings"]
    moveit_interface = SawyerMoveitInterface()
    moveit_interface.set_velocity_scaling(.35)
    moveit_interface.set_acceleration_scaling(.25)
    moveit_interface.set_planner(str(model_settings["planner"]))
    cclfd = CC_LFD(configs, model_settings, moveit_interface)
    cclfd.build_environment()

    #####################################
    # Raw Demonstration Data Processors #
    #####################################

    # Build processors and process demonstrations to generate derivative data e.g. relative position.
    rk_processor = RelativeKinematicsProcessor(cclfd.environment.get_item_ids(), cclfd.environment.get_robot_id())
    ic_processor = InContactProcessor(cclfd.environment.get_item_ids(), cclfd.environment.get_robot_id(), .06, .5)
    soi_processor = SphereOfInfluenceProcessor(cclfd.environment.get_item_ids(), cclfd.environment.get_robot_id())
    rp_processor = RelativePositionProcessor(cclfd.environment.get_item_ids(), cclfd.environment.get_robot_id())
    wp_processor = WithinPerimeterProcessor(cclfd.environment.get_item_ids(), cclfd.environment.get_robot_id())
    processing_pipeline = DataProcessingPipeline([rk_processor, ic_processor, soi_processor, rp_processor, wp_processor])

    ###############################################
    # Configure the Sawyer Demonstration Recorder #
    ###############################################

    rec_settings = configs["settings"]["recording_settings"]
    recorder = SawyerDemonstrationRecorder(rec_settings, cclfd.environment, processing_pipeline, publish_constraint_validity=True)
    rospy.on_shutdown(recorder.stop)

    ##########################################################
    # Configure the Sawyer Demonstration Aligner and Labeler #
    ##########################################################

    label_settings = configs["settings"]["labeling_settings"]
    # Demonstration vectorizor that converts observations into state vector in desired space for DTW alignment.
    demo_vecotorizor = partial(vectorize_demonstration, vectorizors=[get_observation_joint_vector])
    alignment = DemonstrationAlignment(demo_vecotorizor)
    demo_labeler = SawyerDemonstrationLabeler(label_settings, alignment)

    ################################################
    # Import Poor/Broken Skills for AR 4 LfD Study #
    ################################################

    prior_poor_demonstrations = load_json_files(args.input_directory + "/*.json")
    # Convert imported data into Demonstrations and Observations
    demonstrations = []
    for datum in prior_poor_demonstrations["data"]:
        observations = []
        for entry in datum:
            observations.append(Observation(entry))
        demonstrations.append(Demonstration(observations))
    if len(demonstrations) == 0:
        rospy.logwarn("No prior demonstration data to model!! You sure you're using the right experiment script?")
        return 0
    labeled_initial_demos = demo_labeler.label(demonstrations)
    cclfd.build_environment()
    cclfd.build_keyframe_graph(labeled_initial_demos, model_settings.get("bandwidth", .025))
    cclfd.sample_keyframes(model_settings.get("number_of_samples", 50), automate_threshold=True)

    study = FeedbackLfDStudyController(cclfd, recorder, demo_labeler, labeled_initial_demos, args.output_directory)
    study.run()


if __name__ == '__main__':
    main()