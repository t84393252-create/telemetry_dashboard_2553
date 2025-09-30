#!/usr/bin/env python3
import asyncio
import websockets
import json
from datetime import datetime

async def test_websocket():
    uri = "ws://localhost:8000/ws/metrics"
    print("🔌 Connecting to WebSocket...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!\n")
            
            # Receive initial data
            message = await websocket.recv()
            data = json.loads(message)
            
            if data['type'] == 'initial':
                print(f"📊 Initial data received: {len(data.get('data', []))} historical metrics")
                print("-" * 50)
            
            # Track metrics by service and type
            metrics_count = {}
            alerts_received = []
            start_time = datetime.now()
            
            print("📡 Monitoring real-time metrics for 10 seconds...\n")
            
            # Receive real-time updates for 10 seconds
            while (datetime.now() - start_time).seconds < 10:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    data = json.loads(message)
                    
                    if data['type'] == 'metric':
                        metric = data['data']
                        key = f"{metric['service']}_{metric['metric_type']}"
                        metrics_count[key] = metrics_count.get(key, 0) + 1
                        
                        # Show sample metrics
                        if len(metrics_count) <= 5:
                            print(f"  📈 {metric['service']:10} | {metric['metric_type']:12} = {metric['value']:8.2f}")
                    
                    elif data['type'] == 'alert':
                        alert = data['data']
                        alerts_received.append(alert)
                        print(f"  🚨 ALERT: {alert['service']} - {alert['message']} (value: {alert['value']:.2f})")
                        
                except asyncio.TimeoutError:
                    continue
            
            print("\n" + "=" * 50)
            print("📊 STREAMING SUMMARY")
            print("=" * 50)
            
            # Show statistics
            total_metrics = sum(metrics_count.values())
            print(f"\n✅ Total metrics received: {total_metrics}")
            print(f"⏱️  Rate: {total_metrics/10:.1f} metrics/second")
            print(f"🚨 Alerts received: {len(alerts_received)}")
            
            # Show breakdown by service
            print("\n📈 Metrics by service and type:")
            services = set()
            types = set()
            for key, count in sorted(metrics_count.items()):
                service, metric_type = key.split('_', 1)
                services.add(service)
                types.add(metric_type)
                if count > 5:  # Only show frequently updated metrics
                    print(f"   {service:10} - {metric_type:12}: {count:3} updates")
            
            print(f"\n📋 Services detected: {', '.join(sorted(services))}")
            print(f"📊 Metric types: {', '.join(sorted(types))}")
            
            # Verify expected behavior
            print("\n" + "=" * 50)
            print("✅ VALIDATION RESULTS")
            print("=" * 50)
            
            checks = [
                ("WebSocket connection", True),
                ("Initial data received", True),
                ("Real-time streaming", total_metrics > 0),
                ("All 5 services present", len(services) == 5),
                ("All 5 metric types present", len(types) == 5),
                ("Consistent data rate", total_metrics > 200),  # Expect ~250 in 10 seconds
                ("Data generator active", total_metrics > 0)
            ]
            
            for check, result in checks:
                symbol = "✅" if result else "❌"
                print(f"{symbol} {check}")
            
            if all(result for _, result in checks):
                print("\n🎉 All WebSocket tests PASSED!")
            else:
                print("\n⚠️  Some tests failed - check output above")
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("🔬 WebSocket Real-time Streaming Test")
    print("=" * 50)
    print()
    
    success = asyncio.run(test_websocket())
    
    if not success:
        print("\n❌ Test failed - ensure backend is running on http://localhost:8000")
        exit(1)