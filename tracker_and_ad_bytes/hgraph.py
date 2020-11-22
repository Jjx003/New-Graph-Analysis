import os
import networkx as nx

def graph_files(directory):
    '''
    Returns a list of valid graphML files for given directory.
    Directory should contain folders that are titled by website.
    Within the folders, should be the graphML files
    Parameters:
        directory (String) - Location where crawl data is stored
    '''

    files = []

    for fname in os.listdir(directory):
        location = directory + fname

        # Make sure this is a directory
        if os.path.isdir(location):
            for item in os.listdir(location):
                if item.endswith('.graphml'):
                    files.append(location+'/'+item)
    
    return files

def read_graph(f):
    '''
    Parses input graphML file
    Parameters:
        f (String) - File location of graphML
    '''
    try:
        graph = nx.read_graphml(f, force_multigraph=True)
        return graph
    except:
        return None
    return None
    
def resource_nodes(graph):
    '''
    Retrives the resource nodes for a given graph
    Parameters:
        graph (Networkx Graph Object) - the graph
    Output:
        List of tupples of the form (node_id, data)
    '''
    nodes = []

    for node_id, data in graph.nodes(data=True):
        if data['node type'] == 'resource':
            nodes.append((node_id, data))
    
    return nodes

def blocked_resources(graph, nodes):
    '''
    Returns list of blocked nodes given list of (node_id, data)
    For use alongside resource_nodes() function.
    Parameters:
        graph (Networkx Graph Object) - graph
        nodes - Resource noeds extracted from graph
    Output:
        List of tupples of form (node_id, data)
    '''
    blocked_nodes = []

    for node_id, data in nodes:
        in_edges = graph.in_edges(nbunch=node_id, data=True)
        for out_node_id, in_node_id, edge_data in in_edges:
            if edge_data['edge type'] == 'resource block':
                blocked_nodes.append((node_id, data))
                break

    return blocked_nodes

def resource_nodes_no_data(graph):
    '''
    Retrives the resource nodes for a given graph
    Parameters:
        graph (Networkx Graph Object) - the graph
    Output:
        List of node_id
    '''
    nodes = []

    for node_id in graph.nodes():
        if graph.nodes[node_id]['node type'] == 'resource':
            nodes.append(node_id)
    
    return nodes

def blocked_resources_no_data(graph, nodes):
    '''
    Returns list of blocked nodes given list of node_id
    For use alongside resource_nodes() function.
    Parameters:
        graph (Networkx Graph Object) - graph
        nodes - Resource noeds extracted from graph
    Output:
        List of node_id
    '''
    blocked_nodes = []

    for node_id in nodes:
        in_edges = graph.in_edges(nbunch=node_id, data=True)
        for out_node_id, in_node_id, edge_data in in_edges:
            if edge_data['edge type'] == 'resource block':
                blocked_nodes.append(node_id)
                break

    return blocked_nodes

def find_script_node_from_dom(graph, dom_node_id):
    '''
    Returns scirpt corresponding to dom node, for use in the
    blocked_information() function
    '''
    dom_node_out_edges = graph.out_edges(nbunch=dom_node_id, data=True)
    for out_node_id, in_node_id, edge_data in dom_node_out_edges:
        if edge_data['edge type'] == 'execute':
            return (in_node_id, graph.nodes[in_node_id])
    return None

def blocked_information(graph, blocked_nodes):
    '''
    Provides more information on blocked nodes
    Parameters:
        graph (Networkx Grpah Object) - input graph
        blocked_nodes - List of (node_id, data) that is blocked
    Output:
        Tupple of the form (total_bytes, blocked_script_nodes, 
        blocked_request_compete_edges)
    '''
    blocked_request_complete_edges = []
    blocked_script_nodes = []

    for node_id, data in blocked_nodes:
        out_edges = graph.out_edges(nbunch=node_id, data=True)
        for out_node_id, in_node_id, edge_data in out_edges:
            if edge_data['edge type'] == 'request complete':
                blocked_request_complete_edges.append((out_node_id, \
                    in_node_id, edge_data))

                in_node_data = graph.nodes[in_node_id]
                if in_node_data['node type'] == 'HTML element' and \
                    in_node_data['tag name'] == 'script':
                
                    script_node = find_script_node_from_dom(graph, in_node_id)

                    if script_node is not None:
                        blocked_script_nodes.append(script_node)
    
    total_bytes = 0
    for node_id, initiator_id, edge_data in blocked_request_complete_edges:
        total_bytes += int(edge_data['value'])

    return (total_bytes, blocked_script_nodes, blocked_request_complete_edges)
