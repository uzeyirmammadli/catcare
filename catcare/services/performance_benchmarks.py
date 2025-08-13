"""
Performance Benchmarks and Optimization Documentation for Advanced Media Processing.

This module provides comprehensive performance benchmarking tools and optimization
documentation for the media processing system.
"""

import asyncio
import logging
import os
import statistics
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable
from pathlib import Path

from PIL import Image
import psutil

from .media_processing_service import MediaProcessingService
from .async_processing_queue import get_processing_queue, TaskPriority
from .media_cache_service import get_cache_service
from .temp_file_manager import get_temp_file_manager
from .cdn_service import get_cdn_service


@dataclass
class BenchmarkResult:
    """Benchmark result data class."""
    test_name: str
    duration_seconds: float
    throughput_files_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success_rate: float
    error_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """System performance metrics data class."""
    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_mb: float
    network_io: Dict[str, int] = field(default_factory=dict)


class PerformanceBenchmarks:
    """Performance benchmarking and optimization analysis."""
    
    def __init__(self):
        """Initialize performance benchmarks."""
        self.logger = logging.getLogger(__name__)
        
        # Services
        self.media_service = MediaProcessingService()
        self.processing_queue = get_processing_queue()
        self.cache_service = get_cache_service()
        self.temp_manager = get_temp_file_manager()
        self.cdn_service = get_cdn_service()
        
        # Benchmark configuration
        self.benchmark_config = {
            'test_image_sizes': [
                (640, 480),    # VGA
                (1280, 720),   # HD
                (1920, 1080),  # Full HD
                (3840, 2160),  # 4K
            ],
            'test_file_sizes': [
                100 * 1024,      # 100KB
                1024 * 1024,     # 1MB
                5 * 1024 * 1024, # 5MB
                10 * 1024 * 1024 # 10MB
            ],
            'batch_sizes': [1, 5, 10, 20, 50],
            'quality_levels': [60, 75, 85, 95],
            'concurrent_levels': [1, 2, 4, 8]
        }
        
        # Results storage
        self.benchmark_results: List[BenchmarkResult] = []
        self.system_metrics_history: List[Tuple[datetime, SystemMetrics]] = []
        
        self.logger.info("PerformanceBenchmarks initialized")
    
    def run_comprehensive_benchmarks(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks.
        
        Returns:
            Dictionary containing all benchmark results and analysis
        """
        try:
            self.logger.info("Starting comprehensive performance benchmarks...")
            start_time = time.time()
            
            # Clear previous results
            self.benchmark_results.clear()
            self.system_metrics_history.clear()
            
            # Run individual benchmark suites
            results = {
                'single_file_processing': self.benchmark_single_file_processing(),
                'batch_processing': self.benchmark_batch_processing(),
                'compression_performance': self.benchmark_compression_performance(),
                'thumbnail_generation': self.benchmark_thumbnail_generation(),
                'cache_performance': self.benchmark_cache_performance(),
                'queue_performance': self.benchmark_queue_performance(),
                'memory_usage': self.benchmark_memory_usage(),
                'concurrent_processing': self.benchmark_concurrent_processing(),
                'system_metrics': self.collect_system_metrics(),
                'optimization_recommendations': self.generate_optimization_recommendations()
            }
            
            total_time = time.time() - start_time
            results['benchmark_summary'] = {
                'total_duration_seconds': total_time,
                'total_tests_run': len(self.benchmark_results),
                'average_success_rate': statistics.mean([r.success_rate for r in self.benchmark_results]) if self.benchmark_results else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Comprehensive benchmarks completed in {total_time:.2f} seconds")
            return results
            
        except Exception as e:
            self.logger.error(f"Comprehensive benchmarks failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_single_file_processing(self) -> Dict[str, Any]:
        """Benchmark single file processing performance."""
        try:
            self.logger.info("Running single file processing benchmarks...")
            results = {}
            
            for size in self.benchmark_config['test_image_sizes']:
                for quality in self.benchmark_config['quality_levels']:
                    test_name = f"single_file_{size[0]}x{size[1]}_q{quality}"
                    
                    # Create test image
                    test_image_path = self._create_test_image(size)
                    
                    try:
                        # Benchmark processing
                        start_time = time.time()
                        start_metrics = self._get_system_metrics()
                        
                        processed_media = self.media_service.process_uploaded_media(
                            test_image_path,
                            options={'quality': quality}
                        )
                        
                        end_time = time.time()
                        end_metrics = self._get_system_metrics()
                        
                        # Calculate metrics
                        duration = end_time - start_time
                        throughput = 1 / duration if duration > 0 else 0
                        memory_usage = end_metrics.memory_percent - start_metrics.memory_percent
                        success_rate = 1.0 if processed_media else 0.0
                        
                        benchmark_result = BenchmarkResult(
                            test_name=test_name,
                            duration_seconds=duration,
                            throughput_files_per_second=throughput,
                            memory_usage_mb=memory_usage,
                            cpu_usage_percent=end_metrics.cpu_percent,
                            success_rate=success_rate,
                            error_count=0 if processed_media else 1,
                            metadata={
                                'image_size': size,
                                'quality': quality,
                                'compression_ratio': processed_media.compression_ratio if processed_media else 0
                            }
                        )
                        
                        self.benchmark_results.append(benchmark_result)
                        results[test_name] = benchmark_result.__dict__
                        
                    finally:
                        # Clean up test file
                        if os.path.exists(test_image_path):
                            os.unlink(test_image_path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Single file processing benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_batch_processing(self) -> Dict[str, Any]:
        """Benchmark batch processing performance."""
        try:
            self.logger.info("Running batch processing benchmarks...")
            results = {}
            
            for batch_size in self.benchmark_config['batch_sizes']:
                test_name = f"batch_processing_{batch_size}_files"
                
                # Create test images
                test_images = []
                try:
                    for i in range(batch_size):
                        size = self.benchmark_config['test_image_sizes'][i % len(self.benchmark_config['test_image_sizes'])]
                        test_image_path = self._create_test_image(size, f"batch_test_{i}")
                        test_images.append(test_image_path)
                    
                    # Benchmark batch processing
                    start_time = time.time()
                    start_metrics = self._get_system_metrics()
                    
                    successful_files = 0
                    error_count = 0
                    
                    for image_path in test_images:
                        try:
                            processed_media = self.media_service.process_uploaded_media(
                                image_path,
                                options={'quality': 85}
                            )
                            if processed_media:
                                successful_files += 1
                            else:
                                error_count += 1
                        except Exception:
                            error_count += 1
                    
                    end_time = time.time()
                    end_metrics = self._get_system_metrics()
                    
                    # Calculate metrics
                    duration = end_time - start_time
                    throughput = batch_size / duration if duration > 0 else 0
                    memory_usage = end_metrics.memory_percent - start_metrics.memory_percent
                    success_rate = successful_files / batch_size if batch_size > 0 else 0
                    
                    benchmark_result = BenchmarkResult(
                        test_name=test_name,
                        duration_seconds=duration,
                        throughput_files_per_second=throughput,
                        memory_usage_mb=memory_usage,
                        cpu_usage_percent=end_metrics.cpu_percent,
                        success_rate=success_rate,
                        error_count=error_count,
                        metadata={
                            'batch_size': batch_size,
                            'successful_files': successful_files
                        }
                    )
                    
                    self.benchmark_results.append(benchmark_result)
                    results[test_name] = benchmark_result.__dict__
                    
                finally:
                    # Clean up test files
                    for image_path in test_images:
                        if os.path.exists(image_path):
                            os.unlink(image_path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Batch processing benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_compression_performance(self) -> Dict[str, Any]:
        """Benchmark compression performance across different settings."""
        try:
            self.logger.info("Running compression performance benchmarks...")
            results = {}
            
            test_image_path = self._create_test_image((1920, 1080), "compression_test")
            
            try:
                for quality in self.benchmark_config['quality_levels']:
                    test_name = f"compression_quality_{quality}"
                    
                    # Benchmark compression
                    start_time = time.time()
                    start_metrics = self._get_system_metrics()
                    
                    processed_media = self.media_service.process_uploaded_media(
                        test_image_path,
                        options={'quality': quality}
                    )
                    
                    end_time = time.time()
                    end_metrics = self._get_system_metrics()
                    
                    # Calculate metrics
                    duration = end_time - start_time
                    throughput = 1 / duration if duration > 0 else 0
                    memory_usage = end_metrics.memory_percent - start_metrics.memory_percent
                    success_rate = 1.0 if processed_media else 0.0
                    
                    benchmark_result = BenchmarkResult(
                        test_name=test_name,
                        duration_seconds=duration,
                        throughput_files_per_second=throughput,
                        memory_usage_mb=memory_usage,
                        cpu_usage_percent=end_metrics.cpu_percent,
                        success_rate=success_rate,
                        error_count=0 if processed_media else 1,
                        metadata={
                            'quality': quality,
                            'compression_ratio': processed_media.compression_ratio if processed_media else 0,
                            'original_size': processed_media.file_size_original if processed_media else 0,
                            'compressed_size': processed_media.file_size_processed if processed_media else 0
                        }
                    )
                    
                    self.benchmark_results.append(benchmark_result)
                    results[test_name] = benchmark_result.__dict__
                
            finally:
                if os.path.exists(test_image_path):
                    os.unlink(test_image_path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Compression performance benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_thumbnail_generation(self) -> Dict[str, Any]:
        """Benchmark thumbnail generation performance."""
        try:
            self.logger.info("Running thumbnail generation benchmarks...")
            results = {}
            
            test_image_path = self._create_test_image((3840, 2160), "thumbnail_test")
            
            try:
                thumbnail_sizes = [(150, 150), (300, 300), (600, 400)]
                
                for sizes in [thumbnail_sizes[:1], thumbnail_sizes[:2], thumbnail_sizes]:
                    test_name = f"thumbnails_{len(sizes)}_sizes"
                    
                    # Benchmark thumbnail generation
                    start_time = time.time()
                    start_metrics = self._get_system_metrics()
                    
                    try:
                        thumbnails = self.media_service.generate_thumbnails(
                            test_image_path,
                            {'thumbnail_sizes': sizes}
                        )
                        success_rate = 1.0 if thumbnails else 0.0
                        error_count = 0
                    except Exception:
                        thumbnails = []
                        success_rate = 0.0
                        error_count = 1
                    
                    end_time = time.time()
                    end_metrics = self._get_system_metrics()
                    
                    # Calculate metrics
                    duration = end_time - start_time
                    throughput = len(sizes) / duration if duration > 0 else 0
                    memory_usage = end_metrics.memory_percent - start_metrics.memory_percent
                    
                    benchmark_result = BenchmarkResult(
                        test_name=test_name,
                        duration_seconds=duration,
                        throughput_files_per_second=throughput,
                        memory_usage_mb=memory_usage,
                        cpu_usage_percent=end_metrics.cpu_percent,
                        success_rate=success_rate,
                        error_count=error_count,
                        metadata={
                            'thumbnail_count': len(sizes),
                            'generated_count': len(thumbnails) if thumbnails else 0
                        }
                    )
                    
                    self.benchmark_results.append(benchmark_result)
                    results[test_name] = benchmark_result.__dict__
                
            finally:
                if os.path.exists(test_image_path):
                    os.unlink(test_image_path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Thumbnail generation benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_cache_performance(self) -> Dict[str, Any]:
        """Benchmark cache performance."""
        try:
            self.logger.info("Running cache performance benchmarks...")
            results = {}
            
            test_image_path = self._create_test_image((1920, 1080), "cache_test")
            
            try:
                # Test cache miss (first access)
                start_time = time.time()
                thumbnail_path = self.cache_service.get_thumbnail(test_image_path, "300x300")
                cache_miss_time = time.time() - start_time
                
                # Test cache hit (second access)
                start_time = time.time()
                thumbnail_path_cached = self.cache_service.get_thumbnail(test_image_path, "300x300")
                cache_hit_time = time.time() - start_time
                
                # Calculate cache performance
                cache_speedup = cache_miss_time / cache_hit_time if cache_hit_time > 0 else 0
                
                results['cache_miss_time'] = cache_miss_time
                results['cache_hit_time'] = cache_hit_time
                results['cache_speedup'] = cache_speedup
                results['cache_stats'] = self.cache_service.get_cache_stats()
                
            finally:
                if os.path.exists(test_image_path):
                    os.unlink(test_image_path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Cache performance benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_queue_performance(self) -> Dict[str, Any]:
        """Benchmark async processing queue performance."""
        try:
            self.logger.info("Running queue performance benchmarks...")
            results = {}
            
            # Test different queue loads
            for task_count in [5, 10, 20]:
                test_name = f"queue_{task_count}_tasks"
                
                # Create test images
                test_images = []
                try:
                    for i in range(task_count):
                        test_image_path = self._create_test_image((1280, 720), f"queue_test_{i}")
                        test_images.append(test_image_path)
                    
                    # Submit tasks to queue
                    start_time = time.time()
                    task_ids = []
                    
                    for image_path in test_images:
                        task_id = self.processing_queue.submit_task(
                            'media_processing',
                            image_path,
                            {'quality': 85},
                            TaskPriority.NORMAL
                        )
                        task_ids.append(task_id)
                    
                    # Wait for completion
                    completed_tasks = 0
                    error_count = 0
                    
                    while completed_tasks + error_count < task_count:
                        time.sleep(0.1)
                        for task_id in task_ids:
                            status = self.processing_queue.get_task_status(task_id)
                            if status and status['status'] in ['completed', 'failed']:
                                if status['status'] == 'completed':
                                    completed_tasks += 1
                                else:
                                    error_count += 1
                                task_ids.remove(task_id)
                                break
                    
                    end_time = time.time()
                    
                    # Calculate metrics
                    duration = end_time - start_time
                    throughput = task_count / duration if duration > 0 else 0
                    success_rate = completed_tasks / task_count if task_count > 0 else 0
                    
                    results[test_name] = {
                        'duration_seconds': duration,
                        'throughput_tasks_per_second': throughput,
                        'success_rate': success_rate,
                        'completed_tasks': completed_tasks,
                        'error_count': error_count
                    }
                    
                finally:
                    # Clean up test files
                    for image_path in test_images:
                        if os.path.exists(image_path):
                            os.unlink(image_path)
            
            # Add queue statistics
            results['queue_stats'] = self.processing_queue.get_queue_stats()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Queue performance benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage patterns."""
        try:
            self.logger.info("Running memory usage benchmarks...")
            results = {}
            
            # Monitor memory during different operations
            memory_samples = []
            
            # Baseline memory
            baseline_memory = psutil.virtual_memory().percent
            memory_samples.append(('baseline', baseline_memory))
            
            # Memory during single file processing
            test_image_path = self._create_test_image((3840, 2160), "memory_test")
            try:
                memory_before = psutil.virtual_memory().percent
                processed_media = self.media_service.process_uploaded_media(
                    test_image_path,
                    options={'quality': 85}
                )
                memory_after = psutil.virtual_memory().percent
                memory_samples.append(('single_file_processing', memory_after - memory_before))
                
                # Memory during thumbnail generation
                memory_before = psutil.virtual_memory().percent
                thumbnails = self.media_service.generate_thumbnails(
                    test_image_path,
                    {'thumbnail_sizes': [(150, 150), (300, 300), (600, 400)]}
                )
                memory_after = psutil.virtual_memory().percent
                memory_samples.append(('thumbnail_generation', memory_after - memory_before))
                
            finally:
                if os.path.exists(test_image_path):
                    os.unlink(test_image_path)
            
            # Analyze memory patterns
            results['memory_samples'] = memory_samples
            results['peak_memory_usage'] = max(sample[1] for sample in memory_samples)
            results['average_memory_usage'] = statistics.mean(sample[1] for sample in memory_samples)
            results['memory_efficiency'] = {
                'baseline': baseline_memory,
                'peak_increase': max(sample[1] for sample in memory_samples if sample[0] != 'baseline'),
                'recommendations': self._generate_memory_recommendations(memory_samples)
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Memory usage benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def benchmark_concurrent_processing(self) -> Dict[str, Any]:
        """Benchmark concurrent processing performance."""
        try:
            self.logger.info("Running concurrent processing benchmarks...")
            results = {}
            
            for concurrent_level in self.benchmark_config['concurrent_levels']:
                test_name = f"concurrent_{concurrent_level}_threads"
                
                # Create test images
                test_images = []
                try:
                    for i in range(concurrent_level * 2):  # More files than threads
                        test_image_path = self._create_test_image((1920, 1080), f"concurrent_test_{i}")
                        test_images.append(test_image_path)
                    
                    # Benchmark concurrent processing
                    start_time = time.time()
                    start_metrics = self._get_system_metrics()
                    
                    successful_files = 0
                    error_count = 0
                    
                    with ThreadPoolExecutor(max_workers=concurrent_level) as executor:
                        future_to_file = {
                            executor.submit(
                                self.media_service.process_uploaded_media,
                                image_path,
                                {'quality': 85}
                            ): image_path
                            for image_path in test_images
                        }
                        
                        for future in as_completed(future_to_file):
                            try:
                                result = future.result()
                                if result:
                                    successful_files += 1
                                else:
                                    error_count += 1
                            except Exception:
                                error_count += 1
                    
                    end_time = time.time()
                    end_metrics = self._get_system_metrics()
                    
                    # Calculate metrics
                    duration = end_time - start_time
                    throughput = len(test_images) / duration if duration > 0 else 0
                    memory_usage = end_metrics.memory_percent - start_metrics.memory_percent
                    success_rate = successful_files / len(test_images) if test_images else 0
                    
                    results[test_name] = {
                        'duration_seconds': duration,
                        'throughput_files_per_second': throughput,
                        'memory_usage_mb': memory_usage,
                        'cpu_usage_percent': end_metrics.cpu_percent,
                        'success_rate': success_rate,
                        'successful_files': successful_files,
                        'error_count': error_count,
                        'concurrent_level': concurrent_level
                    }
                    
                finally:
                    # Clean up test files
                    for image_path in test_images:
                        if os.path.exists(image_path):
                            os.unlink(image_path)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Concurrent processing benchmark failed: {str(e)}")
            return {'error': str(e)}
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics."""
        try:
            metrics = self._get_system_metrics()
            
            return {
                'cpu_percent': metrics.cpu_percent,
                'memory_percent': metrics.memory_percent,
                'memory_available_mb': metrics.memory_available_mb,
                'disk_usage_percent': metrics.disk_usage_percent,
                'disk_free_mb': metrics.disk_free_mb,
                'network_io': metrics.network_io,
                'temp_file_stats': self.temp_manager.get_stats(),
                'cache_stats': self.cache_service.get_cache_stats(),
                'cdn_stats': self.cdn_service.get_performance_stats()
            }
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {str(e)}")
            return {'error': str(e)}
    
    def generate_optimization_recommendations(self) -> Dict[str, Any]:
        """Generate optimization recommendations based on benchmark results."""
        try:
            recommendations = {
                'performance': [],
                'memory': [],
                'storage': [],
                'configuration': []
            }
            
            # Analyze benchmark results
            if self.benchmark_results:
                avg_throughput = statistics.mean([r.throughput_files_per_second for r in self.benchmark_results])
                avg_memory_usage = statistics.mean([r.memory_usage_mb for r in self.benchmark_results])
                avg_success_rate = statistics.mean([r.success_rate for r in self.benchmark_results])
                
                # Performance recommendations
                if avg_throughput < 1.0:
                    recommendations['performance'].append(
                        "Low throughput detected. Consider increasing concurrent processing threads."
                    )
                
                if avg_success_rate < 0.95:
                    recommendations['performance'].append(
                        "Success rate below 95%. Review error handling and fallback mechanisms."
                    )
                
                # Memory recommendations
                if avg_memory_usage > 20:
                    recommendations['memory'].append(
                        "High memory usage detected. Consider implementing memory pooling or reducing batch sizes."
                    )
                
                # Configuration recommendations
                quality_results = [r for r in self.benchmark_results if 'quality' in r.metadata]
                if quality_results:
                    best_quality = max(quality_results, key=lambda x: x.throughput_files_per_second / x.memory_usage_mb)
                    recommendations['configuration'].append(
                        f"Optimal quality setting appears to be {best_quality.metadata.get('quality', 85)} "
                        f"for best throughput/memory ratio."
                    )
            
            # System-based recommendations
            system_metrics = self._get_system_metrics()
            
            if system_metrics.memory_percent > 80:
                recommendations['memory'].append(
                    "System memory usage is high. Consider reducing cache sizes or concurrent operations."
                )
            
            if system_metrics.cpu_percent > 90:
                recommendations['performance'].append(
                    "CPU usage is very high. Consider reducing concurrent processing or optimizing algorithms."
                )
            
            if system_metrics.disk_usage_percent > 90:
                recommendations['storage'].append(
                    "Disk usage is very high. Enable automatic cleanup and consider CDN integration."
                )
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Optimization recommendations generation failed: {str(e)}")
            return {'error': str(e)}
    
    def _create_test_image(self, size: Tuple[int, int], name: str = "test") -> str:
        """Create a test image for benchmarking."""
        try:
            # Create a test image with some content
            image = Image.new('RGB', size, color='red')
            
            # Add some patterns to make it more realistic
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            
            # Draw some shapes
            for i in range(0, size[0], 50):
                for j in range(0, size[1], 50):
                    color = (i % 255, j % 255, (i + j) % 255)
                    draw.rectangle([i, j, i + 25, j + 25], fill=color)
            
            # Save to temporary file
            temp_path = self.temp_manager.create_temp_file(
                suffix='.jpg',
                prefix=f'{name}_',
                purpose='benchmark_test'
            )
            
            image.save(temp_path, 'JPEG', quality=95)
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Test image creation failed: {str(e)}")
            raise
    
    def _get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get network I/O if available
            network_io = {}
            try:
                net_io = psutil.net_io_counters()
                network_io = {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv
                }
            except Exception:
                pass
            
            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_free_mb=disk.free / 1024 / 1024,
                network_io=network_io
            )
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {str(e)}")
            return SystemMetrics(0, 0, 0, 0, 0)
    
    def _generate_memory_recommendations(self, memory_samples: List[Tuple[str, float]]) -> List[str]:
        """Generate memory optimization recommendations."""
        recommendations = []
        
        peak_usage = max(sample[1] for sample in memory_samples)
        
        if peak_usage > 30:
            recommendations.append("Consider implementing memory pooling for large image operations")
        
        if peak_usage > 50:
            recommendations.append("High memory usage detected - consider processing smaller batches")
        
        # Check for memory leaks (increasing usage pattern)
        usage_values = [sample[1] for sample in memory_samples if sample[0] != 'baseline']
        if len(usage_values) > 2 and all(usage_values[i] <= usage_values[i+1] for i in range(len(usage_values)-1)):
            recommendations.append("Potential memory leak detected - review object cleanup")
        
        return recommendations
    
    def export_benchmark_report(self, output_path: str) -> bool:
        """Export comprehensive benchmark report."""
        try:
            import json
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'system_info': {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
                    'platform': os.name
                },
                'benchmark_results': [result.__dict__ for result in self.benchmark_results],
                'system_metrics_history': [
                    {
                        'timestamp': timestamp.isoformat(),
                        'metrics': metrics.__dict__
                    }
                    for timestamp, metrics in self.system_metrics_history
                ],
                'optimization_recommendations': self.generate_optimization_recommendations()
            }
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            self.logger.info(f"Benchmark report exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Benchmark report export failed: {str(e)}")
            return False


# Global benchmarks instance
_performance_benchmarks: Optional[PerformanceBenchmarks] = None


def get_performance_benchmarks() -> PerformanceBenchmarks:
    """Get the global performance benchmarks instance.
    
    Returns:
        PerformanceBenchmarks instance
    """
    global _performance_benchmarks
    if _performance_benchmarks is None:
        _performance_benchmarks = PerformanceBenchmarks()
    return _performance_benchmarks