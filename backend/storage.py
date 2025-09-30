import aiosqlite
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from contextlib import asynccontextmanager
from models import MetricData, MetricQuery, AggregatedMetric
import asyncio
from pathlib import Path


class MetricsStorage:
    def __init__(self, db_path: str = "metrics.db"):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    service TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    tags TEXT,
                    created_at REAL DEFAULT (unixepoch('now'))
                )
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON metrics(timestamp DESC)
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_metrics_service 
                ON metrics(service, timestamp DESC)
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS aggregated_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    service TEXT NOT NULL,
                    metric_type TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    p50 REAL,
                    p95 REAL,
                    p99 REAL,
                    min REAL,
                    max REAL,
                    avg REAL,
                    count INTEGER,
                    created_at REAL DEFAULT (unixepoch('now'))
                )
            ''')
            
            await db.execute('''
                CREATE INDEX IF NOT EXISTS idx_aggregated_timestamp 
                ON aggregated_metrics(timestamp DESC, interval)
            ''')
            
            await db.commit()
    
    async def insert_metric(self, metric: MetricData):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO metrics (timestamp, service, metric_type, value, tags)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    metric.timestamp.timestamp(),
                    metric.service,
                    metric.metric_type.value,
                    metric.value,
                    json.dumps(metric.tags) if metric.tags else None
                ))
                await db.commit()
    
    async def insert_metrics_batch(self, metrics: List[MetricData]):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.executemany('''
                    INSERT INTO metrics (timestamp, service, metric_type, value, tags)
                    VALUES (?, ?, ?, ?, ?)
                ''', [
                    (
                        m.timestamp.timestamp(),
                        m.service,
                        m.metric_type.value,
                        m.value,
                        json.dumps(m.tags) if m.tags else None
                    )
                    for m in metrics
                ])
                await db.commit()
    
    async def query_metrics(self, query: MetricQuery) -> List[Dict]:
        conditions = ["timestamp >= ? AND timestamp <= ?"]
        params = [query.start_time.timestamp(), query.end_time.timestamp()]
        
        if query.services:
            placeholders = ','.join(['?' for _ in query.services])
            conditions.append(f"service IN ({placeholders})")
            params.extend(query.services)
        
        if query.metric_types:
            placeholders = ','.join(['?' for _ in query.metric_types])
            conditions.append(f"metric_type IN ({placeholders})")
            params.extend([mt.value for mt in query.metric_types])
        
        where_clause = " AND ".join(conditions)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f'''
                SELECT timestamp, service, metric_type, value, tags
                FROM metrics
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT 10000
            ''', params)
            
            rows = await cursor.fetchall()
            return [
                {
                    "timestamp": datetime.fromtimestamp(row["timestamp"]).isoformat(),
                    "service": row["service"],
                    "metric_type": row["metric_type"],
                    "value": row["value"],
                    "tags": json.loads(row["tags"]) if row["tags"] else {}
                }
                for row in rows
            ]
    
    async def get_services(self) -> List[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT DISTINCT service FROM metrics
                WHERE timestamp > ?
                ORDER BY service
            ''', (datetime.now().timestamp() - 86400,))
            
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def cleanup_old_data(self):
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                cutoff_raw = datetime.now() - timedelta(hours=24)
                await db.execute('''
                    DELETE FROM metrics WHERE timestamp < ?
                ''', (cutoff_raw.timestamp(),))
                
                cutoff_aggregated = datetime.now() - timedelta(days=7)
                await db.execute('''
                    DELETE FROM aggregated_metrics WHERE timestamp < ?
                ''', (cutoff_aggregated.timestamp(),))
                
                await db.commit()
    
    async def get_latest_metrics(self, limit: int = 100) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT timestamp, service, metric_type, value, tags
                FROM metrics
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            rows = await cursor.fetchall()
            return [
                {
                    "timestamp": datetime.fromtimestamp(row["timestamp"]).isoformat(),
                    "service": row["service"],
                    "metric_type": row["metric_type"],
                    "value": row["value"],
                    "tags": json.loads(row["tags"]) if row["tags"] else {}
                }
                for row in rows
            ]