from adblockparser import AdblockRules
import csv
import hgraph
import json
import multiprocessing
import networkx as nx
import os
import random
import sys
import time
import traceback

# (IMPORTANT) Constants need to be defined in the config file per server
from branch_size_analysis_config import *

# Do not include .txt at the end because the process number will be appended at the end
OUTPUT_PATH = OUTPUT_DIR + "branch_info_" + SERVER_NUMBER
SIZE_ANALYSIS_PATH = OUTPUT_DIR + "size_analysis_" + SERVER_NUMBER
REMAINING_SIZE_ANALYSIS_PATH = OUTPUT_DIR + "remaining_analysis" + SERVER_NUMBER
DEPTHS_PATH = OUTPUT_DIR + "depths_" + SERVER_NUMBER
ERROR_PATH = OUTPUT_DIR + "branch_errors_" + SERVER_NUMBER

# Lists of filter paths
AD_PATHS = [FILTER_DIR + s for s in AD_FILES]
TRACKER_PATHS = [FILTER_DIR + s for s in TRACKER_FILES]

# List of .txt files; Each file contains a string that evaluates into the actual list of graphml paths
GRAPHML_LIST_PATHS = [GRAPHML_LIST_DIR + s for s in GRAPHML_LIST_FILES]

# Constants for resource types
UNBLOCKED = 0
AD = 1
TRACKER = 2
OTHER = 3
AD_TRACKER = 4
BRANCH_BLOCKED = 5

def nodes_set_to_list(nodes_set):
    """Given a dict or set of nodes, return a sorted list of nodes."""
    nodes_list = list(nodes_set)
    for i in range(len(nodes_list)):
        nodes_list[i] = int(nodes_list[i][1:])
    nodes_list.sort()
    for i in range(len(nodes_list)):
        nodes_list[i] = "n" + str(nodes_list[i])
    return nodes_list

def get_rules(paths):
    """Generate rules from filter lists."""
    raw_rules = []
    for path in paths:
        with open(path, "r", encoding="utf8") as f:
            raw_rules += f.read().splitlines()
                
    return AdblockRules(raw_rules)

def get_graphml_paths(paths):
    """Extract list of graphml paths from get_paths.py lists."""
    graphml_paths = []
    for path in paths:
        with open(path, "r", encoding="utf8") as f:
            graphml_paths += eval(f.read())

    return graphml_paths
    
def get_graph_and_nodes(path):
    """Returns a graph and its associated resource nodes."""
    graph = hgraph.read_graph(path)
    resource_nodes = hgraph.resource_nodes_no_data(graph)
    blocked_nodes = hgraph.blocked_resources_no_data(graph, resource_nodes)
    unblocked_nodes = list(set(resource_nodes) - set(blocked_nodes))
    
    return graph, resource_nodes, blocked_nodes, unblocked_nodes

def DFS(graph, node, starting_node, visited_nodes, branches, html_scripts, depth, DFS_stack):
    """"""
    # Names used in comments: Current Node (Script) -> Connected Node (HTML Element) -> Next Node (Script)
    
    # Outgoing edges of current node
    out_edges = graph.out_edges(nbunch=node, data=True)
    
    for out_node_id, in_node_id, edge_data in out_edges:
        if in_node_id in visited_nodes:
            # Skip connected node if already visited
            continue
        
        if edge_data["edge type"] == "create node":
            # Connected node was created by current node
            
            branches[starting_node].append(in_node_id) # Keep track of connected node in branch
            visited_nodes.add(in_node_id) # Connected node is now visited

            if in_node_id in html_scripts:
                # Connected node has an associated next node; Add next node to DFS stack
                next_node_id = html_scripts[in_node_id]
                branches[starting_node].append(next_node_id)
                visited_nodes.add(next_node_id)
                DFS_stack.append([graph, next_node_id, starting_node, visited_nodes, branches, html_scripts, depth + 1])

def get_blocked_bytes(graph, node):
    """Given a node, calculate how many bytes were requested."""
    total = 0
    resource_node_out_edges = graph.out_edges(nbunch=node, data=True)
    for _, _, edge_data in resource_node_out_edges:
        if edge_data['edge type'] == 'request complete':
            # Outgoing edge contains number of bytes used by resource
            total += int(edge_data['value'])
    return total

