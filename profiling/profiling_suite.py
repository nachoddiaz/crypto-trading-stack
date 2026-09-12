"""
Profiling Suite - cProfile, py-spy integration examples

Ejecutar:
    python profiling/profiling_suite.py

Para py-spy (proceso en vivo):
    py-spy record -o flamegraph.svg -- python apps/ingestor.py
"""

import cProfile
import pstats
import io
import time
import numpy as np
from contextlib import contextmanager


class Profiler:
    """
    Wrapper para cProfile con output formateado.
    
    Uso:
        profiler = Profiler()
        
        with profiler.profile("strategy_calculation"):
            strategy.calculate(data)
        
        profiler.print_all()
    """
    
    def __init__(self):
        self._profiles = {}
    
    @contextmanager
    def profile(self, name: str):
        """Context manager para perfilar bloques de código."""
        pr = cProfile.Profile()
        pr.enable()
        try:
            yield
        finally:
            pr.disable()
            self._profiles[name] = pr
    
    def get_stats(self, name: str, top_n: int = 10) -> str:
        """Obtiene estadísticas formateadas para un perfil."""
        if name not in self._profiles:
            return f"No profile found: {name}"
        
        s = io.StringIO()
        ps = pstats.Stats(self._profiles[name], stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(top_n)
        return s.getvalue()
    
    def print_stats(self, name: str, top_n: int = 10):
        """Imprime estadísticas de un perfil."""
        print(f"\n{'='*60}")
        print(f"📊 PROFILE: {name}")
        print('='*60)
        print(self.get_stats(name, top_n))
    
    def print_all(self, top_n: int = 10):
        """Imprime todos los perfiles."""
        for name in self._profiles:
            self.print_stats(name, top_n)
    
    def save_stats(self, name: str, filename: str):
        """Guarda estadísticas a archivo para snakeviz."""
        if name in self._profiles:
            self._profiles[name].dump_stats(filename)
            print(f"Saved to {filename} - Run: snakeviz {filename}")


def profile_function(func):
    """
    Decorador para perfilar funciones.
    
    Uso:
        @profile_function
        def my_slow_function():
            ...
    """
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(10)
        print(f"\n📊 Profile of {func.__name__}:")
        print(s.getvalue())
        
        return result
    return wrapper


# --- FUNCIONES DE EJEMPLO PARA PERFILAR ---

def simulate_numba_calculation(n: int = 100000):
    """Simula cálculos pesados tipo Numba."""
    arr = np.random.random(n)
    # Operaciones matemáticas
    result = np.cumsum(arr)
    result = np.sqrt(result)
    result = np.mean(result)
    return result


def simulate_data_processing(n_rows: int = 10000):
    """Simula procesamiento de datos tipo pandas."""
    import pandas as pd  # Import local para medir overhead
    
    data = {
        'timestamp': np.random.random(n_rows) * 1e9,
        'price': np.random.random(n_rows) * 100000,
        'volume': np.random.random(n_rows) * 1000
    }
    df = pd.DataFrame(data)
    
    # Operaciones típicas
    df['returns'] = df['price'].pct_change()
    df['ma_10'] = df['price'].rolling(10).mean()
    df['vol_ma'] = df['volume'].rolling(20).mean()
    
    return df


def simulate_io_operations(n_writes: int = 100):
    """Simula operaciones de I/O."""
    import tempfile
    import json
    
    with tempfile.NamedTemporaryFile(mode='w', delete=True) as f:
        for i in range(n_writes):
            data = {"tick": i, "price": np.random.random()}
            json.dump(data, f)
            f.write('\n')
    
    return n_writes


# --- MAIN ---
if __name__ == "__main__":
    print("🔬 PROFILING SUITE")
    print("="*60)
    
    profiler = Profiler()
    
    # 1. Perfilar cálculos numéricos
    print("\n1️⃣ Profiling NumPy calculations...")
    with profiler.profile("numpy_calc"):
        for _ in range(100):
            simulate_numba_calculation(100000)
    
    # 2. Perfilar procesamiento de datos
    print("2️⃣ Profiling DataFrame processing...")
    with profiler.profile("dataframe_proc"):
        for _ in range(10):
            simulate_data_processing(50000)
    
    # 3. Perfilar I/O
    print("3️⃣ Profiling I/O operations...")
    with profiler.profile("io_operations"):
        for _ in range(50):
            simulate_io_operations(100)
    
    # Imprimir resultados
    profiler.print_all(top_n=8)
    
    # Guardar para snakeviz (opcional)
    # profiler.save_stats("numpy_calc", "numpy_profile.prof")
    
    print("\n" + "="*60)
    print("💡 TIPS:")
    print("   - Para visualización: pip install snakeviz && snakeviz profile.prof")
    print("   - Para live profiling: py-spy record -o flame.svg -- python script.py")
    print("   - Para línea por línea: scalene script.py")
    print("="*60)
