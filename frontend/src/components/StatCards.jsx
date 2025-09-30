import React, { useMemo } from 'react'
import './StatCards.css'

const StatCards = ({ metrics }) => {
  const stats = useMemo(() => {
    const latencyMetrics = metrics.filter(m => m.metric_type === 'latency')
    const throughputMetrics = metrics.filter(m => m.metric_type === 'throughput')
    const errorMetrics = metrics.filter(m => m.metric_type === 'error_rate')
    const cpuMetrics = metrics.filter(m => m.metric_type === 'cpu')
    
    const getLatest = (metricsList) => {
      if (metricsList.length === 0) return 0
      return metricsList[metricsList.length - 1].value
    }
    
    const getAverage = (metricsList) => {
      if (metricsList.length === 0) return 0
      const sum = metricsList.reduce((acc, m) => acc + m.value, 0)
      return sum / metricsList.length
    }
    
    return {
      avgLatency: getAverage(latencyMetrics),
      currentLatency: getLatest(latencyMetrics),
      avgThroughput: getAverage(throughputMetrics),
      currentThroughput: getLatest(throughputMetrics),
      avgErrorRate: getAverage(errorMetrics) * 100,
      currentErrorRate: getLatest(errorMetrics) * 100,
      avgCpu: getAverage(cpuMetrics),
      currentCpu: getLatest(cpuMetrics),
      totalMetrics: metrics.length,
      activeServices: [...new Set(metrics.map(m => m.service))].length
    }
  }, [metrics])

  const cards = [
    {
      title: 'Avg Latency',
      value: `${stats.avgLatency.toFixed(0)}ms`,
      current: `${stats.currentLatency.toFixed(0)}ms`,
      icon: '⚡',
      color: stats.avgLatency < 100 ? 'success' : stats.avgLatency < 500 ? 'warning' : 'danger'
    },
    {
      title: 'Throughput',
      value: `${stats.avgThroughput.toFixed(0)}/s`,
      current: `${stats.currentThroughput.toFixed(0)}/s`,
      icon: '📊',
      color: stats.avgThroughput > 1000 ? 'success' : stats.avgThroughput > 500 ? 'warning' : 'danger'
    },
    {
      title: 'Error Rate',
      value: `${stats.avgErrorRate.toFixed(2)}%`,
      current: `${stats.currentErrorRate.toFixed(2)}%`,
      icon: '⚠️',
      color: stats.avgErrorRate < 1 ? 'success' : stats.avgErrorRate < 5 ? 'warning' : 'danger'
    },
    {
      title: 'CPU Usage',
      value: `${stats.avgCpu.toFixed(0)}%`,
      current: `${stats.currentCpu.toFixed(0)}%`,
      icon: '💻',
      color: stats.avgCpu < 60 ? 'success' : stats.avgCpu < 80 ? 'warning' : 'danger'
    },
    {
      title: 'Active Services',
      value: stats.activeServices,
      current: 'services',
      icon: '🔧',
      color: 'info'
    },
    {
      title: 'Total Metrics',
      value: stats.totalMetrics.toLocaleString(),
      current: 'data points',
      icon: '📈',
      color: 'info'
    }
  ]

  return (
    <div className="stat-cards">
      {cards.map((card, index) => (
        <div key={index} className={`stat-card ${card.color}`}>
          <div className="stat-icon">{card.icon}</div>
          <div className="stat-content">
            <div className="stat-title">{card.title}</div>
            <div className="stat-value">{card.value}</div>
            <div className="stat-current">Current: {card.current}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default StatCards