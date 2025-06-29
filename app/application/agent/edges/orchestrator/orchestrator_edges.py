from langgraph.graph import END
from app.application.agent.registry.edge_registry import add_edge

add_edge(source="ORCHESTRATOR", destination=END)
