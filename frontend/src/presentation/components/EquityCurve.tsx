// D3.js Equity Curve Chart
import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

interface DataPoint {
    date: Date
    value: number
}

export default function EquityCurve() {
    const svgRef = useRef<SVGSVGElement>(null)

    useEffect(() => {
        if (!svgRef.current) return

        // Mock data - TODO: conectar a API
        const data: DataPoint[] = Array.from({ length: 30 }, (_, i) => ({
            date: new Date(Date.now() - (30 - i) * 24 * 60 * 60 * 1000),
            value: 10000 + Math.random() * 2000 + i * 50,
        }))

        const margin = { top: 10, right: 10, bottom: 20, left: 40 }
        const width = svgRef.current.clientWidth - margin.left - margin.right
        const height = 120 - margin.top - margin.bottom

        // Clear previous
        d3.select(svgRef.current).selectAll('*').remove()

        const svg = d3.select(svgRef.current)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`)

        // Scales
        const x = d3.scaleTime()
            .domain(d3.extent(data, d => d.date) as [Date, Date])
            .range([0, width])

        const y = d3.scaleLinear()
            .domain([d3.min(data, d => d.value)! * 0.98, d3.max(data, d => d.value)! * 1.02])
            .range([height, 0])

        // Area gradient
        const gradient = svg.append('defs')
            .append('linearGradient')
            .attr('id', 'equityGradient')
            .attr('x1', '0%').attr('y1', '0%')
            .attr('x2', '0%').attr('y2', '100%')

        gradient.append('stop')
            .attr('offset', '0%')
            .attr('stop-color', '#3fb950')
            .attr('stop-opacity', 0.3)

        gradient.append('stop')
            .attr('offset', '100%')
            .attr('stop-color', '#3fb950')
            .attr('stop-opacity', 0)

        // Area
        const area = d3.area<DataPoint>()
            .x(d => x(d.date))
            .y0(height)
            .y1(d => y(d.value))
            .curve(d3.curveMonotoneX)

        svg.append('path')
            .datum(data)
            .attr('fill', 'url(#equityGradient)')
            .attr('d', area)

        // Line
        const line = d3.line<DataPoint>()
            .x(d => x(d.date))
            .y(d => y(d.value))
            .curve(d3.curveMonotoneX)

        svg.append('path')
            .datum(data)
            .attr('fill', 'none')
            .attr('stroke', '#3fb950')
            .attr('stroke-width', 2)
            .attr('d', line)

        // Y Axis
        svg.append('g')
            .attr('class', 'axis')
            .call(d3.axisLeft(y).ticks(3).tickFormat(d => `$${d3.format('.0s')(d)}`))
            .selectAll('text')
            .attr('fill', '#8b949e')
            .attr('font-size', '10px')

        svg.selectAll('.axis path, .axis line')
            .attr('stroke', '#30363d')

    }, [])

    return <svg ref={svgRef} className="d3-chart" />
}
