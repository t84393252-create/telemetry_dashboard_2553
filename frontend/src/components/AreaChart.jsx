import React, { useMemo } from 'react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

const AreaChartComponent = ({ metrics, metricType }) => {
  const chartData = useMemo(() => {
    const filtered = metrics.filter(m => m.metric_type === metricType)
    const grouped = {}
    
    filtered.forEach(metric => {
      const timeKey = new Date(metric.timestamp).getTime()
      const minuteKey = Math.floor(timeKey / 60000) * 60000
      
      if (!grouped[minuteKey]) {
        grouped[minuteKey] = {
          timestamp: new Date(minuteKey),
          services: {}
        }
      }
      
      if (!grouped[minuteKey].services[metric.service]) {
        grouped[minuteKey].services[metric.service] = []
      }
      grouped[minuteKey].services[metric.service].push(metric.value)
    })
    
    const services = [...new Set(filtered.map(m => m.service))]
    
    return Object.entries(grouped)
      .map(([key, data]) => {
        const result = {
          time: format(data.timestamp, 'HH:mm:ss')
        }
        
        services.forEach(service => {
          const values = data.services[service] || []
          result[service] = values.length > 0 
            ? values.reduce((a, b) => a + b, 0) / values.length 
            : 0
        })
        
        return result
      })
      .slice(-30)
  }, [metrics, metricType])

  const services = useMemo(() => {
    return [...new Set(metrics.filter(m => m.metric_type === metricType).map(m => m.service))]
  }, [metrics, metricType])

  const colors = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6']

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          background: 'rgba(26, 26, 46, 0.95)',
          padding: '10px',
          border: '1px solid #4a4a6a',
          borderRadius: '4px'
        }}>
          <p style={{ color: '#e1e1e6', marginBottom: '5px' }}>{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color, margin: '2px 0' }}>
              {entry.name}: {entry.value.toFixed(0)} req/s
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4e" />
        <XAxis 
          dataKey="time" 
          stroke="#8a8a9a"
          style={{ fontSize: '12px' }}
        />
        <YAxis 
          stroke="#8a8a9a"
          style={{ fontSize: '12px' }}
          label={{ value: 'Throughput (req/s)', angle: -90, position: 'insideLeft', style: { fill: '#8a8a9a' } }}
        />
        <Tooltip content={<CustomTooltip />} />
        {services.map((service, index) => (
          <Area
            key={service}
            type="monotone"
            dataKey={service}
            stackId="1"
            stroke={colors[index % colors.length]}
            fill={colors[index % colors.length]}
            fillOpacity={0.6}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default AreaChartComponent