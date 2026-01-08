import numpy as np
from typing import List, Dict, Any, Optional


def calculate_sharpe_ratio(
    equity_curve: List[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> Optional[float]:
    """
    Calculate annualized Sharpe ratio.
    
    Args:
        equity_curve: List of equity values over time
        risk_free_rate: Annual risk-free rate (default 0)
        periods_per_year: Number of periods in a year (252 for daily)
    
    Returns:
        Sharpe ratio or None if insufficient data
    """
    if len(equity_curve) < 2:
        return None
    
    # Calculate returns
    equity_array = np.array(equity_curve)
    returns = np.diff(equity_array) / equity_array[:-1]
    
    if len(returns) == 0 or np.std(returns) == 0:
        return None
    
    # Annualized metrics
    mean_return = np.mean(returns) * periods_per_year
    std_return = np.std(returns) * np.sqrt(periods_per_year)
    
    sharpe = (mean_return - risk_free_rate) / std_return
    
    return float(sharpe)


def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    Calculate maximum drawdown as a percentage.
    
    Returns:
        Max drawdown as positive percentage (e.g., 15.5 for 15.5% drawdown)
    """
    if len(equity_curve) < 2:
        return 0.0
    
    equity_array = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_array)
    drawdown = (peak - equity_array) / peak * 100
    
    return float(np.max(drawdown))


def calculate_calmar_ratio(
    equity_curve: List[float],
    periods_per_year: int = 252
) -> Optional[float]:
    """
    Calculate Calmar ratio (annualized return / max drawdown).
    
    Returns:
        Calmar ratio or None if max drawdown is 0
    """
    if len(equity_curve) < 2:
        return None
    
    # Calculate annualized return
    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
    num_periods = len(equity_curve) - 1
    annualized_return = (1 + total_return) ** (periods_per_year / num_periods) - 1
    annualized_return_pct = annualized_return * 100
    
    # Calculate max drawdown
    max_dd = calculate_max_drawdown(equity_curve)
    
    if max_dd == 0:
        return None if annualized_return_pct <= 0 else float('inf')
    
    return float(annualized_return_pct / max_dd)


def calculate_win_rate(trades: List[Dict[str, Any]]) -> Optional[float]:
    """
    Calculate win rate from trade history.
    
    Args:
        trades: List of trade records with 'pnl' field
    
    Returns:
        Win rate as percentage (0-100) or None if no trades
    """
    # Only count closing trades
    closing_trades = [t for t in trades if 'CLOSE' in t.get('action', '')]
    
    if len(closing_trades) == 0:
        return None
    
    winning_trades = sum(1 for t in closing_trades if t.get('pnl', 0) > 0)
    
    return float(winning_trades / len(closing_trades) * 100)


def calculate_profit_factor(trades: List[Dict[str, Any]]) -> Optional[float]:
    """
    Calculate profit factor (gross profit / gross loss).
    
    Returns:
        Profit factor or None if no losing trades
    """
    closing_trades = [t for t in trades if 'CLOSE' in t.get('action', '')]
    
    gross_profit = sum(t.get('pnl', 0) for t in closing_trades if t.get('pnl', 0) > 0)
    gross_loss = abs(sum(t.get('pnl', 0) for t in closing_trades if t.get('pnl', 0) < 0))
    
    if gross_loss == 0:
        return None if gross_profit == 0 else float('inf')
    
    return float(gross_profit / gross_loss)


def calculate_sortino_ratio(
    equity_curve: List[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252
) -> Optional[float]:
    """
    Calculate Sortino ratio (like Sharpe but only considers downside volatility).
    """
    if len(equity_curve) < 2:
        return None
    
    equity_array = np.array(equity_curve)
    returns = np.diff(equity_array) / equity_array[:-1]
    
    # Only consider negative returns for downside deviation
    negative_returns = returns[returns < 0]
    
    if len(negative_returns) == 0:
        return None
    
    downside_std = np.std(negative_returns) * np.sqrt(periods_per_year)
    mean_return = np.mean(returns) * periods_per_year
    
    if downside_std == 0:
        return None
    
    return float((mean_return - risk_free_rate) / downside_std)


def calculate_all_metrics(
    equity_curve: List[float],
    trades: List[Dict[str, Any]],
    initial_equity: float,
    survival_time: int
) -> Dict[str, Any]:
    """
    Calculate all performance metrics.
    
    Returns:
        Dictionary with all metrics
    """
    final_equity = equity_curve[-1] if equity_curve else initial_equity
    total_return = (final_equity - initial_equity) / initial_equity * 100
    
    return {
        'final_equity': final_equity,
        'total_return': total_return,
        'sharpe_ratio': calculate_sharpe_ratio(equity_curve),
        'max_drawdown': calculate_max_drawdown(equity_curve),
        'calmar_ratio': calculate_calmar_ratio(equity_curve),
        'sortino_ratio': calculate_sortino_ratio(equity_curve),
        'win_rate': calculate_win_rate(trades),
        'profit_factor': calculate_profit_factor(trades),
        'total_trades': len([t for t in trades if 'CLOSE' in t.get('action', '')]),
        'survival_time': survival_time
    }
