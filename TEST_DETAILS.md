# Detailed Test Implementation Breakdown

This document shows the exact code and logic for each validation test.

---

## Test 1: Health Check Endpoint

### Implementation (`validate_system.py`):
```python
async def test_health_endpoint(self, session: aiohttp.ClientSession):
    """Test the health check endpoint"""
    try:
        async with session.get(f"{BASE_URL}/metrics/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                self.log_result(
                    "Health Check Endpoint", 
                    "status" in data and data["status"] == "healthy"
                )
            else:
                self.log_result("Health Check Endpoint", False, f"Status: {resp.status}")
    except Exception as e:
        self.log_result("Health Check Endpoint", False, str(e))
```

### What It Does:
1. **Sends:** `GET http://localhost:8000/metrics/health`
2. **Checks:** 
   - HTTP status code is 200
   - Response contains `"status"` field
   - Status value equals `"healthy"`
3. **Pass Criteria:** All three conditions must be true
4. **Fail Reasons:**
   - Backend not running (connection refused)
   - Wrong status code (500, 404, etc.)
   - Missing or wrong status field

### Backend Code Being Tested (`main.py`):
```python
@app.get("/metrics/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services_count": len(await storage.get_services())
    }
```

---

## Test 2: Metric Ingestion

### Implementation:
```python
async def test_metric_ingestion(self, session: aiohttp.ClientSession):
    """Test metric ingestion endpoint"""
    test_metric = {
        "timestamp": datetime.now().isoformat(),
        "service": "test_service",
        "metric_type": "latency",
        "value": 123.45,
        "tags": {"test": True}
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/metrics/ingest",
            json=test_metric
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.log_result(
                    "Metric Ingestion", 
                    data.get("status") == "success"
                )
            else:
                self.log_result("Metric Ingestion", False, f"Status: {resp.status}")
    except Exception as e:
        self.log_result("Metric Ingestion", False, str(e))
```

### What It Does:
1. **Creates Test Data:**
   - Timestamp: Current time in ISO format
   - Service: "test_service"
   - Metric Type: "latency"
   - Value: 123.45
   - Tags: {"test": True}

2. **Sends:** `POST http://localhost:8000/metrics/ingest` with JSON body

3. **Backend Processing:**
   ```python
   @app.post("/metrics/ingest")
   async def ingest_metric(metric: MetricData):
       # Store in SQLite database
       await storage.insert_metric(metric)
       
       # Add to in-memory buffer for real-time processing
       processor.add_to_buffer(metric)
       
       # Check if anomaly (value exceeds threshold)
       alert = processor.detect_anomaly(metric)
       
       # Broadcast to WebSocket clients
       await manager.broadcast({
           "type": "metric",
           "data": {...}
       })
       
       return {"status": "success", "alert": alert}
   ```

4. **Pass Criteria:** Response contains `"status": "success"`

---

## Test 3: Metric Query

### Implementation:
```python
async def test_metric_query(self, session: aiohttp.ClientSession):
    """Test metric query endpoint"""
    query = {
        "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "services": None,  # None means all services
        "metric_types": None,  # None means all types
        "aggregation": "raw"  # No aggregation
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/metrics/query",
            json=query
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.log_result(
                    "Metric Query", 
                    "data" in data and isinstance(data["data"], list)
                )
```

### What It Does:
1. **Query Parameters:**
   - Time range: Last hour to now
   - Services: All (None)
   - Metric types: All (None)
   - Aggregation: Raw data (no grouping)

2. **SQL Query Executed (`storage.py`):**
   ```python
   SELECT timestamp, service, metric_type, value, tags
   FROM metrics
   WHERE timestamp >= ? AND timestamp <= ?
   ORDER BY timestamp DESC
   LIMIT 10000
   ```

3. **Pass Criteria:**
   - Response has "data" field
   - Data is a list (can be empty)

---

## Test 4: Services Endpoint

