import logging
from .utils import array_random
import sys
from random import shuffle

logger = logging.getLogger()

"""
This is a new implementation of the map generation -- it's much lighter
than the original incarnation which had multiple objects and was
pretty confusing.

This is (mostly) the same algorithm, except that it's been cleaned up and is
substantially easier to understand.  It also takes out all of the
dependencies (beyond array_random) so it could be used for other things.
"""

def gen_graph(count,
              edge_dist=[[10, 1], [10, 2], [10, 3], [15, 4]],
              use_existing_node_dist=[[6, True], [9, False]],
              edge_distance_dist=[[10, 0], [10, 1], [5, 2], [5, 3]]):
    """
    Generate an undirected graph which represents a dungeon map.
    
    The *_dist parameters are distributions:  a list of (weight, value) 
    pairs used to do a weighted selection.

    Parameters:
        count:  the number of nodes to create
        edge_dist:  The distribution for number of edges per node
        use_existing_node_dist: When creating edges for a node, the
            distribution used for using an existing node (True) or
            creating a new node (False).  Adding weight to the True
            choice will make the graph bushier, less weight makes it
            deeper and skinnier.
        edge_distance_dist: When connecting to an existing node (per the
            False selection above) how many levels away from the current
            depth should be used as a selection criteria

    Returns a list of edges which comprise a pair of node numbers.  Every
    pair will have the node numbers sorted, and each pair will be unique
    """
    if count < 4:
        raise ValueError("The map needs at least 4 nodes")
    
    # find the max edge count in the edge distribution:  that
    # will give us the maximum edges per node
    max_edges = max([x[1] for x in edge_dist])
    if max_edges < 1:
        raise ValueError("The edge_dist doesn't specify enough edges per node")

    # each node consists of a triple [count, target, depth] where
    # the target is how many edges we want, the count is how many we currently 
    # have, and the depth is how deep it is from the start
    nodes = []
    edges = set()

    # seed the map with the start node, and the adjacent nodes
    nodes.append([0, array_random(edge_dist), 0])

    while len(nodes) < count:
        available = [i for i, v in enumerate(nodes) if v[0] < v[1]]
        logger.debug(f"On this pass, there are {len(available)} nodes available of {len(nodes)}.")
        if not available:
            # all of the nodes are full.  Pick a random node
            # that has less than the maximum number of edges
            # and increase its target by 1.  That will give us
            # a place to hook on the next node and hopefully
            # it will have lots of edges.
            available = [i for i, v in enumerate(nodes) if v[0] < max_edges]
            if not available:
                raise ValueError("Graph is full.  Try adding more edges per node")
            node = array_random(available)
            nodes[node][1] += 1
            # now the graph has one node that has an 
            # available edge.
            available = [node]
            logger.debug(f"Added another edge opening for {node}")
        
        # fill in all of the edges for all of the
        # available nodes.
        shuffle(available)
        for node_id in available:
            node = nodes[node_id]
            for _ in [1]: #range(node[1] - node[0]):
                other = None
                if array_random(use_existing_node_dist):
                    # Connect to an existing node if possible, making
                    # sure that's at the same depth, or nearly so,
                    # according to the distribution in edge_distance_dist
                    distance = array_random(edge_distance_dist)
                    up = node[2] - distance
                    down = node[2] + distance
                    logger.debug(f"{len(nodes)}: Finding nearby nodes {up} <= x <= {down}")
                    near_nodes = [i for i, v in enumerate(nodes) if up <= v[2] <= down and v[0] < v[1]]
                    logger.debug(f"Found {len(near_nodes)} to choose from!")
                    if near_nodes:
                        other = array_random(near_nodes)
                        logger.debug(f"Connecting local node: {other} to {node_id}")

                if other is None:
                    # Create a new node to connect to
                    new_node = [0, array_random(edge_dist), node[2] + 1]
                    other = len(nodes)
                    logger.debug(f"Adding a new node {other}")
                    nodes.append(new_node)

                # try to connect the current node and the other node (if they're different)
                if node_id != other:
                    new_edge = tuple(sorted([node_id, other]))
                    if new_edge not in edges:
                        edges.add(new_edge)
                        nodes[node_id][0] += 1
                        nodes[other][0] += 1

    return edges


