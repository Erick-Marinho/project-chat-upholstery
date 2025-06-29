# app/application/agent/registry/edge_registry.py
import logging
from typing import Dict, Callable, List, Any

logger = logging.getLogger(__name__)

class EdgeRegistry:
    """
    Registry centralizado para arestas (edges) do LangGraph.
    """
    
    def __init__(self):
        self._edges: List[Dict[str, Any]] = []

    def add_edge(self, source: str, destination: str, **metadata):
        """
        Registra uma aresta simples (A -> B).

        Args:
            source (str): O nó de origem.
            destination (str): O nó de destino.
        """
        if not all([source, destination]):
            raise ValueError("Source e destination não podem ser vazios.")

        logger.info(f"Aresta simples registrada: '{source}' -> '{destination}'")
        self._edges.append({
            "type": "simple",
            "source": source,
            "destination": destination,
            **metadata
        })

    def register_conditional_edge(self, source: str, mapping: Dict[str, str], **metadata):
        """
        Decorator para registrar uma aresta condicional.
        A função decorada será a condição.

        Args:
            source (str): O nó de origem que dispara a condição.
            mapping (dict): Mapeamento de resultado -> nó de destino.
        """
        if not all([source, mapping]):
            raise ValueError("Source e mapping não podem ser vazios.")

        def decorator(condition_func: Callable):
            logger.info(f"✅ Aresta condicional registrada para '{source}' via '{condition_func.__name__}'")
            self._edges.append({
                "type": "conditional",
                "source": source,
                "condition": condition_func,
                "mapping": mapping,
                **metadata
            })
            return condition_func
        
        return decorator

    def get_edges(self) -> List[Dict[str, Any]]:
        """Retorna todas as arestas registradas."""
        return self._edges.copy()

# Instância global
edge_registry = EdgeRegistry()

# Atalhos para facilitar o uso
add_edge = edge_registry.add_edge
register_conditional_edge = edge_registry.register_conditional_edge