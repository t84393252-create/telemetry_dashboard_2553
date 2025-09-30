import React from 'react'
import { format } from 'date-fns'
import './AlertPanel.css'

const AlertPanel = ({ alerts }) => {
  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical': return '🔴'
      case 'warning': return '🟡'
      case 'info': return '🔵'
      default: return '⚪'
    }
  }

  const getSeverityClass = (severity) => {
    switch (severity) {
      case 'critical': return 'alert-critical'
      case 'warning': return 'alert-warning'
      case 'info': return 'alert-info'
      default: return ''
    }
  }

  if (alerts.length === 0) {
    return (
      <div className="alert-panel">
        <div className="no-alerts">
          <span className="no-alerts-icon">✅</span>
          <p>No active alerts</p>
          <span className="no-alerts-message">All systems operating normally</span>
        </div>
      </div>
    )
  }

  return (
    <div className="alert-panel">
      <div className="alerts-list">
        {alerts.map((alert, index) => (
          <div key={alert.id || index} className={`alert-item ${getSeverityClass(alert.severity)}`}>
            <div className="alert-header">
              <span className="alert-icon">{getSeverityIcon(alert.severity)}</span>
              <span className="alert-service">{alert.service}</span>
              <span className="alert-time">
                {format(new Date(alert.timestamp), 'HH:mm:ss')}
              </span>
            </div>
            <div className="alert-body">
              <div className="alert-message">{alert.message}</div>
              <div className="alert-details">
                <span className="alert-metric">{alert.metric_type}</span>
                <span className="alert-values">
                  Value: {alert.value.toFixed(2)} | Threshold: {alert.threshold}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default AlertPanel