import React, { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const BarChartComponent = ({ metrics, metricType }) => {
  const chartData = useMemo(() => {
    const filtered = metrics.filter(m => m.metric_type === metricType)
    const serviceData = {}
    
    filtered.forEach(metric => {
      if (!serviceData[metric.service]) {
        serviceData[metric.service] = []
      }
      serviceData[metric.service].push(metric.value)
    })
    
    return Object.entries(serviceData).map(([service, values]) => {
      const avg = values.reduce((a, b) => a + b, 0) / values.length
      return {
        service,
        errorRate: avg * 100,
        color: avg > 0.1 ? '#ef4444' : avg > 0.05 ? '#f59e0b' : '#10b981'
      }
    })
  }, [metrics, metricType])

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div style={{
          background: 'rgba(26, 26, 46, 0.95)',
          padding: '10px',
          border: '1px solid #4a4a6a',
          borderRadius: '4px'
        }}>
          <p style={{ color: '#e1e1e6', marginBottom: '5px' }}>{label}</p>
          <p style={{ color: data.color, margin: '2px 0' }}>
            Error Rate: {data.value.toFixed(2)}%
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4e" />
        <XAxis 
          dataKey="service" 
          stroke="#8a8a9a"
          style={{ fontSize: '12px' }}
        />
        <YAxis 
          stroke="#8a8a9a"
          style={{ fontSize: '12px' }}
          label={{ value: 'Error Rate (%)', angle: -90, position: 'insideLeft', style: { fill: '#8a8a9a' } }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="errorRate">
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default BarChartComponent