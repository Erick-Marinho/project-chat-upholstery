import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Adiciona o caminho do seu app para que o Alembic possa encontrar seus modelos
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# Importa a Base dos seus modelos e os próprios modelos para que o Alembic os "veja"
from app.infrastructure.database.database_session import Base, DATABASE_URL_SYNC
from app.domain import memory_models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Sobrescreve a URL do banco com a URL do seu projeto
config.set_main_option("sqlalchemy.url", DATABASE_URL_SYNC)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def include_name(name, type_, parent_names):
    """
    Filtro para o Alembic ignorar tabelas do LangGraph.
    
    Returns:
        True: Alembic deve gerenciar esta tabela
        False: Alembic deve ignorar esta tabela
    """
    if type_ == "table":
        # Lista de tabelas que o LangGraph gerencia
        langgraph_tables = {
            'checkpoints', 
            'checkpoint_writes', 
            'checkpoint_blobs',
            'store', 
            'store_migrations', 
            'checkpoint_migrations'
        }
        
        # Se é uma tabela do LangGraph, ignora
        if name in langgraph_tables:
            return False
    
    # Para todas as outras tabelas, permite que o Alembic gerencie
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_name=include_name
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
