from app.graph.loader import load_graph

G, G_proj = load_graph()
print(len(G.nodes), len(G.edges))
print(len(G_proj.nodes), len(G_proj.edges))