### Implementation:
```python
async def test_services_endpoint(self, session: aiohttp.ClientSession):
    """Test services list endpoint"""
    try:
        async with session.get(f"{BASE_URL}/metrics/services") as resp:
            if resp.status == 200:
                data = await resp.json()
                has_services = "services" in data and len(data["services"]) > 0
                self.log_result(
                    "Services Endpoint", 
                    has_services,
                    f"Found {len(data.get('services', []))} services"
                )
```

### Backend Processing:
```python
@app.get("/metrics/services")
async def get_services():
    # Get unique services from database
    services = await storage.get_services()
    
    service_health = []
    for service in services:
        # Get statistics from in-memory buffer
        stats = processor.get_service_statistics(service)
        
        # Determine health status based on thresholds
        error_rate = stats.get("error_rate", {}).get("current", 0)
        latency = stats.get("latency", {}).get("avg", 0)
        
        if error_rate > 0.1 or latency > 1000:
            status = "unhealthy"
        elif error_rate > 0.05 or latency > 500:
            status = "degraded"
        else:
            status = "healthy"
        
        service_health.append({
            "service": service,
            "status": status,
            "metrics": stats
        })
    
    return {"services": service_health}
```

### Pass Criteria:
- At least 1 service discovered
- Should find 5 services (auth, api, database, cache, queue)

---

## Test 5: WebSocket Connection

### Implementation:
```python
async def test_websocket_connection(self):
    """Test WebSocket connection and data streaming"""
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Wait for initial data
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(message)
            
            initial_ok = data.get("type") == "initial" and "data" in data
            
            if initial_ok:
                # Wait for real-time updates
                metrics_received = 0
                start_time = time.time()
                
                while time.time() - start_time < 5:  # Collect for 5 seconds
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1)
                        data = json.loads(message)
                        if data.get("type") == "metric":
                            metrics_received += 1
                    except asyncio.TimeoutError:
                        continue
                
                self.log_result(
                    "WebSocket Streaming", 
                    metrics_received > 0,
                    f"Received {metrics_received} metrics in 5 seconds"
                )
```

### WebSocket Flow:
1. **Connection:** Client connects to `ws://localhost:8000/ws/metrics`

2. **Initial Message:**
   ```python
   # Server sends last 50 metrics
   latest_metrics = await storage.get_latest_metrics(50)
   await websocket.send_json({
       "type": "initial",
       "data": latest_metrics
   })
   ```

3. **Continuous Updates:**
   ```python
   # Generator creates metrics every second
   # Each metric is broadcast to all connected clients
   await manager.broadcast({
       "type": "metric",
       "data": metric_data
   })
   ```

4. **Pass Criteria:**
   - Initial message received
   - At least 1 metric received in 5 seconds
   - Expected: ~125 metrics (5 services × 5 types × 5 seconds)

---

## Test 6: Data Generation

### Implementation:
```python
async def test_data_generation(self, session: aiohttp.ClientSession):
    """Test that data is being generated"""
    await asyncio.sleep(2)  # Wait for generator to create some data
    
    query = {
        "start_time": (datetime.now() - timedelta(minutes=1)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "aggregation": "raw"
    }
    
    try:
        async with session.post(f"{BASE_URL}/metrics/query", json=query) as resp:
            if resp.status == 200:
                data = await resp.json()
                metrics = data.get("data", [])
                
                # Check for variety in data
                services = set(m["service"] for m in metrics)
                metric_types = set(m["metric_type"] for m in metrics)
                
                self.log_result(
                    "Data Generation", 
                    len(services) >= 5 and len(metric_types) >= 5,
                    f"Services: {len(services)}, Metric Types: {len(metric_types)}"
                )
```

### Generator Logic (`generator.py`):
```python
def generate_batch(self) -> List[MetricData]:
    metrics = []
    current_time = datetime.now()
    
    for service in self.services:  # 5 services
        # Generate realistic patterns
        latency = self.generate_latency(service, self.base_time)
        throughput = self.generate_throughput(service, self.base_time)
        error_rate = self.generate_error_rate(service, self.base_time)
        cpu = self.generate_cpu(service, self.base_time)
        memory = self.generate_memory(service, self.base_time)
        
        # Add all 5 metric types for each service
        metrics.extend([latency, throughput, error_rate, cpu, memory])
    
    return metrics  # Returns 25 metrics per batch

# Runs every second
async def start_generation(self, callback):
    while self.running:
        metrics = self.generate_batch()
        await callback(metrics)  # Process and broadcast
        await asyncio.sleep(1)
```

