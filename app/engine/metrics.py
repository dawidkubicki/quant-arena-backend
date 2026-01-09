"""
Performance metrics for trading strategies.

Includes standard metrics (Sharpe, Sortino, etc.) and CAPM-based
alpha/beta calculations using SPY as the market benchmark.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple


# =============================================================================
# CAPM / Factor Metrics (Alpha & Beta)
# =============================================================================

def calculate_strategy_returns(
    equity_curve: List[float]
) -> np.ndarray:
    """
    Calculate log returns from an equity curve.
    
    Args:
        equity_curve: List of equity values over time
    
    Returns:
        Array of log returns
    """
    if len(equity_curve) < 2:
        return np.array([])
    
    equity_array = np.array(equity_curve)
    # Use log returns for consistency with market data
    returns = np.log(equity_array[1:] / equity_array[:-1])
    
    return returns


def calculate_beta(
    strategy_returns: np.ndarray,
    spy_returns: np.ndarray
) -> Optional[float]:
    """
    Calculate strategy beta relative to SPY.
    
    β = Cov(r_strategy, r_SPY) / Var(r_SPY)
    
    Beta measures the strategy's exposure to market risk:
    - β ≈ 1: Strategy moves with the market
    - β > 1: Strategy is more volatile than market (momentum strategies)
    - β < 1: Strategy is less volatile than market (mean reversion)
    - β ≈ 0: Market neutral strategy
    
    Args:
        strategy_returns: Array of strategy log returns
        spy_returns: Array of SPY log returns (same timestamps)
    
    Returns:
        Beta value or None if insufficient data
    """
    if len(strategy_returns) < 2 or len(spy_returns) < 2:
        return None
    
    # Ensure same length
    min_len = min(len(strategy_returns), len(spy_returns))
    strat = strategy_returns[:min_len]
    spy = spy_returns[:min_len]
    
    # Calculate covariance and variance
    spy_var = np.var(spy, ddof=1)
    
    if spy_var == 0:
        return None
    
    covariance = np.cov(strat, spy, ddof=1)[0, 1]
    beta = covariance / spy_var
    
    return float(beta)


def calculate_rolling_beta(
    strategy_returns: np.ndarray,
    spy_returns: np.ndarray,
    window: int = 20
) -> List[float]:
    """
    Calculate rolling beta over time.
    
    This shows how the strategy's market exposure changes during the simulation.
    
    Args:
        strategy_returns: Array of strategy log returns
        spy_returns: Array of SPY log returns
        window: Rolling window size (default 20 bars)
    
    Returns:
        List of rolling beta values (NaN for first window-1 values)
    """
    if len(strategy_returns) < window or len(spy_returns) < window:
        return []
    
    min_len = min(len(strategy_returns), len(spy_returns))
    strat = strategy_returns[:min_len]
    spy = spy_returns[:min_len]
    
    rolling_betas = []
    
    for i in range(min_len):
        if i < window - 1:
            rolling_betas.append(float('nan'))
        else:
            window_strat = strat[i - window + 1:i + 1]
            window_spy = spy[i - window + 1:i + 1]
            
            spy_var = np.var(window_spy, ddof=1)
            if spy_var == 0:
                rolling_betas.append(float('nan'))
            else:
                cov = np.cov(window_strat, window_spy, ddof=1)[0, 1]
                rolling_betas.append(float(cov / spy_var))
    
    return rolling_betas


def calculate_alpha(
    strategy_returns: np.ndarray,
    spy_returns: np.ndarray,
    beta: Optional[float] = None
) -> Optional[float]:
    """
    Calculate CAPM alpha (excess return over beta-adjusted market return).
    
    α = r_strategy - β * r_SPY
    
    Positive alpha indicates the strategy generates returns above what
    would be expected given its market exposure.
    
    Args:
        strategy_returns: Array of strategy log returns
        spy_returns: Array of SPY log returns
        beta: Pre-calculated beta (if None, will be calculated)
    
    Returns:
        Annualized alpha or None if insufficient data
    """
    if len(strategy_returns) < 2 or len(spy_returns) < 2:
        return None
    
    min_len = min(len(strategy_returns), len(spy_returns))
    strat = strategy_returns[:min_len]
    spy = spy_returns[:min_len]
    
    if beta is None:
        beta = calculate_beta(strat, spy)
        if beta is None:
            return None
    
    # Calculate alpha as mean excess return
    excess_returns = strat - beta * spy
    alpha = np.mean(excess_returns)
    
    # Annualize (assuming 5-min bars, ~78 per day, 252 trading days)
    bars_per_year = 78 * 252
    annualized_alpha = alpha * bars_per_year
    
    return float(annualized_alpha)


def calculate_cumulative_alpha(
    strategy_returns: np.ndarray,
    spy_returns: np.ndarray,
    rolling_beta: Optional[List[float]] = None,
    window: int = 20
) -> List[float]:
    """
    Calculate cumulative alpha over time.
    
    This shows the running sum of period alphas, demonstrating
    how much excess return the strategy has generated.
    
    Args:
        strategy_returns: Array of strategy log returns
        spy_returns: Array of SPY log returns
        rolling_beta: Pre-calculated rolling betas (optional)
        window: Window for rolling beta if not provided
    
    Returns:
        List of cumulative alpha values
    """
    if len(strategy_returns) < window or len(spy_returns) < window:
        return []
    
    min_len = min(len(strategy_returns), len(spy_returns))
    strat = strategy_returns[:min_len]
    spy = spy_returns[:min_len]
    
    if rolling_beta is None:
        rolling_beta = calculate_rolling_beta(strat, spy, window)
    
    cumulative = []
    running_sum = 0.0
    
    for i in range(min_len):
        if i < window - 1 or np.isnan(rolling_beta[i]):
            cumulative.append(0.0)
        else:
            # Period alpha = strategy return - beta * market return
            period_alpha = strat[i] - rolling_beta[i] * spy[i]
            running_sum += period_alpha
            cumulative.append(float(running_sum))
    
    return cumulative


def calculate_information_ratio(
    strategy_returns: np.ndarray,
    spy_returns: np.ndarray
) -> Optional[float]:
    """
    Calculate Information Ratio (excess return / tracking error).
    
    IR measures risk-adjusted excess return relative to the benchmark.
    
    Args:
        strategy_returns: Array of strategy log returns
        spy_returns: Array of SPY log returns
    
    Returns:
        Information ratio or None if insufficient data
    """
    if len(strategy_returns) < 2 or len(spy_returns) < 2:
        return None
    
    min_len = min(len(strategy_returns), len(spy_returns))
    excess = strategy_returns[:min_len] - spy_returns[:min_len]
    
    tracking_error = np.std(excess, ddof=1)
    
    if tracking_error == 0:
        return None
    
    # Annualize
    bars_per_year = 78 * 252
    ir = (np.mean(excess) / tracking_error) * np.sqrt(bars_per_year)
    
    return float(ir)


# =============================================================================
# Standard Performance Metrics
# =============================================================================

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
    survival_time: int,
    spy_returns: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Calculate all performance metrics including CAPM alpha/beta.
    
    Args:
        equity_curve: List of equity values over time
        trades: List of trade records
        initial_equity: Starting equity
        survival_time: Number of ticks survived
        spy_returns: SPY log returns for alpha/beta calculation (optional)
    
    Returns:
        Dictionary with all metrics
    """
    final_equity = equity_curve[-1] if equity_curve else initial_equity
    total_return = (final_equity - initial_equity) / initial_equity * 100
    
    metrics = {
        'final_equity': final_equity,
        'total_return': total_return,
        'sharpe_ratio': calculate_sharpe_ratio(equity_curve),
        'max_drawdown': calculate_max_drawdown(equity_curve),
        'calmar_ratio': calculate_calmar_ratio(equity_curve),
        'sortino_ratio': calculate_sortino_ratio(equity_curve),
        'win_rate': calculate_win_rate(trades),
        'profit_factor': calculate_profit_factor(trades),
        'total_trades': len([t for t in trades if 'CLOSE' in t.get('action', '')]),
        'survival_time': survival_time,
        # CAPM metrics (will be None if spy_returns not provided)
        'alpha': None,
        'beta': None,
        'cumulative_alpha': [],
        'information_ratio': None
    }
    
    # Calculate CAPM metrics if SPY returns are available
    if spy_returns is not None and len(spy_returns) > 0:
        strategy_returns = calculate_strategy_returns(equity_curve)
        spy_returns_array = np.array(spy_returns)
        
        # Calculate beta
        beta = calculate_beta(strategy_returns, spy_returns_array)
        metrics['beta'] = beta
        
        # Calculate alpha
        metrics['alpha'] = calculate_alpha(strategy_returns, spy_returns_array, beta)
        
        # Calculate cumulative alpha
        metrics['cumulative_alpha'] = calculate_cumulative_alpha(
            strategy_returns, spy_returns_array
        )
        
        # Calculate information ratio
        metrics['information_ratio'] = calculate_information_ratio(
            strategy_returns, spy_returns_array
        )
    
    return metrics
