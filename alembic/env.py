from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool, text
from alembic import context
from app.models import figures_model

# Подключаем Base с MetaData(schema='auth')
from app.core.db import Base

# Alembic Config и URL
config = context.config
POSTGRES = {
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "password"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "db": os.getenv("POSTGRES_DB", "your_db"),
}
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql+psycopg2://{POSTGRES['user']}:{POSTGRES['password']}"
    f"@{POSTGRES['host']}:{POSTGRES['port']}/{POSTGRES['db']}"
)

# Logging
if config.config_file_name:
    fileConfig(config.config_file_name)

# Metadata вашей схемы
target_metadata = Base.metadata
SCHEMA = target_metadata.schema  # 'figure'

# Функция-фильтр: пропускаем только объекты из figure (и public по умолчанию)
def include_object(obj, name, type_, reflected, compare_to):
    schema = getattr(obj, 'schema', None)
    # Пропускаем только если это либо figure, либо без схемы (public)
    return schema in (None, SCHEMA)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,           # Inspector читает все, но фильтруем ниже.
        version_table_schema=SCHEMA,
        default_schema_name=SCHEMA,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as conn:
        context.configure(
            connection=conn,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=SCHEMA,
            default_schema_name=SCHEMA,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
