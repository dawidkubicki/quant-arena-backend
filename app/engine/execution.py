from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.engine.strategies.base import Action


@dataclass
class Trade:
    """Record of a single trade."""
    tick: int
    timestamp: Optional[datetime] = None  # Market timestamp (None for synthetic data)
    action: str = ""  # "OPEN_LONG", "CLOSE_LONG", "OPEN_SHORT", "CLOSE_SHORT"
    price: float = 0.0
    executed_price: float = 0.0  # Price after slippage
    size: float = 0.0
    cost: float = 0.0  # Transaction cost (fees)
    pnl: float = 0.0  # Realized P&L (0 for opening trades)
    equity_after: float = 0.0
    reason: str = ""


@dataclass
class Position:
    """Current position state."""
    action: Action = Action.FLAT
    entry_price: float = 0.0
    size: float = 0.0
    entry_tick: int = 0
    unrealized_pnl: float = 0.0


@dataclass
class ExecutionState:
    """Full state of the execution engine."""
    equity: float
    cash: float
    position: Position
    peak_equity: float
    max_drawdown: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    is_killed: bool = False
    kill_reason: str = ""


class ExecutionEngine:
    """
    Handles trade execution, position management, and risk controls.
    """
    
    def __init__(
        self,
        initial_equity: float,
        base_slippage: float = 0.001,
        fee_rate: float = 0.001
    ):
        self.initial_equity = initial_equity
        self.base_slippage = base_slippage
        self.fee_rate = fee_rate
        
        self.state = ExecutionState(
            equity=initial_equity,
            cash=initial_equity,
            position=Position(),
            peak_equity=initial_equity,
            max_drawdown=0.0,
            equity_curve=[initial_equity]
        )
    
    def calculate_slippage(self, price: float, action: Action, volatility: float = 0.02) -> float:
        """Calculate slippage based on volatility."""
        # Slippage increases with volatility
        slippage_multiplier = 1.0 + (volatility / 0.02 - 1.0) * 0.5
        slippage = self.base_slippage * slippage_multiplier
        
        if action == Action.LONG:
            # Buying - price goes up
            return price * (1 + slippage)
        elif action == Action.SHORT:
            # Selling/shorting - price goes down
            return price * (1 - slippage)
        return price
    
    def calculate_fees(self, notional_value: float) -> float:
        """Calculate transaction fees."""
        return notional_value * self.fee_rate
    
    def execute_trade(
        self,
        tick: int,
        target_action: Action,
        price: float,
        position_size: float,
        volatility: float,
        reason: str,
        risk_params: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> Optional[Trade]:
        """
        Execute a trade if conditions are met.
        Returns Trade object if executed, None otherwise.
        
        Args:
            tick: Tick number
            target_action: Desired position
            price: Current market price
            position_size: Size of position
            volatility: Current volatility
            reason: Reason for trade
            risk_params: Risk management parameters
            timestamp: Market timestamp (None for synthetic data)
        """
        if self.state.is_killed:
            return None
        
        current_position = self.state.position.action
        
        # No change in position
        if target_action == current_position:
            return None
        
        trade = None
        
        # Close existing position first
        if current_position != Action.FLAT:
            trade = self._close_position(tick, price, volatility, reason, timestamp)
        
        # Open new position if not going flat
        if target_action != Action.FLAT and not self.state.is_killed:
            # Calculate position size based on current equity
            max_position_value = self.state.equity * (risk_params.get('position_size_pct', 10) / 100)
            actual_size = min(position_size, max_position_value / price)
            
            if actual_size > 0:
                trade = self._open_position(tick, target_action, price, actual_size, volatility, reason, timestamp)
        
        return trade
    
    def _open_position(
        self,
        tick: int,
        action: Action,
        price: float,
        size: float,
        volatility: float,
        reason: str,
        timestamp: Optional[datetime] = None
    ) -> Trade:
        """Open a new position."""
        executed_price = self.calculate_slippage(price, action, volatility)
        notional = executed_price * size
        fees = self.calculate_fees(notional)
        
        # Update state
        self.state.cash -= notional + fees
        self.state.position = Position(
            action=action,
            entry_price=executed_price,
            size=size,
            entry_tick=tick
        )
        
        trade = Trade(
            tick=tick,
            timestamp=timestamp,
            action=f"OPEN_{action.value}",
            price=price,
            executed_price=executed_price,
            size=size,
            cost=fees,
            pnl=0.0,
            equity_after=self.state.equity,
            reason=reason
        )
        
        self.state.trades.append(trade)
        return trade
    
    def _close_position(
        self,
        tick: int,
        price: float,
        volatility: float,
        reason: str,
        timestamp: Optional[datetime] = None
    ) -> Trade:
        """Close current position."""
        pos = self.state.position
        
        # Calculate execution price (opposite of position direction)
        if pos.action == Action.LONG:
            executed_price = self.calculate_slippage(price, Action.SHORT, volatility)
        else:
            executed_price = self.calculate_slippage(price, Action.LONG, volatility)
        
        notional = executed_price * pos.size
        fees = self.calculate_fees(notional)
        
        # Calculate P&L
        if pos.action == Action.LONG:
            pnl = (executed_price - pos.entry_price) * pos.size - fees
        else:  # SHORT
            pnl = (pos.entry_price - executed_price) * pos.size - fees
        
        # Update cash based on position type
        # For LONG: we sell shares, receive exit notional minus fees
        # For SHORT: we return our invested position value, adjusted by P&L
        if pos.action == Action.LONG:
            self.state.cash += notional - fees
        else:  # SHORT
            # When we opened SHORT, we "invested" entry_price * size
            # Now we close and get back that investment +/- P&L
            # P&L already includes closing fees, so we add opening value + pnl
            self.state.cash += pos.entry_price * pos.size + pnl
        
        # Update equity immediately (since position is now FLAT, equity = cash)
        # This ensures correct position sizing if we immediately open a new position
        self.state.equity = self.state.cash
        
        trade = Trade(
            tick=tick,
            timestamp=timestamp,
            action=f"CLOSE_{pos.action.value}",
            price=price,
            executed_price=executed_price,
            size=pos.size,
            cost=fees,
            pnl=pnl,
            equity_after=self.state.cash,  # After close, equity = cash (no position)
            reason=reason
        )
        
        # Reset position
        self.state.position = Position()
        self.state.trades.append(trade)
        
        return trade
    
    def update_equity(self, current_price: float):
        """Update equity and track drawdown."""
        # Calculate unrealized P&L
        pos = self.state.position
        if pos.action == Action.LONG:
            unrealized = (current_price - pos.entry_price) * pos.size
        elif pos.action == Action.SHORT:
            unrealized = (pos.entry_price - current_price) * pos.size
        else:
            unrealized = 0.0
        
        pos.unrealized_pnl = unrealized
        
        # Total equity = cash + position value + unrealized P&L
        if pos.action != Action.FLAT:
            self.state.equity = self.state.cash + pos.entry_price * pos.size + unrealized
        else:
            self.state.equity = self.state.cash
        
        # Update peak and drawdown
        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity
        
        current_dd = (self.state.peak_equity - self.state.equity) / self.state.peak_equity * 100
        self.state.max_drawdown = max(self.state.max_drawdown, current_dd)
        
        # Record equity curve
        self.state.equity_curve.append(self.state.equity)
    
    def check_risk_limits(
        self,
        tick: int,
        current_price: float,
        risk_params: Dict[str, Any],
        volatility: float,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Check and enforce risk limits.
        Returns True if position was killed.
        
        Args:
            tick: Current tick number
            current_price: Current market price
            risk_params: Risk management parameters
            volatility: Current market volatility
            timestamp: Market timestamp (None for synthetic data)
        """
        if self.state.is_killed:
            return True
        
        pos = self.state.position
        if pos.action == Action.FLAT:
            return False
        
        stop_loss_pct = risk_params.get('stop_loss_pct', 5.0)
        take_profit_pct = risk_params.get('take_profit_pct', 10.0)
        max_dd_kill = risk_params.get('max_drawdown_kill', 20.0)
        
        # Calculate position P&L percentage
        if pos.action == Action.LONG:
            position_pnl_pct = (current_price - pos.entry_price) / pos.entry_price * 100
        else:
            position_pnl_pct = (pos.entry_price - current_price) / pos.entry_price * 100
        
        # Stop loss hit
        if position_pnl_pct <= -stop_loss_pct:
            self._close_position(tick, current_price, volatility, f"Stop loss hit ({position_pnl_pct:.2f}%)", timestamp)
            return False
        
        # Take profit hit
        if position_pnl_pct >= take_profit_pct:
            self._close_position(tick, current_price, volatility, f"Take profit hit ({position_pnl_pct:.2f}%)", timestamp)
            return False
        
        # Max drawdown kill switch
        if self.state.max_drawdown >= max_dd_kill:
            # Close any position and kill the agent
            if pos.action != Action.FLAT:
                self._close_position(tick, current_price, volatility, "Max drawdown kill switch", timestamp)
            self.state.is_killed = True
            self.state.kill_reason = f"Max drawdown ({self.state.max_drawdown:.2f}%) exceeded limit ({max_dd_kill}%)"
            return True
        
        return False
    
    def get_results(self) -> Dict[str, Any]:
        """Get final execution results."""
        return {
            'final_equity': self.state.equity,
            'initial_equity': self.initial_equity,
            'total_return': (self.state.equity - self.initial_equity) / self.initial_equity * 100,
            'max_drawdown': self.state.max_drawdown,
            'total_trades': len([t for t in self.state.trades if 'CLOSE' in t.action]),
            'equity_curve': self.state.equity_curve,
            'trades': [
                {
                    'tick': t.tick,
                    'timestamp': t.timestamp,
                    'action': t.action,
                    'price': t.price,
                    'executed_price': t.executed_price,
                    'size': t.size,
                    'cost': t.cost,
                    'pnl': t.pnl,
                    'equity_after': t.equity_after,
                    'reason': t.reason
                }
                for t in self.state.trades
            ],
            'is_killed': self.state.is_killed,
            'kill_reason': self.state.kill_reason
        }
