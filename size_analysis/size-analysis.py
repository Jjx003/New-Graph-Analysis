import networkx
from networkx import MultiDiGraph
import os 
import json
import hgraph
import multiprocessing


graphml_paths = []
resource_ratios = {}
low_blocked_size = {}
mid_blocked_size = {}
high_blocked_size = {}
low_blocked_ratio= {}
mid_blocked_ratio = {}
high_blocked_ratio = {}
error_parsing = {}
NUM_PROCESSES = 8

def analyze_size_impact(process_count, page_graph_files_paths):
	
	# Dictionaries required to save all the data
	resource_ratios = {}
	low_blocked_size = {}
	mid_blocked_size = {}
	high_blocked_size = {}
	low_blocked_ratio= {}
	mid_blocked_ratio = {}
	high_blocked_ratio = {}
	error_parsing = {}

	count = 1
	total_count = len(page_graph_files_paths)

	# For each graphml file
	for page_graph_file_path in page_graph_files_paths:
		print('On count:', count, " out of ", total_count)

		print('Reading page graph: ', page_graph_file_path)

		# Attempt to parse the graphml file
		try:
			page_graph = hgraph.read_graph(page_graph_file_path)
		except Exception as err:
			print("Error parsing file: ", page_graph_file_path)
			error_website_name = page_graph_file_path.split('/')[-2]
			error_parsing[error_website_name] = 1
			with open(f'/home/esiu/summer_size_analysis_10092020/error_logs_{process_count}.txt', "a+") as f:
				f.write('----------\n')
				f.write(page_graph_file_path+'\n')
				f.write(str(err)+'\n')
				print("error in " + page_graph_file_path)     
			continue
		
		# Find the resources in the file
		print('Finding resource nodes...')
		resource_nodes = hgraph.resource_nodes(page_graph)
		print(f'Found {len(resource_nodes)} resource node(s)')

		# Find the blocked resources in the file
		print('Finding blocked resource nodes...')
		blocked_resource_nodes = hgraph.blocked_resources(page_graph, resource_nodes)         
		print(f'Found {len(blocked_resource_nodes)} blocked resource node(s)')


		# Go to each blocked node and find the ones whose request completed (to measure size blocked) AND Sum the blocked size for each graphml file
		print('Tracing blocked resource nodes...')
		total_blocked_bytes, blocked_script_nodes, blocked_request_complete_edges = hgraph.blocked_information(page_graph, blocked_resource_nodes)
		print(f'Found {len(blocked_request_complete_edges)} blocked request complete edge(s)')
		print(f'Counted {total_blocked_bytes} blocked resource byte(s)')
		
		
		
		# Find the total size of resources (including non-blocked and blocked)
		request_complete_edges = []
		for resource_node_id, resource_node_data in resource_nodes:
			resource_node_out_edges = page_graph.out_edges(nbunch=resource_node_id, data=True)
			for out_node_id, in_node_id, edge_data in resource_node_out_edges:
				if edge_data['edge type'] == 'request complete':
					request_complete_edges.append((out_node_id, in_node_id, edge_data))
		print(f'Found {len(request_complete_edges)} request complete edge(s)')

		# Sum the total size of resources for each graphml file
		total_bytes = 0
		for resource_node_id, initiator_node_id, edge_data in request_complete_edges:
			total_bytes += int(edge_data['value'])
		print(f'Counted {total_bytes} total resource byte(s)')
		
		
		
		# calculate the ratio
		website_name = page_graph_file_path.split('/')[-2]
		if total_bytes == 0:
			ratio = 0
		else:
			ratio = total_blocked_bytes / total_bytes
		print(f'Blocked bytes over total resource bytes: ', ratio)
		
		
		# save the website in a dictionary with its ratio and total blocked bytes / total bytes
		resource_ratios[website_name] = {}
		resource_ratios[website_name]["ratio"] = ratio
		resource_ratios[website_name]["total_blocked_bytes"] = total_blocked_bytes
		resource_ratios[website_name]["total_bytes"] = total_bytes
		
		
		


		#1KB <= size <= 1MB
		if(resource_ratios[website_name]["total_blocked_bytes"] <= 1000000 and resource_ratios[website_name]["total_blocked_bytes"] >= 1000): 
			mid_blocked_size[website_name] = {}
			mid_blocked_size[website_name]["total_blocked_bytes"] = total_blocked_bytes
			mid_blocked_size[website_name]["ratio"] = ratio
			mid_blocked_size[website_name]["total_bytes"] = total_bytes
		
		#size > 1MB
		elif resource_ratios[website_name]["total_blocked_bytes"] > 1000000:
			high_blocked_size[website_name] = {}
			high_blocked_size[website_name]["total_blocked_bytes"] = total_blocked_bytes
			high_blocked_size[website_name]["ratio"] = ratio
			high_blocked_size[website_name]["total_bytes"] = total_bytes
		
		#size < 1KB
		else:
			low_blocked_size[website_name] = {}
			low_blocked_size[website_name]["total_blocked_bytes"] = total_blocked_bytes
			low_blocked_size[website_name]["ratio"] = ratio
			low_blocked_size[website_name]["total_bytes"] = total_bytes
		
		#0.3 <= ratio <= 0.8
		if(resource_ratios[website_name]["ratio"] <= 0.8 and resource_ratios[website_name]["ratio"] >= 0.3): 
			mid_blocked_ratio[website_name] = {}
			mid_blocked_ratio[website_name]["total_blocked_bytes"] = total_blocked_bytes
			mid_blocked_ratio[website_name]["ratio"] = ratio
			mid_blocked_ratio[website_name]["total_bytes"] = total_bytes
		
		#ratio > 0.8
		elif resource_ratios[website_name]["ratio"] > 0.8:
			high_blocked_ratio[website_name] = {}
			high_blocked_ratio[website_name]["total_blocked_bytes"] = total_blocked_bytes
			high_blocked_ratio[website_name]["ratio"] = ratio
			high_blocked_ratio[website_name]["total_bytes"] = total_bytes
		
		#0.3 > ratio
		else:
			low_blocked_ratio[website_name] = {}
			low_blocked_ratio[website_name]["total_blocked_bytes"] = total_blocked_bytes
			low_blocked_ratio[website_name]["ratio"] = ratio
			low_blocked_ratio[website_name]["total_bytes"] = total_bytes
		
		# increment count to see what number of graphml file we're on
		count += 1
	
	# Dump all the ratio and size info, also the error json file
	print("Saving all the information of ratios, sizes, and websites...")
	with open(f'/home/esiu/summer_size_analysis_10092020/resource_ratio_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(resource_ratios))
	with open(f'/home/esiu/summer_size_analysis_10092020/low_blocked_size_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(low_blocked_size))
	with open(f'/home/esiu/summer_size_analysis_10092020/mid_blocked_size_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(mid_blocked_size))
	with open(f'/home/esiu/summer_size_analysis_10092020/high_blocked_size_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(high_blocked_size))
	with open(f'/home/esiu/summer_size_analysis_10092020/low_blocked_ratio_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(low_blocked_ratio))
	with open(f'/home/esiu/summer_size_analysis_10092020/mid_blocked_ratio_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(mid_blocked_ratio))
	with open(f'/home/esiu/summer_size_analysis_10092020/high_blocked_ratio_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(high_blocked_ratio))
	with open(f'/home/esiu/summer_size_analysis_10092020/error_parsing_{process_count}.json', 'w') as jsonFile:
		jsonFile.write(json.dumps(error_parsing))

if __name__ == '__main__':

	# Obtain all the file paths for each graphml file
    #page_graph_files_paths = hgraph.graph_files('/home/a2wu/')

    # Instead of the above .graph_files, we will use a text file prepared
	with open("/home/esiu/get_paths/paths_for_a2wu_09242020.txt", "r") as f:
		x = f.read()
		graphml_paths = eval(x)
        
	with open("/home/esiu/get_paths/paths_for_esiu_09242020.txt", "r") as f:
		x = f.read()
		graphml_paths.extend(eval(x))
        
	with open("/home/esiu/get_paths/paths_for_jjx003_09242020.txt", "r") as f:
		x = f.read()
		graphml_paths.extend(eval(x))

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
    
	# End multiprocessing
	for process in processes:
		process.join()

	
