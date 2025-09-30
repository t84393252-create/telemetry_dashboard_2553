from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Set
from models import MetricData, MetricQuery, ServiceHealth, Alert
from storage import MetricsStorage
from processor import MetricsProcessor
from generator import MetricsGenerator


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        for connection in disconnected:
            self.active_connections.discard(connection)


storage = MetricsStorage()
processor = MetricsProcessor()
generator = MetricsGenerator()
manager = ConnectionManager()


async def process_generated_metrics(metrics: List[MetricData]):
    await storage.insert_metrics_batch(metrics)
    
    for metric in metrics:
        processor.add_to_buffer(metric)
        alert = processor.detect_anomaly(metric)
        
        await manager.broadcast({
            "type": "metric",
            "data": {
                "timestamp": metric.timestamp.isoformat(),
                "service": metric.service,
                "metric_type": metric.metric_type.value,
                "value": metric.value,
                "tags": metric.tags
            }
        })
        
        if alert:
            await manager.broadcast({
                "type": "alert",
                "data": {
                    "id": alert.id,
                    "timestamp": alert.timestamp.isoformat(),
                    "service": alert.service,
                    "metric_type": alert.metric_type.value,
                    "severity": alert.severity,
                    "message": alert.message,
                    "value": alert.value,
                    "threshold": alert.threshold
                }
            })


async def cleanup_task():
    while True:
        await asyncio.sleep(3600)
        await storage.cleanup_old_data()
        processor.clear_old_buffer_data()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage.initialize()
    
    cleanup = asyncio.create_task(cleanup_task())
    generation = asyncio.create_task(
        generator.start_generation(process_generated_metrics)
    )
    
    yield
    
    generator.stop_generation()
    cleanup.cancel()
    generation.cancel()


app = FastAPI(title="Telemetry Dashboard API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Telemetry Dashboard API", "status": "running"}


@app.get("/metrics/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services_count": len(await storage.get_services())
    }


@app.post("/metrics/ingest")
async def ingest_metric(metric: MetricData):
    try:
        await storage.insert_metric(metric)
        processor.add_to_buffer(metric)
        
        alert = processor.detect_anomaly(metric)
        
        await manager.broadcast({
            "type": "metric",
            "data": {
                "timestamp": metric.timestamp.isoformat(),
                "service": metric.service,
                "metric_type": metric.metric_type.value,
                "value": metric.value,
                "tags": metric.tags
            }
        })
        
        if alert:
            await manager.broadcast({
                "type": "alert",
                "data": {
                    "id": alert.id,
                    "timestamp": alert.timestamp.isoformat(),
                    "service": alert.service,
                    "metric_type": alert.metric_type.value,
                    "severity": alert.severity,
                    "message": alert.message,
                    "value": alert.value,
                    "threshold": alert.threshold
                }
            })
            
            return {"status": "success", "alert": alert}
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/metrics/query")
async def query_metrics(query: MetricQuery):
    try:
        metrics = await storage.query_metrics(query)
        
        if query.aggregation != "raw":
            interval_map = {"1m": 1, "5m": 5, "1h": 60}
            interval = interval_map.get(query.aggregation, 1)
            
            metric_objects = [
                MetricData(
                    timestamp=datetime.fromisoformat(m["timestamp"]),
                    service=m["service"],
                    metric_type=m["metric_type"],
                    value=m["value"],
                    tags=m["tags"]
                )
                for m in metrics
            ]
            
            aggregated = processor.aggregate_metrics(metric_objects, interval)
            return {
                "data": [
                    {
                        "timestamp": agg.timestamp.isoformat(),
                        "service": agg.service,
                        "metric_type": agg.metric_type.value,
                        "p50": agg.p50,
                        "p95": agg.p95,
                        "p99": agg.p99,
                        "min": agg.min,
                        "max": agg.max,
                        "avg": agg.avg,
                        "count": agg.count
                    }
                    for agg in aggregated
                ]
            }
        
        return {"data": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/services")
async def get_services():
    try:
        services = await storage.get_services()
        
        service_health = []
        for service in services:
            stats = processor.get_service_statistics(service)
            
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/alerts")
async def get_alerts(limit: int = 10):
    try:
        alerts = processor.get_recent_alerts(limit)
        return {
            "alerts": [
                {
                    "id": alert.id,
                    "timestamp": alert.timestamp.isoformat(),
                    "service": alert.service,
                    "metric_type": alert.metric_type.value,
                    "severity": alert.severity,
                    "message": alert.message,
                    "value": alert.value,
                    "threshold": alert.threshold
                }
                for alert in alerts
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/metrics")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        latest_metrics = await storage.get_latest_metrics(50)
        await websocket.send_json({
            "type": "initial",
            "data": latest_metrics
        })
        
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)