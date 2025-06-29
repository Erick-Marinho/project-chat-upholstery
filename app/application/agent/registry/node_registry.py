import logging
from typing import Dict, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

class NodeRegistry:
    """
    Registry centralizado para nodes do langgraph com controle explícito
    """

    def __init__(self):
        self._nodes: Dict[str, Callable] = {}
        self._metadatas: Dict[str, Dict[str, Any]] = {}

    def register_node(
            self,
            name: str,
            enabled: bool = True,
            timeout: int = 0,
            priority: int = 0,
            **metadata
    ):
        """
        decorator para registrar nodes no grafo
        """
        def decorator(func: Callable):
            if not enabled:
                logger.warning(f"Node {name} desabilitado. Ignorando registro.")
                return func
            
            if name in self._nodes:
                raise ValueError(f"Node {name} já registrado.")
            
            self._nodes[name] = func
            self._metadatas[name] = {
                'timeout': timeout,
                'priority': priority,
                'enabled': enabled,
                'description': metadata.get('description', func.__doc__ or "No description"),
            }

            logger.info(f"Node {name} registrado com sucesso.")

            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            return wrapper
    
        return decorator
    
    def get_nodes(self) -> Dict[str, Callable]:
        """
        Retorna todos os nodes registrados e Ativos
        """

        return self._nodes.copy()

    def get_node_metadata(self, name: str) -> Dict[str, Any]:
        """
        Retorna os metadados de um node específico
        """
        return self._metadatas.get(name, {})

    def list_nodes(self) -> Dict[str, Dict[str, Any]]:
        """
        Lista todos os nodes com seus metadados (debugging)
        """
        
        return self._metadatas.copy()

# Instância global (Singleton)    
node_registry = NodeRegistry()

# Decorator para registrar nodes
register_node = node_registry.register_node
