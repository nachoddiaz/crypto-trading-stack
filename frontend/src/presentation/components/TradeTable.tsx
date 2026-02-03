// Trade Table Component
import { Trade } from '../../domain/types'

interface Props {
    trades: Trade[]
}

function formatTime(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleString()
}

export default function TradeTable({ trades }: Props) {
    if (trades.length === 0) {
        return (
            <div style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                No hay trades ejecutados todavía
            </div>
        )
    }

    return (
        <table>
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Símbolo</th>
                    <th>Lado</th>
                    <th>Precio</th>
                    <th>Cantidad</th>
                    <th>Total USDT</th>
                </tr>
            </thead>
            <tbody>
                {trades.map((trade, i) => (
                    <tr key={i}>
                        <td>{formatTime(trade.timestamp)}</td>
                        <td>{trade.symbol}</td>
                        <td className={trade.side.toLowerCase()}>{trade.side}</td>
                        <td>${trade.price.toLocaleString()}</td>
                        <td>{trade.qty.toFixed(6)}</td>
                        <td>${trade.total_usdt.toFixed(2)}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    )
}
