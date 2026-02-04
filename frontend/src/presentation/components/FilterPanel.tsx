// Filter Panel Component - Strategy and Date filters

interface Props {
    strategies: string[]
    selectedStrategy: string
    onStrategyChange: (strategy: string) => void
    startDate: string
    endDate: string
    onStartDateChange: (date: string) => void
    onEndDateChange: (date: string) => void
}

export default function FilterPanel({
    strategies,
    selectedStrategy,
    onStrategyChange,
    startDate,
    endDate,
    onStartDateChange,
    onEndDateChange
}: Props) {
    return (
        <div className="filter-panel">
            <div className="filter-group">
                <label htmlFor="strategy-filter">Estrategia:</label>
                <select
                    id="strategy-filter"
                    className="select-filter"
                    value={selectedStrategy}
                    onChange={(e) => onStrategyChange(e.target.value)}
                >
                    <option value="ALL">Todas</option>
                    {strategies.map(s => (
                        <option key={s} value={s}>{s}</option>
                    ))}
                </select>
            </div>

            <div className="filter-group">
                <label htmlFor="start-date">Desde:</label>
                <input
                    type="date"
                    id="start-date"
                    className="date-input"
                    value={startDate}
                    onChange={(e) => onStartDateChange(e.target.value)}
                />
            </div>

            <div className="filter-group">
                <label htmlFor="end-date">Hasta:</label>
                <input
                    type="date"
                    id="end-date"
                    className="date-input"
                    value={endDate}
                    onChange={(e) => onEndDateChange(e.target.value)}
                />
            </div>
        </div>
    )
}
