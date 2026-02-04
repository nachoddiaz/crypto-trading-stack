// PnL Cards Component - Portfolio Performance
import { PnLMetrics } from '../../domain/types'

interface Props {
    pnl: PnLMetrics
}

function formatPnL(value: number): string {
    const prefix = value >= 0 ? '+' : ''
    return `${prefix}${value.toFixed(2)}%`
}

function formatUSD(value: number): string {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value)
}

export default function PnLCards({ pnl }: Props) {
    const equity = pnl.equity ?? 0
    const initialCapital = pnl.initial_capital ?? 0
    const pnlDollars = equity - initialCapital

    return (
        <div className="card">
            <div className="card-title">Portfolio Performance</div>

            {/* Equity y Capital Inicial */}
            <div className="equity-row">
                <div className="equity-item">
                    <div className="pnl-label">Capital Inicial</div>
                    <div className="equity-value">{formatUSD(initialCapital)}</div>
                </div>
                <div className="equity-item">
                    <div className="pnl-label">Equity Actual</div>
                    <div className={`equity-value ${pnlDollars >= 0 ? 'positive' : 'negative'}`}>
                        {formatUSD(equity)}
                    </div>
                </div>
                <div className="equity-item">
                    <div className="pnl-label">P&L ($)</div>
                    <div className={`equity-value ${pnlDollars >= 0 ? 'positive' : 'negative'}`}>
                        {pnlDollars >= 0 ? '+' : ''}{formatUSD(pnlDollars)}
                    </div>
                </div>
            </div>

            {/* PnL Porcentual */}
            <div className="pnl-grid">
                <div className="pnl-item">
                    <div className="pnl-label">Daily</div>
                    <div className={`pnl-value ${pnl.daily >= 0 ? 'positive' : 'negative'}`}>
                        {formatPnL(pnl.daily)}
                    </div>
                </div>
                <div className="pnl-item">
                    <div className="pnl-label">Monthly</div>
                    <div className={`pnl-value ${pnl.monthly >= 0 ? 'positive' : 'negative'}`}>
                        {formatPnL(pnl.monthly)}
                    </div>
                </div>
                <div className="pnl-item">
                    <div className="pnl-label">QTD</div>
                    <div className={`pnl-value ${pnl.qtd >= 0 ? 'positive' : 'negative'}`}>
                        {formatPnL(pnl.qtd)}
                    </div>
                </div>
                <div className="pnl-item">
                    <div className="pnl-label">YTD</div>
                    <div className={`pnl-value ${pnl.ytd >= 0 ? 'positive' : 'negative'}`}>
                        {formatPnL(pnl.ytd)}
                    </div>
                </div>
            </div>

            {/* Total y Trades */}
            <div className="total-row">
                <div className="total-item">
                    <div className="pnl-label">Total Return</div>
                    <div className={`card-value ${pnl.total >= 0 ? 'positive' : 'negative'}`}>
                        {formatPnL(pnl.total)}
                    </div>
                </div>
                {pnl.total_trades !== undefined && (
                    <div className="total-item">
                        <div className="pnl-label">Total Trades</div>
                        <div className="card-value">{pnl.total_trades}</div>
                    </div>
                )}
            </div>
        </div>
    )
}
