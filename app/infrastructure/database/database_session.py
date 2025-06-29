from app.infrastructure.config.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Constrói a URL de conexão compatível com SQLAlchemy + asyncpg (para a aplicação)
DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
    f"@db:5432/{settings.POSTGRES_DB}"
)

# URL síncrona para o Alembic (usando psycopg2)
DATABASE_URL_SYNC = (
    f"postgresql+psycopg2://"
    f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
    f"@db:5432/{settings.POSTGRES_DB}"
)

# engine é o objeto que gerencia a conexão com o banco de dados
# Cria um motor de banco de dados assíncrono.
# O pool_pre_ping verifica as conexões antes de usá-las
engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

# AsyncSessionFactory é o objeto que cria sessões de banco de dados assíncronas.
# Cria uma fábrica de sessões assíncronas. 
# Cada instância desta classe será uma sessão de banco de dados.
AsyncSessionFactory = async_sessionmaker(
    engine,
    autoflush=False,
    expire_on_commit=False,
)

# Cria uma classe Base para nossos modelos ORM declarativos.
# Todos os nossos modelos de tabela herdarão desta classe.
Base = declarative_base()

async def get_async_session():
    """
    Função geradora que fornece uma sessão de banco de dados.
    Uso típico:
    
    async with get_async_session() as session:
        # usar session aqui
        pass
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()