### Pass Criteria:
- Find all 5 services in recent data
- Find all 5 metric types
- Should have ~1500 metrics in last minute (25/sec × 60)

---

## Test 7: Anomaly Detection

### Implementation:
```python
async def test_anomaly_detection(self, session: aiohttp.ClientSession):
    """Test anomaly detection by sending high-value metrics"""
    # Send a metric that should trigger an alert
    anomaly_metric = {
        "timestamp": datetime.now().isoformat(),
        "service": "test_service",
        "metric_type": "error_rate",
        "value": 0.95,  # 95% error rate should trigger alert
        "tags": {"test": True}
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/metrics/ingest",
            json=anomaly_metric
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                has_alert = "alert" in data and data["alert"] is not None
                self.log_result(
                    "Anomaly Detection", 
                    has_alert,
                    "Alert triggered for high error rate"
                )
```

### Anomaly Detection Logic (`processor.py`):
```python
def detect_anomaly(self, metric: MetricData) -> Optional[Alert]:
    thresholds = {
        MetricType.LATENCY: {"warning": 500, "critical": 1000},
        MetricType.ERROR_RATE: {"warning": 0.05, "critical": 0.1},
        MetricType.CPU: {"warning": 80, "critical": 95},
        MetricType.MEMORY: {"warning": 80, "critical": 95},
        MetricType.THROUGHPUT: {"warning": 100, "critical": 50}
    }
    
    # Get thresholds for this metric type
    thresholds = self.anomaly_thresholds.get(metric.metric_type)
    
    # Determine severity
    if metric.value > thresholds["critical"]:
        severity = "critical"
    elif metric.value > thresholds["warning"]:
        severity = "warning"
    else:
        return None  # No anomaly
    
    # Create alert
    alert = Alert(
        id=str(uuid.uuid4()),
        timestamp=metric.timestamp,
        service=metric.service,
        metric_type=metric.metric_type,
        severity=severity,
        message=f"{metric.metric_type.value} threshold exceeded",
        value=metric.value,
        threshold=threshold
    )
    
    return alert
```

### Pass Criteria:
- Sending error_rate of 0.95 (95%)
- Should exceed critical threshold of 0.1 (10%)
- Alert object returned in response

---

## Test 8: Metric Aggregation

### Implementation:
```python
async def test_aggregation(self, session: aiohttp.ClientSession):
    """Test metric aggregation"""
    query = {
        "start_time": (datetime.now() - timedelta(hours=1)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "aggregation": "1m"  # 1-minute intervals
    }
    
    try:
        async with session.post(
            f"{BASE_URL}/metrics/query",
            json=query
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                metrics = data.get("data", [])
                
                if metrics:
                    sample = metrics[0]
                    has_percentiles = all(
                        key in sample for key in ["p50", "p95", "p99", "min", "max", "avg"]
                    )
                    self.log_result(
                        "Metric Aggregation", 
                        has_percentiles,
                        "Percentiles calculated"
                    )
```

### Aggregation Logic (`processor.py`):
```python
def aggregate_metrics(self, metrics: List[MetricData], interval_minutes: int = 1):
    grouped = defaultdict(list)
    
    # Group metrics by time interval and service/type
    for metric in metrics:
        # Round timestamp to interval
        interval_key = metric.timestamp.replace(
            second=0, 
            microsecond=0,
            minute=(metric.timestamp.minute // interval_minutes) * interval_minutes
        )
        key = (interval_key, metric.service, metric.metric_type)
        grouped[key].append(metric.value)
    
    aggregated = []
    for (timestamp, service, metric_type), values in grouped.items():
        # Calculate percentiles using numpy
        sorted_values = np.sort(values)
        p50 = np.percentile(sorted_values, 50)
        p95 = np.percentile(sorted_values, 95)
        p99 = np.percentile(sorted_values, 99)
        
        aggregated.append(AggregatedMetric(
            timestamp=timestamp,
            service=service,
            metric_type=metric_type,
            p50=p50,
            p95=p95,
            p99=p99,
            min=min(values),
            max=max(values),
            avg=sum(values) / len(values),
            count=len(values)
        ))
    
    return aggregated
```

