"""
Performance Metrics Module - Latency, Throughput, CPU & Memory Monitoring

Métricas implementadas:
- Latencia: p50, p95, p99 (percentiles)
- Throughput: operaciones/segundo
- CPU: uso porcentual
- Memoria: uso en MB

Uso:
    from profiling.latency import PerformanceMonitor
    
    monitor = PerformanceMonitor()
    
    # Medir latencia de una función
    with monitor.measure("process_tick"):
        process_tick(data)
    
    # Obtener métricas
    stats = monitor.get_statistics()
"""

import time
import psutil
import numpy as np
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import threading


@dataclass
class LatencyStats:
    """Estadísticas de latencia para una operación."""
    count: int = 0
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    mean_ms: float = 0.0
    std_ms: float = 0.0


@dataclass  
class SystemStats:
    """Estadísticas del sistema."""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0


class PerformanceMonitor:
    """
    Monitor de rendimiento para medir latencia, throughput, CPU y memoria.
    
    Thread-safe para uso en sistemas multi-threaded.
    
    Ejemplo:
        monitor = PerformanceMonitor()
        
        with monitor.measure("strategy_calculate"):
            signal = strategy.calculate(data)
        
        # Obtener estadísticas
        stats = monitor.get_statistics()
        print(f"p99: {stats['strategy_calculate'].p99:.4f} ms")
    """
    
    def __init__(self, max_samples: int = 10000):
        """
        Args:
            max_samples: Número máximo de muestras a mantener por operación
        """
        self._samples: Dict[str, List[float]] = defaultdict(list)
        self._max_samples = max_samples
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._operation_counts: Dict[str, int] = defaultdict(int)
        
    @contextmanager
    def measure(self, operation_name: str):
        """
        Context manager para medir latencia de una operación.
        
        Args:
            operation_name: Nombre identificador de la operación
            
        Usage:
            with monitor.measure("process_tick"):
                process_tick(tick)
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            with self._lock:
                samples = self._samples[operation_name]
                samples.append(elapsed_ms)
                self._operation_counts[operation_name] += 1
                
                # Mantener límite de muestras (circular buffer)
                if len(samples) > self._max_samples:
                    self._samples[operation_name] = samples[-self._max_samples:]
    
    def record_latency(self, operation_name: str, latency_ms: float):
        """
        Registra una latencia manualmente (sin context manager).
        
        Args:
            operation_name: Nombre de la operación
            latency_ms: Latencia en milisegundos
        """
        with self._lock:
            samples = self._samples[operation_name]
            samples.append(latency_ms)
            self._operation_counts[operation_name] += 1
            
            if len(samples) > self._max_samples:
                self._samples[operation_name] = samples[-self._max_samples:]
    
    def get_latency_stats(self, operation_name: str) -> Optional[LatencyStats]:
        """
        Calcula estadísticas de latencia para una operación.
        
        Returns:
            LatencyStats con p50, p95, p99, min, max, mean, std
        """
        with self._lock:
            samples = self._samples.get(operation_name, [])
            
        if not samples:
            return None
            
        arr = np.array(samples)
        return LatencyStats(
            count=len(arr),
            p50=float(np.percentile(arr, 50)),
            p95=float(np.percentile(arr, 95)),
            p99=float(np.percentile(arr, 99)),
            min_ms=float(np.min(arr)),
            max_ms=float(np.max(arr)),
            mean_ms=float(np.mean(arr)),
            std_ms=float(np.std(arr))
        )
    
    def get_throughput(self, operation_name: str) -> float:
        """
        Calcula throughput (operaciones por segundo) para una operación.
        
        Returns:
            Operaciones por segundo desde el inicio del monitor
        """
        elapsed = time.time() - self._start_time
        if elapsed == 0:
            return 0.0
            
        with self._lock:
            count = self._operation_counts.get(operation_name, 0)
            
        return count / elapsed
    
    @staticmethod
    def get_system_stats() -> SystemStats:
        """
        Obtiene estadísticas actuales del sistema.
        
        Returns:
            SystemStats con CPU y memoria
        """
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return SystemStats(
            cpu_percent=process.cpu_percent(interval=0.1),
            memory_mb=memory_info.rss / (1024 * 1024),
            memory_percent=process.memory_percent()
        )
    
    def get_all_statistics(self) -> Dict:
        """
        Obtiene todas las estadísticas: latencia, throughput, sistema.
        
        Returns:
            Dict con todas las métricas organizadas
        """
        stats = {
            "timestamp": time.time(),
            "uptime_seconds": time.time() - self._start_time,
            "latency": {},
            "throughput": {},
            "system": {}
        }
        
        # Latencia y throughput por operación
        with self._lock:
            operations = list(self._samples.keys())
            
        for op in operations:
            latency = self.get_latency_stats(op)
            if latency:
                stats["latency"][op] = {
                    "count": latency.count,
                    "p50_ms": round(latency.p50, 4),
                    "p95_ms": round(latency.p95, 4),
                    "p99_ms": round(latency.p99, 4),
                    "min_ms": round(latency.min_ms, 4),
                    "max_ms": round(latency.max_ms, 4),
                    "mean_ms": round(latency.mean_ms, 4),
                    "std_ms": round(latency.std_ms, 4)
                }
            stats["throughput"][op] = round(self.get_throughput(op), 2)
        
        # Sistema
        sys_stats = self.get_system_stats()
        stats["system"] = {
            "cpu_percent": round(sys_stats.cpu_percent, 2),
            "memory_mb": round(sys_stats.memory_mb, 2),
            "memory_percent": round(sys_stats.memory_percent, 2)
        }
        
        return stats
    
    def reset(self):
        """Reinicia todas las métricas."""
        with self._lock:
            self._samples.clear()
            self._operation_counts.clear()
            self._start_time = time.time()
    
    def print_summary(self):
        """Imprime un resumen formateado de las métricas."""
        stats = self.get_all_statistics()
        
        print("\n" + "="*70)
        print("📊 PERFORMANCE METRICS SUMMARY")
        print("="*70)
        
        # Sistema
        sys = stats["system"]
        print(f"\n🖥️  SYSTEM RESOURCES")
        print(f"   CPU:    {sys['cpu_percent']:.1f}%")
        print(f"   Memory: {sys['memory_mb']:.1f} MB ({sys['memory_percent']:.1f}%)")
        
        # Latencia por operación
        if stats["latency"]:
            print(f"\n⏱️  LATENCY (ms)")
            print("-"*70)
            print(f"{'Operation':<25} {'Count':>8} {'P50':>8} {'P95':>8} {'P99':>8} {'Mean':>8}")
            print("-"*70)
            
            for op, lat in stats["latency"].items():
                print(f"{op:<25} {lat['count']:>8} {lat['p50_ms']:>8.4f} "
                      f"{lat['p95_ms']:>8.4f} {lat['p99_ms']:>8.4f} {lat['mean_ms']:>8.4f}")
        
        # Throughput
        if stats["throughput"]:
            print(f"\n🚀 THROUGHPUT (ops/sec)")
            for op, tps in stats["throughput"].items():
                print(f"   {op}: {tps:.2f}")
        
        print("\n" + "="*70 + "\n")


# --- DECORADOR PARA MEDIR FUNCIONES ---
def measure_latency(monitor: PerformanceMonitor, operation_name: Optional[str] = None):
    """
    Decorador para medir latencia de funciones.
    
    Usage:
        @measure_latency(monitor, "my_function")
        def my_function():
            ...
    """
    def decorator(func):
        name = operation_name or func.__qualname__
        
        def wrapper(*args, **kwargs):
            with monitor.measure(name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# --- EJEMPLO DE USO / TEST ---
if __name__ == "__main__":
    import random
    
    print("🧪 Testing Performance Monitor...\n")
    
    monitor = PerformanceMonitor()
    
    # Simular operaciones
    print("Ejecutando 1000 operaciones simuladas...")
    for i in range(1000):
        # Simular process_tick
        with monitor.measure("process_tick"):
            time.sleep(random.uniform(0.0001, 0.001))  # 0.1-1ms
        
        # Simular strategy_calculate
        with monitor.measure("strategy_calculate"):
            time.sleep(random.uniform(0.0005, 0.002))  # 0.5-2ms
        
        # Simular db_write
        with monitor.measure("db_write"):
            time.sleep(random.uniform(0.001, 0.005))  # 1-5ms
    
    # Mostrar resultados
    monitor.print_summary()
    
    # También disponible como dict para exportar
    stats = monitor.get_all_statistics()
    print(f"Stats as dict: {list(stats.keys())}")
