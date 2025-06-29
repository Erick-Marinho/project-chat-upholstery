from langgraph.graph import StateGraph
from app.application.agent.state.sheduling_agent_state import SchedulingAgentState
from app.application.agent.loaders.node_loader import NodeLoader
from app.application.agent.loaders.edge_loader import EdgeLoader
from app.infrastructure.pesistence.postgres_persistence import get_checkpointer, get_store
from app.application.agent.registry.node_registry import node_registry
import logging

logger = logging.getLogger(__name__)

class SchedulingAgentBuilder:
    """
    Classe responsável por construir o agente de agendamento.
    """

    def __init__(self):
        """
        Inicializa o construtor do agente de agendamento.
        """
        self.agent_graph = StateGraph(SchedulingAgentState)
        self.node_loader = NodeLoader()
        self.edge_loader = EdgeLoader()

    async def build_agent(self):
        """
        Constrói e compila o agente de agendamento com checkpointer e store.
        """
        print("Construindo o grafo do agente...")
        self._add_nodes()
        self._add_edges()

        self.agent_graph.set_entry_point("ORCHESTRATOR")

        print("Compilando o grafo...")
        # Obter checkpointer e store
        checkpointer = await get_checkpointer()
        store = await get_store()
        
        return self.agent_graph.compile(
            checkpointer=checkpointer,
            store=store
        )

    def _add_nodes(self):
        """
        Carrega e adiciona nodes usando o sistema de registry.
        """
        nodes = self.node_loader.load_nodes()
        
        logger.info(f"Adicionando {len(nodes)} nós ativos ao grafo...")
        
        for name, function in nodes.items():
            self.agent_graph.add_node(name, function)
            metadata = node_registry.get_node_metadata(name)
            logger.info(f"  -> Nó '{name}' adicionado. (Prioridade: {metadata.get('priority', 0)}, Timeout: {metadata.get('timeout', 'N/A')})")

    def _add_edges(self):
        """Carrega e adiciona arestas usando o sistema de registry."""
        edge_definitions = self.edge_loader.load_edges()
        
        logger.info(f"Adicionando {len(edge_definitions)} definições de aresta ao grafo...")

        for edge_def in edge_definitions:
            source_node = edge_def.get("source")

            # Arestas condicionais
            if edge_def.get("type") == "conditional":
                self.agent_graph.add_conditional_edges(
                    source_node, 
                    edge_def["condition"], 
                    edge_def["mapping"]
                )
                destinations = ", ".join(edge_def["mapping"].values())
                condition_name = edge_def["condition"].__name__
                logger.info(f"  -> Aresta condicional '{source_node}' -> [{destinations}] via '{condition_name}' adicionada.")
            
            # Arestas simples
            elif edge_def.get("type") == "simple":
                destination = edge_def.get("destination")
                self.agent_graph.add_edge(source_node, destination)
                logger.info(f"  -> Aresta simples '{source_node}' -> '{destination}' adicionada.")

async def get_scheduling_agent():
    """
    Retorna o agente de agendamento compilado.
    """
    builder = SchedulingAgentBuilder()
    agent = await builder.build_agent()
    return agent
