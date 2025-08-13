"""
Async Processing Queue for server-side media processing operations.

This service provides asynchronous processing capabilities for media files,
allowing for non-blocking operations and better resource management.
"""

import asyncio
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, Empty
from typing import Dict, Any, List, Optional, Callable, Union
from threading import Lock, Event


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ProcessingTask:
    """Data class for processing tasks."""
    id: str
    task_type: str
    file_path: str
    options: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class QueueStats:
    """Queue statistics data class."""
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_processing_time: float = 0.0
    queue_throughput: float = 0.0  # tasks per minute
    worker_utilization: float = 0.0


class AsyncProcessingQueue:
    """Async processing queue for media processing operations."""
    
    def __init__(self, max_workers: int = 4, max_queue_size: int = 1000):
        """Initialize the async processing queue.
        
        Args:
            max_workers: Maximum number of worker threads
            max_queue_size: Maximum queue size
        """
        self.logger = logging.getLogger(__name__)
        
        # Queue configuration
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        
        # Task management
        self.tasks: Dict[str, ProcessingTask] = {}
        self.task_queue = Queue(maxsize=max_queue_size)
        self.tasks_lock = Lock()
        
        # Worker management
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.workers_running = False
        self.shutdown_event = Event()
        
        # Statistics
        self.stats = QueueStats()
        self.stats_lock = Lock()
        self.processing_times: List[float] = []
        self.last_stats_update = datetime.now()
        
        # Task cleanup
        self.cleanup_interval = timedelta(hours=24)  # Clean up completed tasks after 24 hours
        self.last_cleanup = datetime.now()
        
        # Start worker threads
        self._start_workers()
        
        self.logger.info(f"AsyncProcessingQueue initialized with {max_workers} workers")
    
    def submit_task(self, task_type: str, file_path: str, options: Dict[str, Any],
                   priority: TaskPriority = TaskPriority.NORMAL,
                   callback: Optional[Callable] = None) -> str:
        """Submit a task to the processing queue.
        
        Args:
            task_type: Type of processing task
            file_path: Path to file to process
            options: Processing options
            priority: Task priority
            callback: Optional callback function
            
        Returns:
            Task ID for tracking
            
        Raises:
            RuntimeError: If queue is full or shutting down
        """
        if self.shutdown_event.is_set():
            raise RuntimeError("Queue is shutting down")
        
        if self.task_queue.qsize() >= self.max_queue_size:
            raise RuntimeError("Queue is full")
        
        # Create task
        task_id = str(uuid.uuid4())
        task = ProcessingTask(
            id=task_id,
            task_type=task_type,
            file_path=file_path,
            options=options,
            priority=priority,
            callback=callback
        )
        
        # Add to task tracking
        with self.tasks_lock:
            self.tasks[task_id] = task
        
        # Add to queue (priority queue simulation)
        self.task_queue.put((priority.value, task))
        
        # Update statistics
        with self.stats_lock:
            self.stats.total_tasks += 1
            self.stats.pending_tasks += 1
        
        self.logger.info(f"Task {task_id} ({task_type}) submitted with priority {priority.name}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status dictionary or None if not found
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            
            return {
                'id': task.id,
                'task_type': task.task_type,
                'status': task.status.value,
                'progress': task.progress,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'processing_time': (
                    (task.completed_at - task.started_at).total_seconds()
                    if task.started_at and task.completed_at else None
                ),
                'error': task.error,
                'retry_count': task.retry_count,
                'result': task.result
            }
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False otherwise
        """
        with self.tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.now()
                self.logger.info(f"Task {task_id} cancelled")
                return True
            
            return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics.
        
        Returns:
            Dictionary containing queue statistics
        """
        self._update_stats()
        
        with self.stats_lock:
            return {
                'total_tasks': self.stats.total_tasks,
                'pending_tasks': self.stats.pending_tasks,
                'running_tasks': self.stats.running_tasks,
                'completed_tasks': self.stats.completed_tasks,
                'failed_tasks': self.stats.failed_tasks,
                'average_processing_time': self.stats.average_processing_time,
                'queue_throughput': self.stats.queue_throughput,
                'worker_utilization': self.stats.worker_utilization,
                'queue_size': self.task_queue.qsize(),
                'max_workers': self.max_workers,
                'active_workers': len([t for t in self.tasks.values() if t.status == TaskStatus.RUNNING])
            }
    
    def get_pending_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get list of pending tasks.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending task dictionaries
        """
        with self.tasks_lock:
            pending_tasks = [
                {
                    'id': task.id,
                    'task_type': task.task_type,
                    'priority': task.priority.name,
                    'created_at': task.created_at.isoformat(),
                    'file_path': task.file_path
                }
                for task in self.tasks.values()
                if task.status == TaskStatus.PENDING
            ]
            
            # Sort by priority and creation time
            pending_tasks.sort(key=lambda x: (x['priority'], x['created_at']), reverse=True)
            return pending_tasks[:limit]
    
    def clear_completed_tasks(self, older_than: Optional[timedelta] = None) -> int:
        """Clear completed tasks from memory.
        
        Args:
            older_than: Only clear tasks older than this duration
            
        Returns:
            Number of tasks cleared
        """
        if older_than is None:
            older_than = self.cleanup_interval
        
        cutoff_time = datetime.now() - older_than
        cleared_count = 0
        
        with self.tasks_lock:
            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.completed_at and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                cleared_count += 1
        
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} completed tasks")
        
        return cleared_count
    
    def shutdown(self, wait: bool = True, timeout: float = 30.0) -> None:
        """Shutdown the processing queue.
        
        Args:
            wait: Whether to wait for running tasks to complete
            timeout: Maximum time to wait for shutdown
        """
        self.logger.info("Shutting down AsyncProcessingQueue...")
        
        # Signal shutdown
        self.shutdown_event.set()
        self.workers_running = False
        
        if wait:
            # Wait for executor to finish
            self.executor.shutdown(wait=True, timeout=timeout)
        else:
            # Force shutdown
            self.executor.shutdown(wait=False)
        
        self.logger.info("AsyncProcessingQueue shutdown complete")
    
    def _start_workers(self) -> None:
        """Start worker threads."""
        self.workers_running = True
        
        # Start worker threads
        for i in range(self.max_workers):
            self.executor.submit(self._worker_thread, i)
        
        # Start cleanup thread
        self.executor.submit(self._cleanup_thread)
        
        self.logger.info(f"Started {self.max_workers} worker threads")
    
    def _worker_thread(self, worker_id: int) -> None:
        """Worker thread main loop.
        
        Args:
            worker_id: Worker identifier
        """
        self.logger.debug(f"Worker {worker_id} started")
        
        while self.workers_running and not self.shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                try:
                    priority, task = self.task_queue.get(timeout=1.0)
                except Empty:
                    continue
                
                # Skip cancelled tasks
                if task.status == TaskStatus.CANCELLED:
                    self.task_queue.task_done()
                    continue
                
                # Process task
                self._process_task(task, worker_id)
                self.task_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {str(e)}")
        
        self.logger.debug(f"Worker {worker_id} stopped")
    
    def _process_task(self, task: ProcessingTask, worker_id: int) -> None:
        """Process a single task.
        
        Args:
            task: Task to process
            worker_id: Worker identifier
        """
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            
            # Update statistics
            with self.stats_lock:
                self.stats.pending_tasks -= 1
                self.stats.running_tasks += 1
            
            self.logger.info(f"Worker {worker_id} processing task {task.id} ({task.task_type})")
            
            # Import here to avoid circular imports
            from .media_processing_service import MediaProcessingService
            
            # Create processing service instance
            processing_service = MediaProcessingService()
            
            # Process based on task type
            if task.task_type == 'media_processing':
                result = processing_service.process_uploaded_media(
                    task.file_path,
                    original_filename=task.options.get('original_filename'),
                    options=task.options
                )
                task.result = result.__dict__ if result else None
                
            elif task.task_type == 'thumbnail_generation':
                result = processing_service.generate_thumbnails(
                    task.file_path,
                    task.options
                )
                task.result = [thumb.__dict__ for thumb in result] if result else []
                
            elif task.task_type == 'format_conversion':
                result = processing_service.convert_format(
                    task.file_path,
                    task.options.get('target_format', 'JPEG'),
                    task.options
                )
                task.result = result
                
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            
            # Update statistics
            processing_time = (task.completed_at - task.started_at).total_seconds()
            with self.stats_lock:
                self.stats.running_tasks -= 1
                self.stats.completed_tasks += 1
                self.processing_times.append(processing_time)
                
                # Keep only recent processing times for average calculation
                if len(self.processing_times) > 1000:
                    self.processing_times = self.processing_times[-500:]
            
            # Execute callback if provided
            if task.callback:
                try:
                    task.callback(task)
                except Exception as e:
                    self.logger.warning(f"Task callback failed: {str(e)}")
            
            self.logger.info(f"Task {task.id} completed in {processing_time:.2f}s")
            
        except Exception as e:
            # Handle task failure
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            
            # Update statistics
            with self.stats_lock:
                self.stats.running_tasks -= 1
                self.stats.failed_tasks += 1
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                
                # Re-queue with lower priority
                retry_priority = TaskPriority(max(1, task.priority.value - 1))
                self.task_queue.put((retry_priority.value, task))
                
                with self.stats_lock:
                    self.stats.failed_tasks -= 1
                    self.stats.pending_tasks += 1
                
                self.logger.warning(f"Task {task.id} failed, retrying ({task.retry_count}/{task.max_retries}): {str(e)}")
            else:
                self.logger.error(f"Task {task.id} failed permanently after {task.retry_count} retries: {str(e)}")
    
    def _cleanup_thread(self) -> None:
        """Background thread for periodic cleanup."""
        self.logger.debug("Cleanup thread started")
        
        while self.workers_running and not self.shutdown_event.is_set():
            try:
                # Sleep for cleanup interval
                if self.shutdown_event.wait(timeout=3600):  # 1 hour
                    break
                
                # Perform cleanup
                if datetime.now() - self.last_cleanup > self.cleanup_interval:
                    self.clear_completed_tasks()
                    self.last_cleanup = datetime.now()
                
            except Exception as e:
                self.logger.error(f"Cleanup thread error: {str(e)}")
        
        self.logger.debug("Cleanup thread stopped")
    
    def _update_stats(self) -> None:
        """Update queue statistics."""
        now = datetime.now()
        
        with self.stats_lock:
            # Update task counts
            with self.tasks_lock:
                self.stats.pending_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)
                self.stats.running_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING)
                self.stats.completed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
                self.stats.failed_tasks = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
            
            # Calculate average processing time
            if self.processing_times:
                self.stats.average_processing_time = sum(self.processing_times) / len(self.processing_times)
            
            # Calculate throughput (tasks per minute)
            time_diff = (now - self.last_stats_update).total_seconds()
            if time_diff > 0:
                completed_since_last = len([t for t in self.tasks.values() 
                                          if t.status == TaskStatus.COMPLETED and 
                                          t.completed_at and t.completed_at > self.last_stats_update])
                self.stats.queue_throughput = (completed_since_last / time_diff) * 60
            
            # Calculate worker utilization
            if self.max_workers > 0:
                self.stats.worker_utilization = (self.stats.running_tasks / self.max_workers) * 100
            
            self.last_stats_update = now


# Global queue instance
_processing_queue: Optional[AsyncProcessingQueue] = None


def get_processing_queue() -> AsyncProcessingQueue:
    """Get the global processing queue instance.
    
    Returns:
        AsyncProcessingQueue instance
    """
    global _processing_queue
    if _processing_queue is None:
        _processing_queue = AsyncProcessingQueue()
    return _processing_queue


def shutdown_processing_queue() -> None:
    """Shutdown the global processing queue."""
    global _processing_queue
    if _processing_queue is not None:
        _processing_queue.shutdown()
        _processing_queue = None