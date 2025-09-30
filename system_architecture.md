# Telemetry Dashboard System Architecture

## System Overview Diagram

```mermaid
graph TB
    subgraph "Docker Network - telemetry-network"
        subgraph "Backend Container [:8000]"
            GEN[("📊 Metrics Generator<br/>Simulates 5 services")]
            PROC[["🔍 Processor<br/>• Anomaly Detection<br/>• Aggregation<br/>• Statistics"]]
            API{{"🚀 FastAPI Server<br/>• REST Endpoints<br/>• WebSocket Server"}}
            STORE[("💾 SQLite Storage<br/>• Metrics DB<br/>• 24hr retention"]]
            MGR[["📡 Connection Manager<br/>WebSocket Handler"]]
        end
        
        subgraph "Frontend Container [:3000]"
            VITE[["⚡ Vite Dev Server"]]
            REACT[["⚛️ React App"]]
            HOOK[["🔄 useMetrics Hook<br/>WebSocket Client"]]
            
            subgraph "UI Components"
                CARDS["📊 StatCards"]
                LINE["📈 LineChart"]
                AREA["📉 AreaChart"]
                BAR["📊 BarChart"]
                HEAT["🗺️ Heatmap"]
                ALERT["🚨 AlertPanel"]
            end
        end
    end
    
    BROWSER[["🌐 Browser"]]
    
    %% Data Flow
    GEN -.->|"Generate<br/>1/sec"| PROC
    PROC -->|Store| STORE
    PROC -->|Detect<br/>Anomalies| MGR
    STORE <-->|Query| API
    MGR <-->|Broadcast| API
    API <===>|"WebSocket<br/>ws://localhost:8000/ws/metrics"| HOOK
    API <-->|"REST API<br/>http://localhost:8000"| REACT
    VITE -->|Serve| REACT
    REACT -->|Render| CARDS & LINE & AREA & BAR & HEAT & ALERT
    BROWSER <-->|":3000"| VITE
    HOOK -->|"Real-time<br/>Updates"| CARDS & LINE & AREA & BAR & HEAT & ALERT

    classDef backend fill:#2a2a4e,stroke:#4a4a6a,color:#e1e1e6
    classDef frontend fill:#1a3a2e,stroke:#2a5a3e,color:#e1e1e6
    classDef storage fill:#3a2a1e,stroke:#5a4a3e,color:#e1e1e6
    
    class GEN,PROC,API,MGR backend
    class VITE,REACT,HOOK,CARDS,LINE,AREA,BAR,HEAT,ALERT frontend
    class STORE storage
```

## Data Flow Walkthrough

### 1️⃣ **Metric Generation Phase**
```
Generator (1/sec) → Creates 25 metrics → 5 services × 5 metric types
```

The **MetricsGenerator** simulates realistic telemetry:
- **Services**: auth, api, database, cache, queue
- **Metrics**: latency, throughput, error_rate, cpu, memory
- **Patterns**: Sine waves (daily cycles), random spikes, gradual trends

### 2️⃣ **Processing Pipeline**
```
Raw Metric → Processor → [Buffer | Storage | Anomaly Check]
```

Each metric flows through:
1. **Buffer** - In-memory deque (1000 items max per service/type)
2. **Storage** - SQLite persistence for historical queries
3. **Anomaly Detection** - Threshold checking → Alert generation

### 3️⃣ **Real-time Broadcasting**
```
Metric/Alert → Connection Manager → All WebSocket Clients
```

**WebSocket Message Types**:
```json
// Initial connection
{
  "type": "initial",
  "data": [/* last 50 metrics */]
}

// Live metric
{
  "type": "metric",
  "data": {
    "timestamp": "2024-01-29T10:30:00",
    "service": "api",
    "metric_type": "latency",
    "value": 125.4
  }
}

// Alert
{
  "type": "alert",
  "data": {
    "severity": "critical",
    "message": "latency threshold exceeded for api",
    "value": 1250,
    "threshold": 1000
  }
}
```

### 4️⃣ **Frontend Consumption**
```
WebSocket → useMetrics Hook → React State → Components Re-render
```

The **useMetrics** hook:
- Maintains WebSocket connection with auto-reconnect
- Buffers last 500 data points
- Provides filtered data access methods
- Updates React state → triggers re-renders

### 5️⃣ **Visualization Layer**
```
Metrics Array → Component → Data Transform → Chart Library → SVG/Canvas
```

Each component:
- Filters relevant metric type
- Transforms data for chart format
- Renders using visualization libraries
- Updates in real-time as new data arrives

## API Endpoints

### REST API
```
GET  /metrics/health     → Health check
POST /metrics/ingest     → Manual metric ingestion
POST /metrics/query      → Historical queries
GET  /metrics/services   → Service status & statistics
GET  /metrics/alerts     → Recent alerts

WebSocket /ws/metrics    → Real-time stream
```

## Data Persistence

### SQLite Schema
```sql
metrics table:
- timestamp (indexed)
- service (indexed)
- metric_type
- value
- tags (JSON)

aggregated_metrics table:
- timestamp, service, metric_type
- interval (1m/5m/1h)
- p50, p95, p99, min, max, avg, count
```

### Retention Policy
- **Raw metrics**: 24 hours (cleanup task)
- **Aggregated**: 7 days
- **In-memory buffer**: Last 1000 per metric/service

## Anomaly Detection Thresholds

| Metric Type | Warning | Critical |
|------------|---------|----------|
| Latency | >500ms | >1000ms |
| Error Rate | >5% | >10% |
| CPU | >80% | >95% |
| Memory | >80% | >95% |
| Throughput | <100 req/s | <50 req/s |

## Docker Networking

```yaml
Backend → Port 8000 → Exposed to host
Frontend → Port 3000 → Exposed to host
Internal → Bridge network → Service discovery by name
```

The frontend container connects to backend using internal hostname:
- External: `http://localhost:8000`
- Internal: `http://backend:8000`

## System Startup Sequence

1. Docker Compose starts both containers
2. Backend initializes SQLite database
3. Backend starts FastAPI server
4. Generator begins producing metrics
5. Frontend Vite server starts
6. Browser loads React app
7. WebSocket connection established
8. Initial metrics batch received
9. Real-time updates begin flowing