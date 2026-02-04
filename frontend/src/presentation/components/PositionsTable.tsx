// Positions Table Component - Similar to TradeTable but for current positions
import { Position } from '../../domain/types'

interface Props {
    positions: Position[]
}

export default function PositionsTable({ positions }: Props) {
    if (!positions || positions.length === 0) {
        return (
            <div style={{ padding: '20px', textAlign: 'center', color: '#8b949e' }}>
                No hay posiciones abiertas
            </div>
        )
    }

    return (
        <table>
            <thead>
                <tr>
                    <th>Símbolo</th>
                    <th>Cantidad</th>
                    <th>Último Precio</th>
                    <th>Side</th>
                </tr>
            </thead>
            <tbody>
                {positions.map((pos, i) => {
                    // Soporte para ambos formatos: qty (antiguo) y quantity (nuevo)
                    const quantity = pos.qty ?? pos.quantity ?? 0
                    const lastTrade = pos.last_trade
                    const price = lastTrade?.price ?? pos.current_price ?? 0
                    const side = lastTrade?.side ?? 'N/A'

                    return (
                        <tr key={i}>
                            <td>{pos.symbol}</td>
                            <td>{typeof quantity === 'number' ? quantity.toFixed(6) : quantity}</td>
                            <td>${typeof price === 'number' ? price.toLocaleString() : price}</td>
                            <td className={side === 'BUY' ? 'buy' : side === 'SELL' ? 'sell' : ''}>
                                {side}
                            </td>
                        </tr>
                    )
                })}
            </tbody>
        </table>
    )
}