def branch_analysis(graphml_paths, ad_rules, tracker_rules, process_count):
    num_done = 0
    num_graphml_paths = len(graphml_paths)

    for path in graphml_paths:
        url = path.split("/")[-2]
        print(str(num_done) + "/" + str(num_graphml_paths) + ": " + url)

        DFS_stack = []
        depths = {}

        num_branches = [0, 0, 0, 0, 0] # Unblocked, Ad, Tracker, Other, Ad_Tracker
        blocked_bytes = [0, 0, 0, 0, 0, 0] # Unblocked, Ad, Tracker, Other, Ad_Tracker, Branch_Blocked

        # Parse graph for nodes
        try:
            graph, resource_nodes, blocked_nodes, unblocked_nodes = get_graph_and_nodes(path)
            
            # Get script nodes
            script_nodes = hgraph.get_scripts(graph)
            blocked_script_nodes = {} # Script id: url
            unblocked_script_nodes = {} # Script id: url
            html_scripts = {} # HTML id: Outgoing script id
            script_resources = {} # Script id: Original resource node
            for html_node, script_node, resource_node, is_blocked in script_nodes:
                node_data = graph.nodes[script_node]
                if "url" not in node_data:
                    continue

                html_scripts[html_node] = script_node # Add script id as value of html key
                script_resources[script_node] = resource_node
                if is_blocked:
                    blocked_script_nodes[script_node] = node_data["url"] # Add script id to blocked dict
                else:
                    unblocked_script_nodes[script_node] = node_data["url"] # Add script id to to unblocked dict

            blocked_starting_nodes = nodes_set_to_list(blocked_script_nodes) # List of all script nodes in sorted order
            unblocked_starting_nodes = nodes_set_to_list(unblocked_script_nodes) # List of all script nodes in sorted order
            visited_nodes = set() # Nodes visted by DFS
            branches = {} # Dict of all script/HTML element nodes generated by a starting node
            branch_resources = {} # Dict of resource nodes created the branch of the starting node

            calculated = set()
            unblocked_calculated = set()

            # Generate branches and first level off each branch (All blocked)
            for starting_node in blocked_starting_nodes:
                if starting_node in visited_nodes:
                    continue # Skip node already in a branch

                in_edges = graph.in_edges(nbunch=starting_node, data=True)
                for out_node_id, in_node_id, edge_data in in_edges:
                    if edge_data['edge type'] == 'execute':
                        visited_nodes.add(out_node_id)
                # Generate branch of this starting node
                branches[starting_node] = [starting_node]
                branch_resources[starting_node] = [script_resources[starting_node]]
                visited_nodes.add(script_resources[starting_node])
                visited_nodes.add(starting_node)
                
                max_depth = 0
                
                DFS_stack.append([graph, starting_node, starting_node, visited_nodes, branches, html_scripts, 0])
                
                while len(DFS_stack) != 0:
                    popped_list = DFS_stack.pop()
                    visited_nodes.add(popped_list[1])
                    visited_nodes.add(popped_list[2])
                    if max_depth < popped_list[6]:
                        max_depth = popped_list[6]
                    DFS(popped_list[0], popped_list[1], popped_list[2], visited_nodes,
                        popped_list[4], popped_list[5], popped_list[6], DFS_stack)
                    
                depths[starting_node] = max_depth
                    
                current_branch_resources = set()
                earliest_ancestor = branch_resources[starting_node][0]
                isTrackerBlock = tracker_rules.should_block(graph.nodes[earliest_ancestor]['url'])
                isAdBlock =  ad_rules.should_block(graph.nodes[earliest_ancestor]['url'])

                earliest_ancestor_type = OTHER
                if isTrackerBlock and isAdBlock:
                    earliest_ancestor_type = AD_TRACKER
                elif isTrackerBlock:
                    earliest_ancestor_type = TRACKER
                elif isAdBlock:
                    earliest_ancestor_type = AD

                # First level of each branch
                current_branch_resources = set()
                for node_id in branches[starting_node]:
                    out_edges = graph.out_edges(nbunch=node_id, data=True)
                    for out_node_id, in_node_id, edge_data in out_edges:
                        in_node_data = graph.nodes[in_node_id]
                        
                        # All resources in blocked branch
                        if in_node_data["node type"] == "resource" and in_node_id not in visited_nodes:
                            current_branch_resources.add(in_node_id)
                            visited_nodes.add(in_node_id)

                branch_resources[starting_node] += list(current_branch_resources)

                # Just go over resource nodes in branch and get unblocked ones (that would have been blocked b.c. ancestor)
                for rn in branch_resources[starting_node]:
                    if rn in unblocked_calculated:
                        continue
                    blocked = False
                    in_edges = graph.in_edges(nbunch=rn, data=True)
                    for out_node_id, in_node_id, edge_data in in_edges:
                        if edge_data['edge type'] == 'resource block':
                            blocked = True
                            break
                    if not blocked:
                        unblocked_calculated.add(rn)
                        blocked_bytes[BRANCH_BLOCKED] += get_blocked_bytes(graph, rn)

                num_branches[earliest_ancestor_type] += 1
                for node in branch_resources[starting_node]:
                    if node in calculated:
                        continue
                    blocked_bytes[earliest_ancestor_type] += get_blocked_bytes(graph, node)
                    calculated.add(node)


            #missed_blocked_resource_nodes = blocked_branch_resource_nodes - set(blocked_nodes)
            all_resource_nodes = set(hgraph.resource_nodes_no_data(graph))
            blocked_resource_nodes = set(hgraph.blocked_resources_no_data(graph, all_resource_nodes))

            remaining_blocked_bytes = [0, 0, 0, 0, 0] # (Not used), Ad, Tracker, Other, Ad_Tracker

            for bn in blocked_resource_nodes:
                if bn not in calculated:
                    isUnvisitedTrackerBlock = tracker_rules.should_block(graph.nodes[bn]['url'])
                    isUnvisitedAdBlock =  ad_rules.should_block(graph.nodes[bn]['url'])

                    unvisited_blocked_type = UNKNOWN
                    if isUnvisitedTrackerBlock and isUnvisitedAdBlock:
                        unvisited_blocked_type = AD_TRACKER
                    elif isUnvisitedTrackerBlock:
                        unvisited_blocked_type = TRACKER
                    elif isUnvisitedAdBlock:
                        unvisited_blocked_type = AD

                    remaining_blocked_bytes[unvisited_blocked_type] += get_blocked_bytes(graph, bn)
                    calculated.add(bn)

            # unblocked total bytes for sanity checking
            unblocked_resource_nodes = all_resource_nodes.difference(blocked_resource_nodes)
            for ub in unblocked_resource_nodes:
                if ub not in calculated:
                    blocked_bytes[UNBLOCKED] += get_blocked_bytes(graph, ub)
                    calculated.add(ub)

            # blocked_total_bytes will include those in and those not in branches
            # total_remaining_blocked_bytes are those that weren't in branches
            blocked_total_bytes = sum(blocked_bytes[1:5]) # Ad, Tracker, Other, Ad_Tracker
            total_remaining_blocked_bytes = sum(remaining_blocked_bytes)

            with open(SIZE_ANALYSIS_PATH + f'_{process_count}.txt', "a+", encoding="utf8") as f:
                f.write(url + "," + str(blocked_bytes).strip("[]") + "," + str(blocked_total_bytes) + ','
                        + str(remaining_blocked_total_bytes) + "\n")

            # Blocked resources not found in a branch
            with open(REMAINING_SIZE_ANALYSIS_PATH + f'_{process_count}.txt', "a+", encoding="utf8") as f:
                f.write(url + "," + str(remaining_blocked_tracker_and_ad_bytes) + "," + str(remaining_blocked_tracker_bytes) + "," + str(remaining_blocked_ad_bytes) + "," +    \
                        str(remaining_blocked_unknown_bytes) + ',' + str(remaining_blocked_total_bytes) + "\n")

            with open(DEPTHS_PATH + f'_{process_count}.txt', "a+", encoding="utf8") as f:
                f.write(url + "," + str(depths) + "\n")

            # Generate branches and first level off each branch
            for starting_node in unblocked_starting_nodes:
                if starting_node in visited_nodes:
                    continue # Skip node already in a branch
                
                # Generate branch of this starting node
                branches[starting_node] = [starting_node]
                visited_nodes.add(starting_node)
                while len(DFS_stack) != 0:
                    popped_list = DFS_stack.pop()
                    visited_nodes.add(popped_list[1])
                    visited_nodes.add(popped_list[2])
                    DFS(popped_list[0], popped_list[1], popped_list[2], visited_nodes, popped_list[4], popped_list[5])

                num_branches[UNBLOCKED] += 1

            with open(OUTPUT_PATH + f'_{process_count}.txt', "a+", encoding="utf8") as f:
                f.write(url + "," + str(num_branches).strip("[]") + "," + "\n")
    
        except Exception as err:
            # Save and print error and stack trace
            track = traceback.format_exc()
            with open(ERROR_PATH + f'_{process_count}.txt', "a+") as f:
                f.write('----------\n')
                f.write(path+'\n')
                f.write(str(err)+'\n')
                f.write(track+'\n')
            print("error in " + url)            
            print(track)
        num_done += 1
    
def main():
    ad_rules = get_rules(AD_PATHS)
    tracker_rules = get_rules(TRACKER_PATHS)
    graphml_paths = get_graphml_paths(GRAPHML_LIST_PATHS)
    
    # Begin multiprocessing
    processes = []
    for i in range(NUM_PROCESSES):
        # Split graphml files evenly among processes
        lower_bound = len(graphml_paths) * i // NUM_PROCESSES
        upper_bound = len(graphml_paths) * (i + 1) // NUM_PROCESSES

        # Start new process for compare_img_list()
        p = multiprocessing.Process(target=branch_analysis, args=[graphml_paths[lower_bound:upper_bound], ad_rules, tracker_rules, i])
        p.start()
        processes.append(p)

    # End multiprocessing
    for process in processes:
        process.join()
    
if __name__ == '__main__':
    main()
