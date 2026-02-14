"""
Database connection management with pooling and retry logic.
"""

import time
import logging
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
from psycopg2 import pool, OperationalError, DatabaseError
from psycopg2.extensions import connection as PgConnection

from .config import get_settings, MAX_RETRIES, RETRY_BACKOFF_FACTOR

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    Manages PostgreSQL connection pool with retry logic.
    Implements singleton pattern for connection pooling.
    """
    
    _instance: Optional['DatabaseConnectionPool'] = None
    _pool: Optional[pool.SimpleConnectionPool] = None
    
    def __new__(cls) -> 'DatabaseConnectionPool':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize connection pool if not already initialized."""
        if self._pool is None:
            settings = get_settings()
            db_config = settings.database
            
            try:
                self._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=db_config.pool_size + db_config.max_overflow,
                    host=db_config.host,
                    port=db_config.port,
                    database=db_config.name,
                    user=db_config.user,
                    password=db_config.password,
                )
                logger.info(f"Database connection pool initialized (max: {db_config.pool_size + db_config.max_overflow})")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
    
    def get_connection(self) -> PgConnection:
        """
        Get a connection from the pool.
        
        Returns:
            Database connection
            
        Raises:
            OperationalError: If unable to get connection
        """
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            conn = self._pool.getconn()
            logger.debug("Connection acquired from pool")
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def return_connection(self, conn: PgConnection) -> None:
        """
        Return a connection to the pool.
        
        Args:
            conn: Database connection to return
        """
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            self._pool.putconn(conn)
            logger.debug("Connection returned to pool")
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        if self._pool is not None:
            self._pool.closeall()
            logger.info("All database connections closed")


@contextmanager
def get_db_connection(auto_commit: bool = True) -> Generator[PgConnection, None, None]:
    """
    Context manager for database connections with automatic cleanup.
    
    Args:
        auto_commit: Whether to auto-commit transactions
        
    Yields:
        Database connection
        
    Example:
        >>> with get_db_connection() as conn:
        ...     cursor = conn.cursor()
        ...     cursor.execute("SELECT * FROM table")
    """
    pool_manager = DatabaseConnectionPool()
    conn = None
    
    try:
        conn = pool_manager.get_connection()
        conn.autocommit = auto_commit
        yield conn
    except Exception as e:
        if conn and not auto_commit:
            conn.rollback()
            logger.warning("Transaction rolled back due to error")
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            pool_manager.return_connection(conn)


def get_connection_with_retry(max_retries: int = MAX_RETRIES) -> PgConnection:
    """
    Get database connection with exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Returns:
        Database connection
        
    Raises:
        OperationalError: If unable to connect after all retries
    """
    settings = get_settings()
    db_config = settings.database
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.name,
                user=db_config.user,
                password=db_config.password,
            )
            logger.info("Database connection established")
            return conn
        except OperationalError as e:
            wait_time = RETRY_BACKOFF_FACTOR ** attempt
            logger.warning(
                f"Connection attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {wait_time}s..."
            )
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached. Unable to connect to database.")
                raise


def test_connection() -> bool:
    """
    Test database connectivity.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    logger.info("Database connection test successful")
                    return True
        return False
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def execute_with_retry(
    query: str,
    params: Optional[tuple] = None,
    max_retries: int = MAX_RETRIES
) -> list:
    """
    Execute query with retry logic for transient failures.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        max_retries: Maximum retry attempts
        
    Returns:
        Query results
        
    Raises:
        DatabaseError: If query fails after all retries
    """
    for attempt in range(max_retries):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    if cursor.description:  # SELECT query
                        return cursor.fetchall()
                    return []
        except (OperationalError, DatabaseError) as e:
            wait_time = RETRY_BACKOFF_FACTOR ** attempt
            logger.warning(
                f"Query attempt {attempt + 1}/{max_retries} failed: {e}. "
                f"Retrying in {wait_time}s..."
            )
            if attempt < max_retries - 1:
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached for query execution")
                raise
