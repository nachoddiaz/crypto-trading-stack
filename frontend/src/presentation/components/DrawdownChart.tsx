// D3.js Drawdown Chart
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

interface DataPoint {
    date: Date
    drawdown: number
}

export default function DrawdownChart() {
    const svgRef = useRef<SVGSVGElement>(null)

    useEffect(() => {
        if (!svgRef.current) return

        // Mock data - TODO: calcular desde equity curve real
        const data: DataPoint[] = Array.from({ length: 30 }, (_, i) => ({
            date: new Date(Date.now() - (30 - i) * 24 * 60 * 60 * 1000),
            drawdown: -Math.random() * 5, // Drawdown siempre negativo
        }))

        const margin = { top: 10, right: 10, bottom: 20, left: 40 }
        const width = svgRef.current.clientWidth - margin.left - margin.right
        const height = 120 - margin.top - margin.bottom

        d3.select(svgRef.current).selectAll('*').remove()

        const svg = d3.select(svgRef.current)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`)

        const x = d3.scaleTime()
            .domain(d3.extent(data, d => d.date) as [Date, Date])
            .range([0, width])

        const y = d3.scaleLinear()
            .domain([d3.min(data, d => d.drawdown)! * 1.1, 0])
            .range([height, 0])

        // Gradient
        const gradient = svg.append('defs')
            .append('linearGradient')
            .attr('id', 'ddGradient')
            .attr('x1', '0%').attr('y1', '0%')
            .attr('x2', '0%').attr('y2', '100%')

        gradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#f85149')
            .attr('stop-opacity', 0)

        gradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#f85149')
            .attr('stop-opacity', 0.4)

        // Area (inverted - from 0 down)
        const area = d3.area<DataPoint>()
            .x(d => x(d.date))
            .y0(y(0))
            .y1(d => y(d.drawdown))
            .curve(d3.curveMonotoneX)

        svg.append('path')
            .datum(data)
            .attr('fill', 'url(#ddGradient)')
            .attr('d', area)

        // Line
        const line = d3.line<DataPoint>()
            .x(d => x(d.date))
            .y(d => y(d.drawdown))
            .curve(d3.curveMonotoneX)

        svg.append('path')
            .datum(data)
            .attr('fill', 'none')
            .attr('stroke', '#f85149')
            .attr('stroke-width', 2)
            .attr('d', line)

        // Zero line
        svg.append('line')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', y(0))
            .attr('y2', y(0))
            .attr('stroke', '#30363d')
            .attr('stroke-dasharray', '3,3')

        // Y Axis
        svg.append('g')
            .attr('class', 'axis')
            .call(d3.axisLeft(y).ticks(3).tickFormat(d => `${d}%`))
            .selectAll('text')
            .attr('fill', '#8b949e')
            .attr('font-size', '10px')

        svg.selectAll('.axis path, .axis line')
            .attr('stroke', '#30363d')

    }, [])

    return <svg ref={svgRef} className="d3-chart" />
}
