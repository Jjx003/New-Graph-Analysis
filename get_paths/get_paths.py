import hgraph

cluster_graphs_dir = "/home/jjx003/Cluster-Crawler/cluster_graphs/"
output_dir = "paths_for_jjx003.txt"

graphml_paths = hgraph.graph_files(cluster_graphs_dir)
with open(output_dir, "w", encoding='utf8') as f:
    f.write(str(graphml_paths))
