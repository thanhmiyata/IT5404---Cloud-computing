import os
from psycopg2.pool import SimpleConnectionPool

_pool = None


def _get_dsn() -> str:
    return (
        f"dbname={os.getenv('DB_NAME')} "
        f"user={os.getenv('DB_USER')} "
        f"password={os.getenv('DB_PASSWORD')} "
        f"host={os.getenv('DB_HOST')} "
        f"port={os.getenv('DB_PORT', '5432')}"
    )


def init_pool(minconn: int = 1, maxconn: int = 5) -> None:
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(minconn=minconn, maxconn=maxconn, dsn=_get_dsn())


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


def get_conn():
    if _pool is None:
        init_pool()
    return _pool.getconn()


def put_conn(conn) -> None:
    if _pool is None:
        conn.close()
    else:
        _pool.putconn(conn)