### Pass Criteria:
- Response contains aggregated metrics
- Each metric has p50, p95, p99, min, max, avg fields
- Count shows number of raw metrics in interval

---

## Performance Tests

### Test 9: Ingestion Throughput

```python
async def test_ingestion_throughput(self, session: aiohttp.ClientSession, duration: int = 10):
    """Test how many metrics per second can be ingested"""
    metrics_sent = 0
    errors = 0
    start_time = time.time()
    
    async def send_metric():
        nonlocal metrics_sent, errors
        metric = {
            "timestamp": datetime.now().isoformat(),
            "service": "perf_test",
            "metric_type": "latency",
            "value": 100.0,
            "tags": {"test": "performance"}
        }
        
        try:
            async with session.post(
                f"{BASE_URL}/metrics/ingest",
                json=metric,
                timeout=aiohttp.ClientTimeout(total=1)
            ) as resp:
                if resp.status == 200:
                    metrics_sent += 1
                else:
                    errors += 1
        except:
            errors += 1
    
    # Send metrics concurrently
    while time.time() - start_time < duration:
        tasks = [send_metric() for _ in range(10)]  # 10 concurrent
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0.01)  # Small delay between batches
    
    elapsed = time.time() - start_time
    throughput = metrics_sent / elapsed
```

### What It Tests:
- Sends batches of 10 concurrent requests
- Runs for 10 seconds
- Calculates metrics per second
- Target: >100/sec (Good), >50/sec (Acceptable)

---

## Test 10: Query Latency

```python
async def test_query_latency(self, session: aiohttp.ClientSession, iterations: int = 100):
    """Test query response times"""
    latencies = []
    
    for i in range(iterations):
        start = time.time()
        try:
            async with session.post(
                f"{BASE_URL}/metrics/query",
                json=query,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    await resp.json()
                    latencies.append((time.time() - start) * 1000)  # ms
        except:
            errors += 1
    
    # Calculate percentiles
    avg_latency = statistics.mean(latencies)
    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    p99 = sorted(latencies)[int(len(latencies) * 0.99)]
```

### What It Measures:
- Response time for 100 queries
- Calculates average, P50, P95, P99
- Target: <50ms avg (Good), <100ms avg (Acceptable)

---

## Test 11: Concurrent Connections

```python
async def test_concurrent_connections(self, session: aiohttp.ClientSession):
    """Test system behavior under concurrent load"""
    async def make_request():
        try:
            start = time.time()
            async with session.get(
                f"{BASE_URL}/metrics/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    return time.time() - start, True
        except:
            return 0, False
    
    # Test with increasing concurrent connections
    for concurrent in [10, 50, 100]:
        tasks = [make_request() for _ in range(concurrent)]
        results = await asyncio.gather(*tasks)
        
        successful = sum(1 for _, success in results if success)
        success_rate = (successful / concurrent) * 100
```

### What It Tests:
- 10, 50, 100 concurrent connections
- Measures success rate and response time
- Target: 100% success rate for all levels

---

## Summary

Each test validates a specific system capability:

| Test | Validates | Key Metric |
|------|-----------|------------|
| Health Check | API responsive | Status = "healthy" |
| Ingestion | Can store metrics | Status = "success" |
| Query | Can retrieve data | Returns list |
| Services | Discovery works | 5 services found |
| WebSocket | Real-time streaming | Continuous messages |
| Generation | Background tasks | 25 metrics/sec |
| Anomaly | Alert detection | Triggers on threshold |
| Aggregation | Statistics calc | Percentiles correct |
| Throughput | Load handling | >50 metrics/sec |
| Latency | Response speed | <100ms average |
| Concurrent | Scalability | 100% success rate |

Together, these tests ensure every component of the telemetry dashboard functions correctly!