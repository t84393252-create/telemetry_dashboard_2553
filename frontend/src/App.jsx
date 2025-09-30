import React, { useState, useEffect } from 'react'
import Select from 'react-select'
import { useMetrics } from './hooks/useMetrics'
import LineChartComponent from './components/LineChart'
import AreaChartComponent from './components/AreaChart'
import BarChartComponent from './components/BarChart'
import HeatmapComponent from './components/Heatmap'
import StatCards from './components/StatCards'
import AlertPanel from './components/AlertPanel'
import './App.css'

const timeRangeOptions = [
  { value: '5m', label: 'Last 5 minutes' },
  { value: '15m', label: 'Last 15 minutes' },
  { value: '1h', label: 'Last 1 hour' },
  { value: '6h', label: 'Last 6 hours' },
  { value: '24h', label: 'Last 24 hours' }
]

const customSelectStyles = {
  control: (base) => ({
    ...base,
    background: '#1a1a2e',
    borderColor: '#4a4a6a',
    color: '#e1e1e6',
    minHeight: 38
  }),
  menu: (base) => ({
    ...base,
    background: '#1a1a2e',
    border: '1px solid #4a4a6a'
  }),
  option: (base, state) => ({
    ...base,
    background: state.isFocused ? '#2a2a4e' : '#1a1a2e',
    color: '#e1e1e6',
    cursor: 'pointer'
  }),
  singleValue: (base) => ({
    ...base,
    color: '#e1e1e6'
  }),
  placeholder: (base) => ({
    ...base,
    color: '#8a8a9a'
  })
}

function App() {
  const { metrics, alerts, connected, error } = useMetrics()
  const [selectedTimeRange, setSelectedTimeRange] = useState(timeRangeOptions[0])
  const [selectedService, setSelectedService] = useState(null)
  const [services, setServices] = useState([])

  useEffect(() => {
    const uniqueServices = [...new Set(metrics.map(m => m.service))]
    const serviceOptions = [
      { value: null, label: 'All Services' },
      ...uniqueServices.map(s => ({ value: s, label: s }))
    ]
    setServices(serviceOptions)
  }, [metrics])

  const filteredMetrics = selectedService?.value 
    ? metrics.filter(m => m.service === selectedService.value)
    : metrics

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-content">
          <h1>Telemetry Dashboard</h1>
          <div className="header-controls">
            <div className="connection-status">
              <span className={`status-dot ${connected ? 'connected' : 'disconnected'}`} />
              {connected ? 'Connected' : 'Disconnected'}
            </div>
            <Select
              value={selectedService}
              onChange={setSelectedService}
              options={services}
              styles={customSelectStyles}
              placeholder="Select Service"
              className="service-select"
            />
            <Select
              value={selectedTimeRange}
              onChange={setSelectedTimeRange}
              options={timeRangeOptions}
              styles={customSelectStyles}
              className="time-select"
            />
          </div>
        </div>
      </header>

      <main className="dashboard">
        <div className="dashboard-grid">
          <div className="grid-item stats-section">
            <StatCards metrics={filteredMetrics} />
          </div>

          <div className="grid-item chart-section">
            <h2>Response Time Trends</h2>
            <LineChartComponent 
              metrics={filteredMetrics} 
              metricType="latency"
            />
          </div>

          <div className="grid-item chart-section">
            <h2>Request Throughput</h2>
            <AreaChartComponent 
              metrics={filteredMetrics}
              metricType="throughput"
            />
          </div>

          <div className="grid-item chart-section">
            <h2>Error Rates by Service</h2>
            <BarChartComponent 
              metrics={filteredMetrics}
              metricType="error_rate"
            />
          </div>

          <div className="grid-item heatmap-section">
            <h2>Service Health Matrix</h2>
            <HeatmapComponent metrics={filteredMetrics} />
          </div>

          <div className="grid-item alerts-section">
            <h2>Recent Alerts</h2>
            <AlertPanel alerts={alerts} />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App