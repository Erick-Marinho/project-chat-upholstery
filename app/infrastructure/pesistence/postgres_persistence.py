import logging
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore
from app.infrastructure.config.config import settings

logger = logging.getLogger(__name__)

# URI PostgreSQL
def _get_database_host() -> str:
    """
    Detecta automaticamente o host do banco baseado no ambiente:
    - Se está rodando no Docker: usa 'db'
    - Se está rodando localmente: usa 'localhost'
    """
    import socket
    try:
        socket.gethostbyname('db')
        return 'db'  # Está dentro da rede Docker
    except socket.gaierror:
        return 'localhost'  # Está rodando localmente

DB_HOST = _get_database_host()

postgres_uri = (
    f"postgresql://"
    f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
    f"@{DB_HOST}:5432/{settings.POSTGRES_DB}"
)

class DatabaseManager:
    """
    Gerencia a conexão e a inicialização do banco de dados PostgreSQL,
    incluindo checkpointer e BaseStore do LangGraph.
    """
    _pool: AsyncConnectionPool = None
    _checkpointer: AsyncPostgresSaver = None
    _store: AsyncPostgresStore = None

    async def get_pool(self) -> AsyncConnectionPool:
        """Retorna o pool de conexões. Cria um se não existir."""
        if self._pool is None:
            logger.info("Criando novo pool de conexões com o PostgreSQL...")
            
            connection_kwargs = {
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            }
            
            self._pool = AsyncConnectionPool(
                conninfo=postgres_uri,
                max_size=20,
                kwargs=connection_kwargs
            )
            await self._pool.open()
            
        return self._pool

    async def initialize_database(self):
        """
        Orquestra a criação das tabelas do LangGraph (checkpoints + store).
        """
        logger.info("Iniciando a inicialização do banco de dados para o LangGraph...")
        await self._setup_langgraph_tables()
        await self._setup_store_tables()
        logger.info("Inicialização do banco de dados do LangGraph concluída.")

    async def _setup_langgraph_tables(self):
        """
        Configura as tabelas essenciais para o LangGraph (checkpoints).
        """
        try:
            pool = await self.get_pool()
            async with pool.connection() as conn:
                setup_checkpointer = AsyncPostgresSaver(conn)
                await setup_checkpointer.setup()
                
            logger.info("Tabelas do LangGraph (checkpoints) verificadas/criadas com sucesso.")
            logger.info("checkpoints")
            logger.info("checkpoint_writes")
            
        except Exception as e:
            logger.error(f"Erro no setup das tabelas do LangGraph: {e}")
            raise

    async def _setup_store_tables(self):
        """
        Configura as tabelas do BaseStore para dados auxiliares.
        """
        try:
            pool = await self.get_pool()
            async with pool.connection() as conn:
                setup_store = AsyncPostgresStore(conn)
                await setup_store.setup()
                
            logger.info("Tabelas do BaseStore verificadas/criadas com sucesso.")
            logger.info("BaseStore REAL ativado!")
            
        except Exception as e:
            logger.error(f"Erro no setup das tabelas do BaseStore: {e}")
            raise

    async def get_checkpointer(self) -> AsyncPostgresSaver:
        """
        Retorna a instância do checkpointer do LangGraph.
        """
        if self._checkpointer is None:
            logger.info("Instanciando o AsyncPostgresSaver para o checkpointer.")
            pool = await self.get_pool()
            self._checkpointer = AsyncPostgresSaver(pool)
        return self._checkpointer

    async def get_store(self) -> AsyncPostgresStore:
        """
        Retorna a instância do BaseStore do LangGraph.
        """
        if self._store is None:
            logger.info("Instanciando o AsyncPostgresStore para o BaseStore.")
            pool = await self.get_pool()
            self._store = AsyncPostgresStore(pool)
        return self._store

# Instância única (Singleton)
db_manager = DatabaseManager()

# Funções de fachada
async def get_checkpointer() -> AsyncPostgresSaver:
    return await db_manager.get_checkpointer()

async def get_store() -> AsyncPostgresStore:
    return await db_manager.get_store()