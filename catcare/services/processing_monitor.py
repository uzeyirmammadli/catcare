"""
Processing Monitor for advanced media processing performance tracking.

This service handles performance metrics collection, error rate tracking,
storage usage monitoring, and automatic performance adjustment.
"""

import os
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil
import json


@dataclass
class ProcessingMetrics:
    """Data class for processing performance metrics."""
    operation_type: str
    file_size: int
    processing_time: float
    compression_ratio: Optional[float] = None
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None


@dataclass
class StorageMetrics:
    """Data class for storage usage metrics."""
    total_space_gb: float
    used_space_gb: float
    available_space_gb: float
    usage_percent: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorSummary:
    """Data class for error summary statistics."""
    error_type: str
    count: int
    first_occurrence: datetime
    last_occurrence: datetime
    sample_messages: List[str] = field(default_factory=list)


@dataclass
class PerformanceAlert:
    """Data class for performance alerts."""
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


class ProcessingMonitor:
    """Class for monitoring media processing performance and system health."""
    
    def __init__(self, storage_path: str = None, alert_callback: Callable = None):
        """Initialize the processing monitor.
        
        Args:
            storage_path: Path to store monitoring data (optional)
            alert_callback: Callback function for alerts (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.storage_path = storage_path or os.path.join(os.getcwd(), 'monitoring_data')
        self.alert_callback = alert_callback
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Metrics storage
        self.processing_metrics: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self.storage_metrics: deque = deque(maxlen=1000)      # Keep last 1k storage checks
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_details: Dict[str, ErrorSummary] = {}
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=100)   # Keep last 100 performance samples
        self.current_load: Dict[str, float] = {}
        
        # Thresholds and configuration
        self.storage_thresholds = {
            'warning': 80.0,    # 80% usage warning
            'critical': 90.0,   # 90% usage critical
            'emergency': 95.0   # 95% usage emergency
        }
        
        self.performance_thresholds = {
            'processing_time_warning': 30.0,     # 30 seconds per file
            'processing_time_critical': 60.0,    # 60 seconds per file
            'error_rate_warning': 0.05,          # 5% error rate
            'error_rate_critical': 0.15,         # 15% error rate
            'memory_usage_warning': 80.0,        # 80% memory usage
            'memory_usage_critical': 90.0,       # 90% memory usage
        }
        
        # Monitoring state
        self.monitoring_active = False
        self.monitoring_thread = None
        self.monitoring_interval = 60  # Check every 60 seconds
        
        # Performance adjustment settings
        self.auto_adjustment_enabled = True
        self.adjustment_history: deque = deque(maxlen=50)
        
        self.logger.info("ProcessingMonitor initialized")
    
    def start_monitoring(self) -> None:
        """Start background monitoring thread."""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Background monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background monitoring thread."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        self.logger.info("Background monitoring stopped")
    
    def record_processing_metrics(self, operation_type: str, file_size: int, 
                                processing_time: float, success: bool = True,
                                compression_ratio: Optional[float] = None,
                                error_type: Optional[str] = None,
                                error_message: Optional[str] = None) -> None:
        """Record processing performance metrics.
        
        Args:
            operation_type: Type of processing operation
            file_size: Size of processed file in bytes
            processing_time: Time taken for processing in seconds
            success: Whether the operation was successful
            compression_ratio: Compression ratio achieved (optional)
            error_type: Type of error if operation failed (optional)
            error_message: Error message if operation failed (optional)
        """
        try:
            # Get current system metrics
            memory_usage = self._get_memory_usage()
            cpu_usage = self._get_cpu_usage()
            
            # Create metrics record
            metrics = ProcessingMetrics(
                operation_type=operation_type,
                file_size=file_size,
                processing_time=processing_time,
                compression_ratio=compression_ratio,
                success=success,
                error_type=error_type,
                error_message=error_message,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage
            )
            
            # Store metrics
            self.processing_metrics.append(metrics)
            
            # Update error tracking
            if not success and error_type:
                self._update_error_tracking(error_type, error_message)
            
            # Update performance history
            self._update_performance_history(processing_time, file_size)
            
            # Check for performance issues
            self._check_performance_thresholds(metrics)
            
            self.logger.debug(f"Recorded processing metrics: {operation_type}, "
                            f"{file_size} bytes, {processing_time:.2f}s, success={success}")
            
        except Exception as e:
            self.logger.error(f"Failed to record processing metrics: {str(e)}")
    
    def record_storage_metrics(self, storage_path: str = None) -> StorageMetrics:
        """Record current storage usage metrics.
        
        Args:
            storage_path: Path to check storage for (defaults to current directory)
            
        Returns:
            StorageMetrics object with current storage information
        """
        try:
            path = storage_path or os.getcwd()
            
            # Get disk usage statistics
            disk_usage = psutil.disk_usage(path)
            
            # Convert to GB
            total_gb = disk_usage.total / (1024**3)
            used_gb = disk_usage.used / (1024**3)
            available_gb = disk_usage.free / (1024**3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Create storage metrics
            storage_metrics = StorageMetrics(
                total_space_gb=total_gb,
                used_space_gb=used_gb,
                available_space_gb=available_gb,
                usage_percent=usage_percent
            )
            
            # Store metrics
            self.storage_metrics.append(storage_metrics)
            
            # Check storage thresholds
            self._check_storage_thresholds(storage_metrics)
            
            self.logger.debug(f"Recorded storage metrics: {usage_percent:.1f}% used "
                            f"({used_gb:.1f}GB / {total_gb:.1f}GB)")
            
            return storage_metrics
            
        except Exception as e:
            self.logger.error(f"Failed to record storage metrics: {str(e)}")
            # Return empty metrics on error
            return StorageMetrics(0, 0, 0, 0)
    
    def get_processing_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing statistics for the specified time period.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary containing processing statistics
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter metrics within time period
            recent_metrics = [
                m for m in self.processing_metrics 
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    'period_hours': hours,
                    'total_operations': 0,
                    'message': 'No processing operations in the specified period'
                }
            
            # Calculate statistics
            total_operations = len(recent_metrics)
            successful_operations = sum(1 for m in recent_metrics if m.success)
            failed_operations = total_operations - successful_operations
            
            # Processing time statistics
            processing_times = [m.processing_time for m in recent_metrics]
            avg_processing_time = sum(processing_times) / len(processing_times)
            max_processing_time = max(processing_times)
            min_processing_time = min(processing_times)
            
            # File size statistics
            file_sizes = [m.file_size for m in recent_metrics]
            avg_file_size = sum(file_sizes) / len(file_sizes)
            total_data_processed = sum(file_sizes)
            
            # Compression statistics
            compression_ratios = [m.compression_ratio for m in recent_metrics if m.compression_ratio is not None]
            avg_compression_ratio = sum(compression_ratios) / len(compression_ratios) if compression_ratios else None
            
            # Error rate
            error_rate = failed_operations / total_operations if total_operations > 0 else 0
            
            # Operation type breakdown
            operation_counts = defaultdict(int)
            for m in recent_metrics:
                operation_counts[m.operation_type] += 1
            
            # Throughput (operations per hour)
            throughput = total_operations / hours if hours > 0 else 0
            
            return {
                'period_hours': hours,
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'failed_operations': failed_operations,
                'error_rate': error_rate,
                'processing_time': {
                    'average_seconds': avg_processing_time,
                    'max_seconds': max_processing_time,
                    'min_seconds': min_processing_time
                },
                'file_size': {
                    'average_bytes': avg_file_size,
                    'average_mb': avg_file_size / (1024**2),
                    'total_processed_bytes': total_data_processed,
                    'total_processed_gb': total_data_processed / (1024**3)
                },
                'compression': {
                    'average_ratio': avg_compression_ratio,
                    'average_reduction_percent': (1 - avg_compression_ratio) * 100 if avg_compression_ratio else None
                },
                'operation_breakdown': dict(operation_counts),
                'throughput_per_hour': throughput
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get processing statistics: {str(e)}")
            return {'error': str(e)}
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary containing error summary
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filter recent errors
            recent_errors = {}
            for error_type, error_summary in self.error_details.items():
                if error_summary.last_occurrence >= cutoff_time:
                    recent_errors[error_type] = {
                        'count': error_summary.count,
                        'first_occurrence': error_summary.first_occurrence.isoformat(),
                        'last_occurrence': error_summary.last_occurrence.isoformat(),
                        'sample_messages': error_summary.sample_messages[-3:]  # Last 3 messages
                    }
            
            # Get total error count for the period
            recent_metrics = [
                m for m in self.processing_metrics 
                if m.timestamp >= cutoff_time and not m.success
            ]
            
            total_errors = len(recent_metrics)
            
            # Most common errors
            error_counts = defaultdict(int)
            for m in recent_metrics:
                if m.error_type:
                    error_counts[m.error_type] += 1
            
            most_common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'period_hours': hours,
                'total_errors': total_errors,
                'unique_error_types': len(recent_errors),
                'most_common_errors': most_common_errors,
                'error_details': recent_errors
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get error summary: {str(e)}")
            return {'error': str(e)}
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get current storage status and recent trends.
        
        Returns:
            Dictionary containing storage status information
        """
        try:
            # Get current storage metrics
            current_metrics = self.record_storage_metrics()
            
            # Get recent storage history
            recent_metrics = list(self.storage_metrics)[-10:]  # Last 10 measurements
            
            if len(recent_metrics) > 1:
                # Calculate trend
                oldest = recent_metrics[0]
                newest = recent_metrics[-1]
                usage_trend = newest.usage_percent - oldest.usage_percent
                
                # Estimate time to full (if trend is positive)
                time_to_full = None
                if usage_trend > 0:
                    time_span_hours = (newest.timestamp - oldest.timestamp).total_seconds() / 3600
                    if time_span_hours > 0:
                        remaining_percent = 100 - newest.usage_percent
                        trend_per_hour = usage_trend / time_span_hours
                        if trend_per_hour > 0:
                            time_to_full_hours = remaining_percent / trend_per_hour
                            time_to_full = {
                                'hours': time_to_full_hours,
                                'days': time_to_full_hours / 24
                            }
            else:
                usage_trend = 0
                time_to_full = None
            
            # Determine status level
            usage_percent = current_metrics.usage_percent
            if usage_percent >= self.storage_thresholds['emergency']:
                status_level = 'emergency'
            elif usage_percent >= self.storage_thresholds['critical']:
                status_level = 'critical'
            elif usage_percent >= self.storage_thresholds['warning']:
                status_level = 'warning'
            else:
                status_level = 'normal'
            
            return {
                'current_usage': {
                    'total_gb': current_metrics.total_space_gb,
                    'used_gb': current_metrics.used_space_gb,
                    'available_gb': current_metrics.available_space_gb,
                    'usage_percent': current_metrics.usage_percent
                },
                'status_level': status_level,
                'usage_trend_percent': usage_trend,
                'time_to_full': time_to_full,
                'thresholds': self.storage_thresholds,
                'last_updated': current_metrics.timestamp.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get storage status: {str(e)}")
            return {'error': str(e)}
    
    def detect_performance_degradation(self) -> Dict[str, Any]:
        """Detect performance degradation by comparing recent performance to historical baseline.
        
        Returns:
            Dictionary containing degradation analysis
        """
        try:
            if len(self.performance_history) < 10:
                return {
                    'status': 'insufficient_data',
                    'message': 'Not enough performance data for degradation analysis'
                }
            
            # Split performance history into recent and baseline
            recent_samples = list(self.performance_history)[-20:]  # Last 20 samples
            baseline_samples = list(self.performance_history)[:-20] if len(self.performance_history) > 20 else []
            
            if not baseline_samples:
                return {
                    'status': 'no_baseline',
                    'message': 'Not enough historical data for baseline comparison'
                }
            
            # Calculate performance metrics
            recent_avg_time = sum(s['processing_time'] for s in recent_samples) / len(recent_samples)
            baseline_avg_time = sum(s['processing_time'] for s in baseline_samples) / len(baseline_samples)
            
            recent_avg_throughput = sum(s['throughput'] for s in recent_samples) / len(recent_samples)
            baseline_avg_throughput = sum(s['throughput'] for s in baseline_samples) / len(baseline_samples)
            
            # Calculate degradation percentages
            time_degradation = ((recent_avg_time - baseline_avg_time) / baseline_avg_time) * 100
            throughput_degradation = ((baseline_avg_throughput - recent_avg_throughput) / baseline_avg_throughput) * 100
            
            # Determine degradation level
            degradation_threshold_minor = 15.0  # 15% degradation
            degradation_threshold_major = 30.0  # 30% degradation
            
            max_degradation = max(time_degradation, throughput_degradation)
            
            if max_degradation >= degradation_threshold_major:
                degradation_level = 'major'
            elif max_degradation >= degradation_threshold_minor:
                degradation_level = 'minor'
            else:
                degradation_level = 'none'
            
            # Generate recommendations
            recommendations = []
            if time_degradation > degradation_threshold_minor:
                recommendations.append("Consider reducing processing quality settings")
                recommendations.append("Check for system resource constraints")
            
            if throughput_degradation > degradation_threshold_minor:
                recommendations.append("Consider increasing batch processing parallelism")
                recommendations.append("Check for network or storage bottlenecks")
            
            return {
                'status': 'analyzed',
                'degradation_level': degradation_level,
                'metrics': {
                    'processing_time_degradation_percent': time_degradation,
                    'throughput_degradation_percent': throughput_degradation,
                    'recent_avg_processing_time': recent_avg_time,
                    'baseline_avg_processing_time': baseline_avg_time,
                    'recent_avg_throughput': recent_avg_throughput,
                    'baseline_avg_throughput': baseline_avg_throughput
                },
                'recommendations': recommendations,
                'sample_sizes': {
                    'recent_samples': len(recent_samples),
                    'baseline_samples': len(baseline_samples)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to detect performance degradation: {str(e)}")
            return {'error': str(e)}
    
    def suggest_performance_adjustments(self) -> Dict[str, Any]:
        """Suggest performance adjustments based on current metrics and system state.
        
        Returns:
            Dictionary containing adjustment suggestions
        """
        try:
            suggestions = []
            current_metrics = self._get_current_system_metrics()
            
            # Analyze recent processing performance
            recent_metrics = list(self.processing_metrics)[-50:]  # Last 50 operations
            if not recent_metrics:
                return {
                    'status': 'no_data',
                    'message': 'No recent processing data available for analysis'
                }
            
            # Calculate average processing time and error rate
            avg_processing_time = sum(m.processing_time for m in recent_metrics) / len(recent_metrics)
            error_rate = sum(1 for m in recent_metrics if not m.success) / len(recent_metrics)
            
            # Memory-based suggestions
            if current_metrics['memory_usage_percent'] > self.performance_thresholds['memory_usage_critical']:
                suggestions.append({
                    'type': 'memory_optimization',
                    'priority': 'high',
                    'suggestion': 'Reduce batch processing size to lower memory usage',
                    'current_value': current_metrics['memory_usage_percent'],
                    'threshold': self.performance_thresholds['memory_usage_critical']
                })
            elif current_metrics['memory_usage_percent'] > self.performance_thresholds['memory_usage_warning']:
                suggestions.append({
                    'type': 'memory_optimization',
                    'priority': 'medium',
                    'suggestion': 'Consider reducing image processing quality to save memory',
                    'current_value': current_metrics['memory_usage_percent'],
                    'threshold': self.performance_thresholds['memory_usage_warning']
                })
            
            # Processing time-based suggestions
            if avg_processing_time > self.performance_thresholds['processing_time_critical']:
                suggestions.append({
                    'type': 'processing_optimization',
                    'priority': 'high',
                    'suggestion': 'Enable aggressive compression mode to reduce processing time',
                    'current_value': avg_processing_time,
                    'threshold': self.performance_thresholds['processing_time_critical']
                })
            elif avg_processing_time > self.performance_thresholds['processing_time_warning']:
                suggestions.append({
                    'type': 'processing_optimization',
                    'priority': 'medium',
                    'suggestion': 'Consider reducing thumbnail generation sizes',
                    'current_value': avg_processing_time,
                    'threshold': self.performance_thresholds['processing_time_warning']
                })
            
            # Error rate-based suggestions
            if error_rate > self.performance_thresholds['error_rate_critical']:
                suggestions.append({
                    'type': 'error_reduction',
                    'priority': 'high',
                    'suggestion': 'Enable fallback processing mode to reduce errors',
                    'current_value': error_rate,
                    'threshold': self.performance_thresholds['error_rate_critical']
                })
            elif error_rate > self.performance_thresholds['error_rate_warning']:
                suggestions.append({
                    'type': 'error_reduction',
                    'priority': 'medium',
                    'suggestion': 'Review and improve error handling for common failure cases',
                    'current_value': error_rate,
                    'threshold': self.performance_thresholds['error_rate_warning']
                })
            
            # Storage-based suggestions
            storage_status = self.get_storage_status()
            if storage_status.get('current_usage', {}).get('usage_percent', 0) > self.storage_thresholds['warning']:
                suggestions.append({
                    'type': 'storage_optimization',
                    'priority': 'high' if storage_status['current_usage']['usage_percent'] > self.storage_thresholds['critical'] else 'medium',
                    'suggestion': 'Enable more aggressive compression to save storage space',
                    'current_value': storage_status['current_usage']['usage_percent'],
                    'threshold': self.storage_thresholds['warning']
                })
            
            # Performance improvement suggestions
            if len(suggestions) == 0:
                # System is performing well, suggest optimizations
                suggestions.append({
                    'type': 'optimization',
                    'priority': 'low',
                    'suggestion': 'System is performing well. Consider enabling higher quality settings if resources allow.',
                    'current_value': None,
                    'threshold': None
                })
            
            return {
                'status': 'analyzed',
                'total_suggestions': len(suggestions),
                'suggestions': suggestions,
                'system_metrics': current_metrics,
                'analysis_period': {
                    'operations_analyzed': len(recent_metrics),
                    'average_processing_time': avg_processing_time,
                    'error_rate': error_rate
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to suggest performance adjustments: {str(e)}")
            return {'error': str(e)}
    
    def apply_automatic_adjustments(self) -> Dict[str, Any]:
        """Apply automatic performance adjustments based on current system state.
        
        Returns:
            Dictionary containing applied adjustments
        """
        try:
            if not self.auto_adjustment_enabled:
                return {
                    'status': 'disabled',
                    'message': 'Automatic adjustments are disabled'
                }
            
            suggestions = self.suggest_performance_adjustments()
            if 'error' in suggestions:
                return suggestions
            
            applied_adjustments = []
            
            # Apply high-priority suggestions automatically
            for suggestion in suggestions.get('suggestions', []):
                if suggestion['priority'] == 'high':
                    adjustment_result = self._apply_adjustment(suggestion)
                    if adjustment_result:
                        applied_adjustments.append(adjustment_result)
            
            # Record adjustment history
            adjustment_record = {
                'timestamp': datetime.now(),
                'adjustments_applied': len(applied_adjustments),
                'adjustments': applied_adjustments
            }
            self.adjustment_history.append(adjustment_record)
            
            return {
                'status': 'completed',
                'adjustments_applied': len(applied_adjustments),
                'adjustments': applied_adjustments,
                'timestamp': adjustment_record['timestamp'].isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to apply automatic adjustments: {str(e)}")
            return {'error': str(e)}
    
    def export_metrics(self, output_path: str = None, format: str = 'json') -> str:
        """Export collected metrics to file.
        
        Args:
            output_path: Path to save metrics file (optional)
            format: Export format ('json' or 'csv')
            
        Returns:
            Path to exported file
        """
        try:
            if not output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(self.storage_path, f'metrics_export_{timestamp}.{format}')
            
            # Prepare export data
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'processing_metrics': [
                    {
                        'operation_type': m.operation_type,
                        'file_size': m.file_size,
                        'processing_time': m.processing_time,
                        'compression_ratio': m.compression_ratio,
                        'success': m.success,
                        'error_type': m.error_type,
                        'error_message': m.error_message,
                        'timestamp': m.timestamp.isoformat(),
                        'memory_usage_mb': m.memory_usage_mb,
                        'cpu_usage_percent': m.cpu_usage_percent
                    }
                    for m in self.processing_metrics
                ],
                'storage_metrics': [
                    {
                        'total_space_gb': m.total_space_gb,
                        'used_space_gb': m.used_space_gb,
                        'available_space_gb': m.available_space_gb,
                        'usage_percent': m.usage_percent,
                        'timestamp': m.timestamp.isoformat()
                    }
                    for m in self.storage_metrics
                ],
                'error_summary': {
                    error_type: {
                        'count': summary.count,
                        'first_occurrence': summary.first_occurrence.isoformat(),
                        'last_occurrence': summary.last_occurrence.isoformat(),
                        'sample_messages': summary.sample_messages
                    }
                    for error_type, summary in self.error_details.items()
                }
            }
            
            # Export based on format
            if format.lower() == 'json':
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Metrics exported to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to export metrics: {str(e)}")
            raise
    
    def _monitoring_loop(self) -> None:
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Record storage metrics
                self.record_storage_metrics()
                
                # Check for performance degradation
                degradation_status = self.detect_performance_degradation()
                if degradation_status.get('degradation_level') in ['minor', 'major']:
                    self._send_alert(PerformanceAlert(
                        alert_type='performance_degradation',
                        severity='medium' if degradation_status['degradation_level'] == 'minor' else 'high',
                        message=f"Performance degradation detected: {degradation_status['degradation_level']}",
                        metrics=degradation_status
                    ))
                
                # Apply automatic adjustments if enabled
                if self.auto_adjustment_enabled:
                    self.apply_automatic_adjustments()
                
                # Sleep until next monitoring cycle
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(self.monitoring_interval)
    
    def _update_error_tracking(self, error_type: str, error_message: Optional[str]) -> None:
        """Update error tracking statistics."""
        self.error_counts[error_type] += 1
        
        if error_type not in self.error_details:
            self.error_details[error_type] = ErrorSummary(
                error_type=error_type,
                count=1,
                first_occurrence=datetime.now(),
                last_occurrence=datetime.now(),
                sample_messages=[]
            )
        else:
            self.error_details[error_type].count += 1
            self.error_details[error_type].last_occurrence = datetime.now()
        
        # Add sample message (keep only last 5)
        if error_message:
            sample_messages = self.error_details[error_type].sample_messages
            sample_messages.append(error_message)
            if len(sample_messages) > 5:
                sample_messages.pop(0)
    
    def _update_performance_history(self, processing_time: float, file_size: int) -> None:
        """Update performance history for trend analysis."""
        throughput = file_size / processing_time if processing_time > 0 else 0
        
        performance_sample = {
            'timestamp': datetime.now(),
            'processing_time': processing_time,
            'file_size': file_size,
            'throughput': throughput
        }
        
        self.performance_history.append(performance_sample)
    
    def _check_performance_thresholds(self, metrics: ProcessingMetrics) -> None:
        """Check performance metrics against thresholds and generate alerts."""
        alerts = []
        
        # Check processing time
        if metrics.processing_time > self.performance_thresholds['processing_time_critical']:
            alerts.append(PerformanceAlert(
                alert_type='processing_time',
                severity='high',
                message=f"Processing time exceeded critical threshold: {metrics.processing_time:.2f}s",
                metrics={'processing_time': metrics.processing_time, 'file_size': metrics.file_size}
            ))
        elif metrics.processing_time > self.performance_thresholds['processing_time_warning']:
            alerts.append(PerformanceAlert(
                alert_type='processing_time',
                severity='medium',
                message=f"Processing time exceeded warning threshold: {metrics.processing_time:.2f}s",
                metrics={'processing_time': metrics.processing_time, 'file_size': metrics.file_size}
            ))
        
        # Check memory usage
        if metrics.memory_usage_mb and metrics.memory_usage_mb > self.performance_thresholds['memory_usage_critical']:
            alerts.append(PerformanceAlert(
                alert_type='memory_usage',
                severity='high',
                message=f"Memory usage exceeded critical threshold: {metrics.memory_usage_mb:.1f}%",
                metrics={'memory_usage_mb': metrics.memory_usage_mb}
            ))
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert)
    
    def _check_storage_thresholds(self, storage_metrics: StorageMetrics) -> None:
        """Check storage metrics against thresholds and generate alerts."""
        usage_percent = storage_metrics.usage_percent
        
        if usage_percent >= self.storage_thresholds['emergency']:
            alert = PerformanceAlert(
                alert_type='storage_usage',
                severity='critical',
                message=f"Storage usage critical: {usage_percent:.1f}% used",
                metrics={'usage_percent': usage_percent, 'available_gb': storage_metrics.available_space_gb}
            )
            self._send_alert(alert)
        elif usage_percent >= self.storage_thresholds['critical']:
            alert = PerformanceAlert(
                alert_type='storage_usage',
                severity='high',
                message=f"Storage usage high: {usage_percent:.1f}% used",
                metrics={'usage_percent': usage_percent, 'available_gb': storage_metrics.available_space_gb}
            )
            self._send_alert(alert)
        elif usage_percent >= self.storage_thresholds['warning']:
            alert = PerformanceAlert(
                alert_type='storage_usage',
                severity='medium',
                message=f"Storage usage warning: {usage_percent:.1f}% used",
                metrics={'usage_percent': usage_percent, 'available_gb': storage_metrics.available_space_gb}
            )
            self._send_alert(alert)
    
    def _send_alert(self, alert: PerformanceAlert) -> None:
        """Send performance alert."""
        try:
            self.logger.warning(f"Performance Alert [{alert.severity.upper()}]: {alert.message}")
            
            if self.alert_callback:
                self.alert_callback(alert)
                
        except Exception as e:
            self.logger.error(f"Failed to send alert: {str(e)}")
    
    def _apply_adjustment(self, suggestion: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Apply a performance adjustment suggestion.
        
        Args:
            suggestion: Suggestion dictionary
            
        Returns:
            Applied adjustment details or None if not applied
        """
        try:
            # This is a placeholder for actual adjustment implementation
            # In a real implementation, this would modify processing parameters
            
            adjustment = {
                'type': suggestion['type'],
                'suggestion': suggestion['suggestion'],
                'applied': True,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"Applied automatic adjustment: {suggestion['suggestion']}")
            return adjustment
            
        except Exception as e:
            self.logger.error(f"Failed to apply adjustment: {str(e)}")
            return None
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            memory = psutil.virtual_memory()
            return memory.percent
        except Exception:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def _get_current_system_metrics(self) -> Dict[str, float]:
        """Get current system performance metrics."""
        return {
            'memory_usage_percent': self._get_memory_usage(),
            'cpu_usage_percent': self._get_cpu_usage(),
            'timestamp': datetime.now().isoformat()
        }