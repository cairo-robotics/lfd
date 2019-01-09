import itertools
from collections import defaultdict
import rospy
import numpy as np
from networkx import MultiDiGraph


class KeyframeGraph(MultiDiGraph):
    """
    NetworkX MultiDiGraph extended graph class for containing keyframes and their corresponding models.
    """

    def __init__(self):
        MultiDiGraph.__init__(self)

    def get_keyframe_sequence(self):
        """
        Provides the keyframe sequence in order.

        Returns
        -------
        node_chain : list
            List of keyframe/node sequence.
        """

        node_chain = list(set(itertools.chain(*self.edges())))
        node_chain.sort()
        return node_chain

    def cull_node(self, node):
        """
        Takes received node and removes it from the task graph

        Parameters
        ----------
        node: hashable networkx node name (usually int)
            the node to be removed from network x graph
        """

        next_nodes = [x for x in self.successors(node)]
        prev_nodes = [x for x in self.predecessors(node)]
        if next_nodes == []:
            prev_node = prev_nodes[0]
            self.remove_edge(prev_node, node)
            rospy.loginfo("Node %s has been culled", node)
        elif prev_nodes == []:
            next_node = next_nodes[0]
            self.remove_edge(node, next_node)
            rospy.loginfo("Node %s has been culled", node)
        else:
            prev_node = prev_nodes[0]
            next_node = next_nodes[0]
            self.add_edge(prev_node, next_node)
            self.remove_edge(prev_node, node)
            self.remove_edge(node, next_node)
            rospy.loginfo("Node %s has been culled", node)

    def fit_models(self, observation_vectorizor):
        """
        Fits all models in graph. Expects that each keyframe node in graph has populated "observation" key
        as a list of Observation objects.

        Parameters
        ----------
        observation_vectorizor : function
            Function that takes observations stored in graph and converts their data into vector form for use by model
            fitting function.
        """

        for node in self.nodes():
            np_array = []
            for obsv in self.nodes[node]["observations"]:
                vector = np.array(observation_vectorizor(obsv))
                np_array.append(np.array(observation_vectorizor(obsv)))
            np_array = np.array(np_array)
            self.nodes[node]["model"].fit(np_array)


class ObservationClusterer():
    """
    Clusters together observations by keyframe ID and gathers pertinent information regarding each keyframe. This will
    be used by a KeyframeGraph object.
    """

    def generate_clusters(self, demonstrations):
        """
        Generates the clustered Observations from a list of Demonstrations.

        Parameters
        ----------
        demonstrations : list
            List of the Demonstration objects from which labeled Observations.

        Returns
        -------
        clusters : dict
            Dictionary of clusters with top level keys the keyframe IDs and values another dictionary populated
            with pertinent information associated with each keyframe (i.e. keyframe type, applied constraints etc,.)
        """

        observations = []
        for demo in demonstrations:
            for obsv in demo.observations:
                observations.append(obsv)
        clusters = self.cluster_observations_by_id(observations)
        for cluster in clusters.values():
            self.assign_keyframe_type(cluster)
            self.assign_applied_constraints(cluster)
        return clusters

    def cluster_observations_by_id(self, observations):
        """
        Takes in a the entirety of observations from all Demosntrations and groups them together 
        by keyframe ID.

        Parameters
        ----------
        observations : list
            List of the Observation objects to cluster.

        Returns
        -------
        clusters : dict
            Dictionary of clusters with top level keys the keyframe IDs and values another dictionary populated
            with 'observations' key with list of Observations.
        """

        clusters = defaultdict(lambda: {"observations": []})

        for obsv in observations:
            keyframe_id = obsv.get_keyframe_info()[0]
            if keyframe_id is not None:
                clusters[keyframe_id]["observations"].append(obsv)
        return clusters

    def assign_keyframe_type(self, cluster):
        """
        Assigns the keyframe type for the given keyframe cluster.


        Parameters
        ----------
        cluster : dict
            Dictionary to assign the keyframe type.
        """

        keyframe_type = cluster['observations'][0].get_keyframe_info()[1]
        cluster["keyframe_type"] = keyframe_type

    def assign_applied_constraints(self, cluster):
        """
        Assigns the applied constraints for the given keyframe cluster.

        Parameters
        ----------
        cluster : dict
            Dictionary to assign the applied constraints..
        """

        applied_constraints = cluster['observations'][0].get_applied_constraint_data()
        cluster["applied_constraints"] = applied_constraints