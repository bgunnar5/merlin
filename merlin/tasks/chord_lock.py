

"""

"""

import contextlib
import logging
import time
import uuid

import redis

from merlin.backends.redis.redis_backend import RedisBackend


LOG = logging.getLogger("merlin")


class DistributedLock:
    """
    A Redis-based distributed lock implementation for coordinating
    chord modifications across multiple Celery workers.
    """
    
    def __init__(
        self,
        chord_id: str,
        timeout: int = 5,
        retry_delay: float = 0.001, 
        blocking: bool = True,
        max_wait: int = 10,
    ):
        """
        Initialize the distributed lock.
        
        Args:
            chord_id: Unique chord ID to use for the lock
            timeout: Lock timeout in seconds
            retry_delay: Delay between lock acquisition attempts
            blocking: Whether to block until lock is acquired
            max_wait: Maximum time to wait for lock acquisition
        """
        self.redis_client: redis.Redis = RedisBackend().client
        self.key = f"chord_lock:{chord_id}"
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.blocking = blocking
        self.max_wait = max_wait
        self.lock_value = str(uuid.uuid4())
        self.acquired = False
    
    def acquire(self) -> bool:
        """
        Acquire the distributed lock.
            
        Returns:
            True if lock was acquired, False otherwise
        """
        if not self.redis_client:
            LOG.warning("Redis client not available, skipping distributed lock")
            return True
            
        start_time = time.time()
        current_delay = self.retry_delay
        
        while True:
            acquired = self.redis_client.set(
                self.key, 
                self.lock_value, 
                nx=True,
                ex=self.timeout
            )
            
            if acquired:
                self.acquired = True
                LOG.debug(f"Acquired lock: {self.key}")
                return True
                
            if not self.blocking:
                return False
                
            if time.time() - start_time > self.max_wait:
                LOG.warning(f"Lock timeout {self.key} after {self.max_wait}s")
                return False
            
            # Exponential backoff with jitter
            time.sleep(current_delay)
            current_delay = min(current_delay * 1.5, 0.1)  # Cap at 100ms
    
    def release(self) -> bool:
        """
        Release the distributed lock.
        
        Returns:
            True if lock was released, False otherwise
        """
        if not self.redis_client or not self.acquired:
            return True
            
        # Use Lua script to ensure atomic release (only release if we own the lock)
        lua_script = """
        if redis.call("GET", KEYS[1]) == ARGV[1] then
            return redis.call("DEL", KEYS[1])
        else
            return 0
        end
        """
        
        try:
            result = self.redis_client.eval(lua_script, 1, self.key, self.lock_value)
            if result:
                LOG.debug(f"Released distributed lock: {self.key}")
                self.acquired = False
                return True
            else:
                LOG.warning(f"Failed to release lock {self.key} - may have been acquired by another process")
                return False
        except Exception as e:
            LOG.error(f"Error releasing lock {self.key}: {e}")
            return False
    
    def __enter__(self):
        if not self.acquire():
            raise TimeoutError(f"Could not acquire lock: {self.key}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
