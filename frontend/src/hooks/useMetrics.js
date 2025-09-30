import { useState, useEffect, useRef, useCallback } from 'react'

const MAX_DATA_POINTS = 500

export const useMetrics = (wsUrl = 'ws://localhost:8000/ws/metrics') => {
  const [metrics, setMetrics] = useState([])
  const [alerts, setAlerts] = useState([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttempts = useRef(0)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
        setError(null)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          
          if (message.type === 'initial') {
            setMetrics(message.data.slice(-MAX_DATA_POINTS))
          } else if (message.type === 'metric') {
            setMetrics(prev => {
              const newMetrics = [...prev, message.data]
              return newMetrics.slice(-MAX_DATA_POINTS)
            })
          } else if (message.type === 'alert') {
            setAlerts(prev => {
              const newAlerts = [message.data, ...prev]
              return newAlerts.slice(0, 100)
            })
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('WebSocket error:', event)
        setError('Connection error')
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        wsRef.current = null

        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        reconnectAttempts.current++
        
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connect()
        }, delay)
      }
    } catch (err) {
      console.error('Error creating WebSocket:', err)
      setError(err.message)
    }
  }, [wsUrl])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [connect])

  const getMetricsByType = useCallback((metricType, service = null) => {
    return metrics.filter(m => {
      const typeMatch = m.metric_type === metricType
      const serviceMatch = !service || m.service === service
      return typeMatch && serviceMatch
    })
  }, [metrics])

  const getServiceMetrics = useCallback((service) => {
    return metrics.filter(m => m.service === service)
  }, [metrics])

  const getLatestMetrics = useCallback((count = 50) => {
    return metrics.slice(-count)
  }, [metrics])

  return {
    metrics,
    alerts,
    connected,
    error,
    getMetricsByType,
    getServiceMetrics,
    getLatestMetrics
  }
}