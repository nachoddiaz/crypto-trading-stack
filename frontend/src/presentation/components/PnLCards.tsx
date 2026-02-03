// PnL Cards Component
import { PnLMetrics } from '../../domain/types'

interface Props {
    pnl: PnLMetrics
}

function formatPnL(value: number): string {
    const prefix = value >= 0 ? '+' : ''
    return `${prefix}${value.toFixed(2)}%`
}

export default function PnLCards({ pnl }: Props) {
    return (
        <div className="card">
            <div className="card-title">Performance</div>
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
            <div style={{ marginTop: '12px', textAlign: 'center' }}>
                <div className="pnl-label">Total</div>
                <div className={`card-value ${pnl.total >= 0 ? 'positive' : 'negative'}`}>
                    {formatPnL(pnl.total)}
                </div>
            </div>
        </div>
    )
}
