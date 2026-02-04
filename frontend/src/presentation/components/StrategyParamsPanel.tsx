// Strategy Params Panel - Shows parameters for selected symbol only
import { useEffect, useState } from 'react'

interface StrategyParamsProps {
    strategy: string
    symbol: string
}

interface ParamValues {
    fast?: number
    slow?: number
    period?: number
    threshold?: number
    trend_ema?: number
}

export default function StrategyParamsPanel({ strategy, symbol }: StrategyParamsProps) {
    const [params, setParams] = useState<ParamValues | null>(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (strategy === 'ALL') {
            setParams(null)
            return
        }

        setLoading(true)
        fetch(`/api/strategy-params?strategy=${strategy}`)
            .then(res => res.json())
            .then(data => {
                // Solo mostrar el símbolo seleccionado
                const symbolParams = data.params?.[symbol] || null
                setParams(symbolParams)
                setLoading(false)
            })
            .catch(() => setLoading(false))
    }, [strategy, symbol])

    if (strategy === 'ALL') {
        return null
    }

    if (loading) {
        return <div className="strategy-params-loading">Cargando...</div>
    }

    if (!params) {
        return <div className="strategy-params-empty">Sin parámetros para {symbol}</div>
    }

    // Renderizar según estrategia
    const renderParams = () => {
        switch (strategy) {
            case 'SMA':
                return (
                    <div className="params-row">
                        <div className="param-item">
                            <span className="param-label">MA Rápida</span>
                            <span className="param-value fast-ma">{params.fast}</span>
                        </div>
                        <div className="param-item">
                            <span className="param-label">MA Lenta</span>
                            <span className="param-value slow-ma">{params.slow}</span>
                        </div>
                    </div>
                )
            case 'MOMENTUM':
                return (
                    <div className="params-row">
                        <div className="param-item">
                            <span className="param-label">Período</span>
                            <span className="param-value">{params.period}</span>
                        </div>
                        <div className="param-item">
                            <span className="param-label">Umbral</span>
                            <span className="param-value">{((params.threshold || 0) * 100).toFixed(2)}%</span>
                        </div>
                    </div>
                )
            case 'ENGULFING':
                return (
                    <div className="params-row">
                        <div className="param-item">
                            <span className="param-label">EMA Tendencia</span>
                            <span className="param-value">{params.trend_ema}</span>
                        </div>
                    </div>
                )
            default:
                return null
        }
    }

    return (
        <div className="strategy-params-inline">
            {renderParams()}
        </div>
    )
}
