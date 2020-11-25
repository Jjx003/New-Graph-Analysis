import networkx
from networkx import MultiDiGraph
import os 
import json
import hgraph
import multiprocessing
from adblockparser import AdblockRules

FILTER_DIR = './filters/'
ERROR_LOG_DIR = './errors/'
PRIVACY_FILTER_FILES = ["easyprivacy_09_10_2020.txt", "ublockprivacy_08_29_2020.txt"]
AD_FILTER_FILES = ['easylist_09_10_2020.txt', 'ublockfilters_09_10_2020.txt']
PATHS_FILE = "/home/esiu/get_paths/paths_for_a2wu_09242020.txt"

BYTES_OUTPUT_DIR = './output'
NUM_PROCESSES = 8 # Modify according to your hardware capabilities


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
        current_dict['a'] = 0 # Ad Bytes
        current_dict['t'] = 0 # Tracker Bytes
        current_dict['o'] = 0 # "Other Bytes"

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
        # Extract resource nodes and blocked resource nodes
        resource_nodes = hgraph.resource_nodes_no_data(page_graph)
        blocked_resource_nodes = hgraph.blocked_resources_no_data(page_graph, resource_nodes)
        for blocked in blocked_resource_nodes:
            url = page_graph.nodes[blocked]['url']
            # Check if tracker (running this check first becasuse these files are smaller than ad filters)
            if tracker_rules.should_block(url):
                current_dict['t'] += get_blocked_bytes(page_graph, blocked)
            elif ad_rules.should_block(url):
                current_dict['a'] += get_blocked_bytes(page_graph, blocked)
            else:
                current_dict['o'] += get_blocked_bytes(page_graph, blocked)
                
            if tracker_rules.should_block(url) and ad_rules.should_block(url):
                trackers_and_ads_node_count += 1
                ad_node_count += 1
                tracker_node_count += 1
            elif  tracker_rules.should_block(url) :
                tracker_node_count += 1
            elif ad_rules.should_block(url):
                ad_node_count += 1
            else:
                others_node_count += 1
            total_blocked_node_count += 1
                
        
        website_url = page_graph_file_path.split("/")[-2]
        
        with open(BYTES_OUTPUT_DIR + f'/{process_count}.txt', "a+", encoding="utf8") as f:
            f.write(website_url + "," + str(current_dict['t']) + "," + str(current_dict['a']) + "," +    \
                    str(current_dict['o']) + "," + str(tracker_node_count) + ',' +             \
                    str(ad_node_count) +  "," + str(others_node_count) + "," +                             \
                    str(trackers_and_ads_node_count) + "," + str(total_blocked_node_count) + "\n")
        
        # website_name = page_graph_file_path.split('/')[-2]
        # website_dict[website_name] = current_dict

    # print("Saving all the information of ratios, sizes, and websites...")
    # with open(f'{BYTES_OUTPUT_DIR}/{process_count}.json', 'w') as jsonFile:
        # jsonFile.write(json.dumps(website_dict)) # Dump files



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
