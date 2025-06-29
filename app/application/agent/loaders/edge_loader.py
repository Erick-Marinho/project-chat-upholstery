# app/application/agent/loaders/edge_loader.py
import importlib
import pkgutil
from typing import List, Dict, Any
from app.application.agent import edges
from app.application.agent.registry.edge_registry import edge_registry
import logging

logger = logging.getLogger(__name__)

class EdgeLoader:
    """
    Carregador de arestas que utiliza o sistema de registry.
    """

    def __init__(self, packages: List = [edges]):
        self.packages = packages
        self._loaded = False

    def load_edges(self) -> List[Dict[str, Any]]:
        """
        Importa os módulos de arestas para ativar os registros,
        depois retorna as arestas do registry.
        """
        if self._loaded:
            return edge_registry.get_edges()

        logger.info("Iniciando descoberta e carregamento de arestas via registry...")

        for package in self.packages:
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if is_pkg:
                    module_path = f"{package.__name__}.{module_name}"
                    try:
                        importlib.import_module(module_path)
                        logger.debug(f"Pacote de aresta '{module_name}' importado.")
                    except ImportError as e:
                        logger.warning(f"Falha ao importar pacote de aresta '{module_path}': {e}")
        
        self._loaded = True
        loaded_edges = edge_registry.get_edges()
        
        logger.info(f"Carregamento finalizado. {len(loaded_edges)} arestas ativas encontradas.")
        return loaded_edges
