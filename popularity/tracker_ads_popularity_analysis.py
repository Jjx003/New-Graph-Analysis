# Adapted from tracker_byte_analysis.py

import networkx
from networkx import MultiDiGraph
import os 
import json
import hgraph
import multiprocessing
from adblockparser import AdblockRules

# (IMPORTANT) Constants need to be defined in the config file per server
from tracker_ads_popularity_analysis import *


# Read the blocking rules and utlize AdblockRules library to generate block checking
def get_rules(paths):
    """Generate rules from filter lists"""
    raw_rules = []
    for path in paths:
        with open(path, "r", encoding="utf8") as f:
            raw_rules += f.read().splitlines()
            
    return AdblockRules(raw_rules)

print("Load Rules")
tracker_rules = get_rules([FILTER_DIR + x for x in PRIVACY_FILTER_FILES])
ad_rules = get_rules([FILTER_DIR + x for x in AD_FILTER_FILES])
print("Rules Loaded!")

# The number of bytes used by a resource can be found within the edges
# of resource nodes. Here we sum up all the bytes for a given node.
def get_blocked_bytes(graph, node):
    total = 0
    resource_node_out_edges = graph.out_edges(nbunch=node, data=True)
    for _, _, edge_data in resource_node_out_edges:
        if edge_data['edge type'] == 'request complete':
            total += int(edge_data['value'])
    return total

# Main function to aggregate all data information into readable files
def analyze_size_impact(process_count, page_graph_files_paths):
    error_parsing = {} # Dictionary containing all files that failed to parse
    # website_dict = {} # Dictionary containing a [website] -> {byte dictionary}. (see current_dictionary)

	# For each graphml file
    count = 1
    total_count = len(page_graph_files_paths)
    
    for page_graph_file_path in page_graph_files_paths:
        print('On count:', count, " out of ", total_count)
        print('Reading page graph: ', page_graph_file_path)
        
        
        # count of trackers/ads/others ;  total count of nodes considered trackers and ads/others ; total count 
        tracker_node_count = 0
        ad_node_count = 0
        others_node_count = 0
        trackers_and_ads_node_count = 0
        total_blocked_node_count = 0
        

        current_dict = {}
        current_dict['t_a'] = 0 # Tracker and Ads Bytes
        current_dict['a'] = 0 # Ad Bytes
        current_dict['t'] = 0 # Tracker Bytes
        current_dict['o'] = 0 # "Other Bytes"

        tracker_urls = {}
        ads_urls = {}
        other_urls = {}



	    # Attempt to parse the graphml file
        page_graph = None
        try:
            page_graph = hgraph.read_graph(page_graph_file_path)
        except Exception as err:
           print("Error parsing file: ", page_graph_file_path)
           error_website_name = page_graph_file_path.split('/')[-2]
           error_parsing[error_website_name] = 1
           # Total Errors = #Lines / 3
           with open(f'{ERROR_LOG_DIR}/error_logs_{process_count}.txt', "a+") as f:
               f.write('----------\n')
               f.write(page_graph_file_path+'\n')
               f.write(str(err)+'\n')
               print("error in " + page_graph_file_path)     
               continue # Move onto next graph file, do not proceed

        count += 1 
        website_url = page_graph_file_path.split("/")[-2]

        # Extract resource nodes and blocked resource nodes
        resource_nodes = hgraph.resource_nodes_no_data(page_graph)
        blocked_resource_nodes = hgraph.blocked_resources_no_data(page_graph, resource_nodes)
        for blocked in blocked_resource_nodes:
            url = page_graph.nodes[blocked]['url']
            # Check if tracker (running this check first becasuse these files are smaller than ad filters)
            isResourceTracker = tracker_rules.should_block(url)
            isResourceAd = ad_rules.should_block(url)


            if isResourceTracker and isResourceAd:
                current_dict['t_a'] += get_blocked_bytes(page_graph, blocked)
                trackers_and_ads_node_count += 1
            elif isResourceTracker:
                current_dict['t'] += get_blocked_bytes(page_graph, blocked)
                tracker_node_count += 1
            elif isResourceAd:
                current_dict['a'] += get_blocked_bytes(page_graph, blocked)
                ad_node_count += 1
            else:
                current_dict['o'] += get_blocked_bytes(page_graph, blocked)
                others_node_count += 1

            total_blocked_node_count += 1


            # Create the ads and trackers url dicts
            if isResourceAd:

                # If the ad resource is not already accounted for:
                if url not in ads_urls:
                    ads_urls[url] = {}
                    ads_urls[url]["count"] = 0
                    ads_urls[url]["total_bytes"] = 0

                ads_urls[url]["count"] += 1
                ads_urls[url]["total_bytes"] += get_blocked_bytes(page_graph, blocked)
            elif isResourceTracker:
                
                # If the tracker resource is not already accounted for:
                if url not in tracker_urls:
                    tracker_urls[url] = {}
                    tracker_urls[url]["count"] = 0
                    tracker_urls[url]["total_bytes"] = 0

                tracker_urls[url]["count"] += 1
                tracker_urls[url]["total_bytes"] += get_blocked_bytes(page_graph, blocked)
            else:

                # If the tracker resource is not already accounted for:
                if url not in other_urls:
                    other_urls[url] = {}
                    other_urls[url]["count"] = 0
                    other_urls[url]["total_bytes"] = 0

                other_urls[url]["count"] += 1
                other_urls[url]["total_bytes"] += get_blocked_bytes(page_graph, blocked)

                
        
        
        with open(BYTES_OUTPUT_DIR + f'_{process_count}.txt', "a+", encoding="utf8") as f:
            f.write(website_url + "," + str(current_dict['t_a']) + "," + str(current_dict['t']) + "," + str(current_dict['a']) + "," +    \
                    str(current_dict['o']) + "\n")
        
        with open(NODES_OUTPUT_DIR + f'_{process_count}.txt', "a+", encoding="utf8") as f:
            f.write(website_url + "," + str(trackers_and_ads_node_count) + "," + str(tracker_node_count) + ',' + str(ad_node_count) +  "," + \
                    str(others_node_count) + "," + str(total_blocked_node_count) + "\n")

        with open(URLS_OUTPUT_DIR + f'_{process_count}.txt', "a+", encoding="utf8") as f:
            f.write(website_url + "$$" + json.dumps(tracker_urls) + "$$" + json.dumps(ads_urls) + "$$" + json.dumps(other_urls) + "\n")
        



if __name__ == '__main__':
        
    # TODO TODO TODO TODO: Explain this path and how to use the get paths script
    with open(PATHS_FILE, "r") as f:
        x = f.read()
        graphml_paths = eval(x)

    print('finished reading', len(graphml_paths))

    # Begin multiprocessing
    processes = []
    for i in range(NUM_PROCESSES):
	    # Split graphml files evenly among processes
        lower_bound = len(graphml_paths) * i // NUM_PROCESSES
        upper_bound = len(graphml_paths) * (i + 1) // NUM_PROCESSES
		
	    # Start new process for filter_list()
        p = multiprocessing.Process(target=analyze_size_impact, args=[i, graphml_paths[lower_bound:upper_bound]])
        p.start()
        processes.append(p)
    
	# Join threads
    for process in processes:
        process.join()
