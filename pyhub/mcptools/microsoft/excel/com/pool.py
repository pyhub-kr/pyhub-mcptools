"""
Excel instance pool for efficient resource management
"""
import time
import logging
import threading
import weakref
from typing import Optional, List, Dict, Any
from queue import Queue, Empty
from contextlib import contextmanager

import pythoncom
import win32com.client

from .decorators import ensure_com_thread, release_com_object

logger = logging.getLogger(__name__)


class ExcelInstance:
    """Wrapper for a pooled Excel instance"""

    def __init__(self, app: Any, instance_id: int):
        self.app = app
        self.instance_id = instance_id
        self.created_at = time.time()
        self.last_used = time.time()
        self.in_use = False
        self.error_count = 0

    def is_alive(self) -> bool:
        """Check if Excel instance is still responsive"""
        try:
            _ = self.app.Visible
            return True
        except:
            return False

    def mark_used(self):
        """Mark instance as recently used"""
        self.last_used = time.time()
        self.in_use = True

    def mark_free(self):
        """Mark instance as free"""
        self.in_use = False

    def mark_error(self):
        """Increment error count"""
        self.error_count += 1


class ExcelPool:
    """
    Pool manager for Excel COM instances

    Manages a pool of Excel instances to avoid the overhead of
    creating/destroying COM objects repeatedly.
    """

    def __init__(
        self,
        min_size: int = 1,
        max_size: int = 5,
        max_idle_time: int = 300,  # 5 minutes
        max_lifetime: int = 3600,   # 1 hour
        max_errors: int = 3
    ):
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.max_lifetime = max_lifetime
        self.max_errors = max_errors

        self._pool: Queue[ExcelInstance] = Queue()
        self._all_instances: Dict[int, ExcelInstance] = {}
        self._instance_counter = 0
        self._lock = threading.Lock()
        self._shutdown = False

        # Start maintenance thread
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True
        )
        self._maintenance_thread.start()

        # Pre-create minimum instances only if min_size > 0
        if self.min_size > 0:
            self._ensure_min_instances()

    @ensure_com_thread
    def _create_instance(self) -> Optional[ExcelInstance]:
        """Create a new Excel instance"""
        try:
            app = win32com.client.Dispatch("Excel.Application")
            app.Visible = False
            app.DisplayAlerts = False
            app.ScreenUpdating = False

            with self._lock:
                self._instance_counter += 1
                instance = ExcelInstance(app, self._instance_counter)
                self._all_instances[instance.instance_id] = instance

            logger.info(f"Created Excel instance {instance.instance_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create Excel instance: {e}")
            return None

    def _destroy_instance(self, instance: ExcelInstance):
        """Destroy an Excel instance"""
        try:
            if instance.app:
                try:
                    # Close all workbooks
                    for wb in instance.app.Workbooks:
                        wb.Close(SaveChanges=False)
                except:
                    pass

                # Quit Excel
                try:
                    instance.app.Quit()
                except:
                    pass

                # Release COM object
                release_com_object(instance.app)

            with self._lock:
                if instance.instance_id in self._all_instances:
                    del self._all_instances[instance.instance_id]

            logger.info(f"Destroyed Excel instance {instance.instance_id}")

        except Exception as e:
            logger.error(f"Error destroying Excel instance: {e}")

    def _ensure_min_instances(self):
        """Ensure minimum number of instances exist"""
        with self._lock:
            current_count = len(self._all_instances)

        for _ in range(self.min_size - current_count):
            instance = self._create_instance()
            if instance:
                self._pool.put(instance)

    def _maintenance_loop(self):
        """Maintenance thread to clean up old/broken instances"""
        while not self._shutdown:
            try:
                time.sleep(30)  # Check every 30 seconds

                current_time = time.time()
                instances_to_remove = []

                with self._lock:
                    for instance_id, instance in self._all_instances.items():
                        # Skip instances currently in use
                        if instance.in_use:
                            continue

                        # Check for various removal conditions
                        should_remove = False

                        # Too many errors
                        if instance.error_count >= self.max_errors:
                            logger.warning(f"Removing instance {instance_id}: too many errors")
                            should_remove = True

                        # Too old
                        elif current_time - instance.created_at > self.max_lifetime:
                            logger.info(f"Removing instance {instance_id}: exceeded lifetime")
                            should_remove = True

                        # Idle too long (but keep minimum instances)
                        elif (len(self._all_instances) > self.min_size and
                              current_time - instance.last_used > self.max_idle_time):
                            logger.info(f"Removing instance {instance_id}: idle timeout")
                            should_remove = True

                        # Not responsive
                        elif not instance.is_alive():
                            logger.warning(f"Removing instance {instance_id}: not responsive")
                            should_remove = True

                        if should_remove:
                            instances_to_remove.append(instance)

                # Remove marked instances
                for instance in instances_to_remove:
                    self._destroy_instance(instance)

                # Ensure minimum instances
                self._ensure_min_instances()

            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")

    @contextmanager
    def get_instance(self, timeout: float = 30.0):
        """
        Get an Excel instance from the pool

        Args:
            timeout: Maximum time to wait for an instance

        Yields:
            Excel COM application object
        """
        instance = None
        start_time = time.time()

        while instance is None and time.time() - start_time < timeout:
            try:
                # Try to get from pool
                instance = self._pool.get(timeout=1.0)

                # Validate instance
                if not instance.is_alive():
                    logger.warning(f"Got dead instance {instance.instance_id}, creating new one")
                    self._destroy_instance(instance)
                    instance = None
                    continue

            except Empty:
                # Pool is empty, try to create new instance if under limit
                with self._lock:
                    if len(self._all_instances) < self.max_size:
                        instance = self._create_instance()
                    else:
                        # Wait a bit and retry
                        time.sleep(0.1)

        if instance is None:
            raise TimeoutError(f"Could not get Excel instance within {timeout} seconds")

        instance.mark_used()

        try:
            yield instance.app
        except Exception as e:
            # Mark error on instance
            instance.mark_error()
            raise
        finally:
            # Return instance to pool
            instance.mark_free()
            if instance.error_count < self.max_errors and instance.is_alive():
                self._pool.put(instance)
            else:
                self._destroy_instance(instance)

    def shutdown(self):
        """Shutdown the pool and cleanup all instances"""
        logger.info("Shutting down Excel pool")
        self._shutdown = True

        # Destroy all instances
        with self._lock:
            instances = list(self._all_instances.values())

        for instance in instances:
            self._destroy_instance(instance)

        logger.info("Excel pool shutdown complete")


# Global pool instance
_excel_pool: Optional[ExcelPool] = None
_pool_lock = threading.Lock()


def get_excel_pool() -> ExcelPool:
    """Get or create the global Excel pool"""
    global _excel_pool

    if _excel_pool is None:
        with _pool_lock:
            if _excel_pool is None:
                _excel_pool = ExcelPool()

    return _excel_pool


def shutdown_excel_pool():
    """Shutdown the global Excel pool"""
    global _excel_pool

    if _excel_pool is not None:
        _excel_pool.shutdown()
        _excel_pool = None