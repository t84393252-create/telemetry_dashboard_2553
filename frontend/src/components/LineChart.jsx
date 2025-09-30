import React, { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

const LineChartComponent = ({ metrics, metricType }) => {
  const chartData = useMemo(() => {
    const filtered = metrics.filter(m => m.metric_type === metricType)
    const grouped = {}
    
    filtered.forEach(metric => {
      const timeKey = new Date(metric.timestamp).getTime()
      const minuteKey = Math.floor(timeKey / 60000) * 60000
      
      if (!grouped[minuteKey]) {
        grouped[minuteKey] = {
          timestamp: new Date(minuteKey),
          values: []
        }
      }
      grouped[minuteKey].values.push(metric.value)
    })
    
    return Object.values(grouped)
      .map(group => {
        const sorted = group.values.sort((a, b) => a - b)
        const p50Index = Math.floor(sorted.length * 0.5)
        const p95Index = Math.floor(sorted.length * 0.95)
        const p99Index = Math.floor(sorted.length * 0.99)
        
        return {
          time: format(group.timestamp, 'HH:mm:ss'),
          p50: sorted[p50Index] || 0,
          p95: sorted[p95Index] || 0,
          p99: sorted[p99Index] || 0
        }
      })
      .slice(-30)
  }, [metrics, metricType])

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
              {entry.name}: {entry.value.toFixed(2)}ms
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4e" />
        <XAxis 
          dataKey="time" 
          stroke="#8a8a9a"
          style={{ fontSize: '12px' }}
        />
        <YAxis 
          stroke="#8a8a9a"
          style={{ fontSize: '12px' }}
          label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft', style: { fill: '#8a8a9a' } }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="p50" 
          stroke="#10b981" 
          strokeWidth={2}
          dot={false}
          name="P50"
        />
        <Line 
          type="monotone" 
          dataKey="p95" 
          stroke="#f59e0b" 
          strokeWidth={2}
          dot={false}
          name="P95"
        />
        <Line 
          type="monotone" 
          dataKey="p99" 
          stroke="#ef4444" 
          strokeWidth={2}
          dot={false}
          name="P99"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default LineChartComponent