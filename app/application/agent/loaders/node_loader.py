# app/application/agent/loaders/node_loader.py
import importlib
import pkgutil
from typing import Dict, Callable, List
from app.application.agent import node
from app.application.agent.registry.node_registry import node_registry
import logging

logger = logging.getLogger(__name__)

class NodeLoader:
    """
    Carregador de nós que utiliza o sistema de registry com controle explícito.
    """

    def __init__(self, packages: List = [node]):
        self.packages = packages
        self._loaded = False

    def load_nodes(self) -> Dict[str, Callable]:
        """
        Importa os módulos de nós para ativar os decoradores,
        depois retorna os nodes registrados no registry.
        """
        if self._loaded:
            return node_registry.get_nodes()

        logger.info("🔍 Iniciando descoberta e carregamento de nós via registry...")
        
        # Força a importação dos __init__.py das pastas de nós
        for package in self.packages:
            self._import_node_packages(package)
        
        self._loaded = True
        nodes = node_registry.get_nodes()
        
        logger.info(f"Carregamento finalizado. {len(nodes)} nós ativos encontrados no registry.")
        
        return nodes

    def _import_node_packages(self, package):
        """
        Importa recursivamente os __init__.py de cada pasta de node.
        Isso força a execução dos decoradores nos nodes ativos.
        """
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            if is_pkg:  # É uma pasta de node (ex: 'orchestrator')
                module_path = f"{package.__name__}.{module_name}"
                try:
                    # Importa o __init__.py da pasta do node.
                    # Isso é o suficiente para ativar o registro.
                    importlib.import_module(module_path)
                    logger.debug(f"Pacote de node '{module_name}' importado com sucesso.")
                except ImportError as e:
                    logger.warning(f"Falha ao importar pacote de node '{module_path}': {e}")

    def get_registry_info(self) -> Dict:
        """Retorna informações do registry para debugging."""
        return {
            "loaded": self._loaded,
            "active_nodes": len(node_registry.get_nodes()),
            "nodes_detail": node_registry.list_nodes()
        }