import React, { useMemo } from 'react'
import './Heatmap.css'

const HeatmapComponent = ({ metrics }) => {
  const heatmapData = useMemo(() => {
    const services = [...new Set(metrics.map(m => m.service))].sort()
    const metricTypes = ['latency', 'error_rate', 'throughput', 'cpu', 'memory']
    
    const data = {}
    services.forEach(service => {
      data[service] = {}
      metricTypes.forEach(type => {
        const serviceMetrics = metrics.filter(
          m => m.service === service && m.metric_type === type
        )
        
        if (serviceMetrics.length > 0) {
          const values = serviceMetrics.map(m => m.value)
          const avg = values.reduce((a, b) => a + b, 0) / values.length
          
          let health = 0
          if (type === 'latency') {
            health = avg < 100 ? 100 : avg < 500 ? 75 : avg < 1000 ? 50 : 25
          } else if (type === 'error_rate') {
            health = avg < 0.01 ? 100 : avg < 0.05 ? 75 : avg < 0.1 ? 50 : 25
          } else if (type === 'throughput') {
            health = avg > 1000 ? 100 : avg > 500 ? 75 : avg > 100 ? 50 : 25
          } else if (type === 'cpu' || type === 'memory') {
            health = avg < 50 ? 100 : avg < 70 ? 75 : avg < 85 ? 50 : 25
          }
          
          data[service][type] = {
            value: avg,
            health
          }
        } else {
          data[service][type] = { value: 0, health: 0 }
        }
      })
    })
    
    return { services, metricTypes, data }
  }, [metrics])

  const getColor = (health) => {
    if (health >= 90) return '#10b981'
    if (health >= 70) return '#84cc16'
    if (health >= 50) return '#f59e0b'
    if (health >= 25) return '#f97316'
    return '#ef4444'
  }

  const formatValue = (type, value) => {
    if (type === 'latency') return `${value.toFixed(0)}ms`
    if (type === 'error_rate') return `${(value * 100).toFixed(1)}%`
    if (type === 'throughput') return `${value.toFixed(0)}/s`
    if (type === 'cpu' || type === 'memory') return `${value.toFixed(0)}%`
    return value.toFixed(2)
  }

  return (
    <div className="heatmap-container">
      <div className="heatmap-grid">
        <div className="heatmap-header-cell"></div>
        {heatmapData.metricTypes.map(type => (
          <div key={type} className="heatmap-header-cell">
            {type.replace('_', ' ').toUpperCase()}
          </div>
        ))}
        
        {heatmapData.services.map(service => (
          <React.Fragment key={service}>
            <div className="heatmap-row-header">{service}</div>
            {heatmapData.metricTypes.map(type => {
              const cellData = heatmapData.data[service][type]
              return (
                <div
                  key={`${service}-${type}`}
                  className="heatmap-cell"
                  style={{
                    backgroundColor: getColor(cellData.health),
                    opacity: cellData.health > 0 ? 0.8 : 0.2
                  }}
                  title={`${service} - ${type}: ${formatValue(type, cellData.value)}`}
                >
                  <span className="heatmap-value">
                    {formatValue(type, cellData.value)}
                  </span>
                </div>
              )
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}

export default HeatmapComponent