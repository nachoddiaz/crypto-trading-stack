import pandas as pd
from typing import List, Dict

class PortfolioReporter:
    """
    Adaptador para convertir datos crudos del TraderEngine a formatos
    visuales (DataFrames) requeridos por el Dashboard.
    """
    
    @staticmethod
    def create_equity_df(raw_data: List[Dict]) -> pd.DataFrame:
        if not raw_data: 
            return pd.DataFrame(columns=["total_equity", "usdt_balance"])
            
        df = pd.DataFrame(raw_data)
        # Conversión de tipos fuera del Hot Path
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('timestamp', inplace=True)
        return df

    @staticmethod
    def create_trades_df(raw_data: List[Dict]) -> pd.DataFrame:
        if not raw_data: 
            return pd.DataFrame(columns=["symbol", "side", "qty", "price", "edge_delta"])
            
        df = pd.DataFrame(raw_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        return df
    
    @staticmethod
    def calculate_metrics(equity_df: pd.DataFrame) -> Dict[str, float]:
        """Calcula métricas de rendimiento (Sharpe, Drawdown) sobre el DF."""
        if equity_df.empty: 
            return {}
        
        # Ejemplo simple de métrica
        returns = equity_df['total_equity'].pct_change().dropna()
        total_ret = (equity_df['total_equity'].iloc[-1] / equity_df['total_equity'].iloc[0]) - 1
        
        return {
            "total_return": total_ret,
            "volatility": returns.std() if not returns.empty else 0.0
        }