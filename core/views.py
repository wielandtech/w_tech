from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)


def homepage(request):
    return render(request, 'core/index.html')


def get_netdata_metrics(request):
    """
    Fetch system metrics from Netdata API and return as JSON.
    Implements caching to reduce API calls.
    """
    # Try to get cached metrics first
    cached_metrics = cache.get('netdata_metrics')
    if cached_metrics:
        return JsonResponse(cached_metrics)
    
    try:
        netdata_url = settings.NETDATA_URL
        timeout = 3  # 3 second timeout
        
        metrics = {
            'cpu': None,
            'ram': None,
            'network': None,
            'disk': None,
            'status': 'ok'
        }
        
        # Fetch CPU usage
        try:
            cpu_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={
                    'chart': 'system.cpu',
                    'points': 1,
                    'options': 'percentage'
                },
                timeout=timeout
            )
            if cpu_response.status_code == 200:
                cpu_data = cpu_response.json()
                # Calculate total CPU usage (sum of all states except idle)
                if 'data' in cpu_data and len(cpu_data['data']) > 0:
                    latest = cpu_data['data'][0]
                    # Find idle index in labels
                    labels = cpu_data.get('labels', [])
                    if 'idle' in labels:
                        idle_idx = labels.index('idle')
                        idle_value = latest[idle_idx + 1] if len(latest) > idle_idx + 1 else 0
                        cpu_usage = 100 - idle_value
                    else:
                        # If no idle, sum all other values
                        cpu_usage = sum([v for v in latest[1:] if isinstance(v, (int, float))])
                    metrics['cpu'] = round(cpu_usage, 1)
        except Exception as e:
            logger.warning(f"Failed to fetch CPU metrics: {e}")
        
        # Fetch RAM usage
        try:
            ram_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={
                    'chart': 'system.ram',
                    'points': 1,
                },
                timeout=timeout
            )
            if ram_response.status_code == 200:
                ram_data = ram_response.json()
                if 'data' in ram_data and len(ram_data['data']) > 0:
                    latest = ram_data['data'][0]
                    labels = ram_data.get('labels', [])
                    
                    # Calculate used RAM (excluding free and cached)
                    total_ram = sum([v for v in latest[1:] if isinstance(v, (int, float))])
                    free_ram = 0
                    
                    if 'free' in labels:
                        free_idx = labels.index('free')
                        free_ram = latest[free_idx + 1] if len(latest) > free_idx + 1 else 0
                    
                    used_ram = total_ram - free_ram
                    ram_percentage = (used_ram / total_ram * 100) if total_ram > 0 else 0
                    
                    metrics['ram'] = {
                        'percentage': round(ram_percentage, 1),
                        'used_gb': round(used_ram / 1024, 2),  # Convert MB to GB
                        'total_gb': round(total_ram / 1024, 2)
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch RAM metrics: {e}")
        
        # Fetch Network I/O
        try:
            net_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={
                    'chart': 'system.net',
                    'points': 1,
                },
                timeout=timeout
            )
            if net_response.status_code == 200:
                net_data = net_response.json()
                if 'data' in net_data and len(net_data['data']) > 0:
                    latest = net_data['data'][0]
                    labels = net_data.get('labels', [])
                    
                    received = 0
                    sent = 0
                    
                    if 'received' in labels:
                        recv_idx = labels.index('received')
                        received = abs(latest[recv_idx + 1]) if len(latest) > recv_idx + 1 else 0
                    
                    if 'sent' in labels:
                        sent_idx = labels.index('sent')
                        sent = abs(latest[sent_idx + 1]) if len(latest) > sent_idx + 1 else 0
                    
                    metrics['network'] = {
                        'received_mbps': round(received / 1024, 2),  # Convert to Mbps
                        'sent_mbps': round(sent / 1024, 2)
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch network metrics: {e}")
        
        # Fetch Disk I/O
        try:
            disk_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={
                    'chart': 'system.io',
                    'points': 1,
                },
                timeout=timeout
            )
            if disk_response.status_code == 200:
                disk_data = disk_response.json()
                if 'data' in disk_data and len(disk_data['data']) > 0:
                    latest = disk_data['data'][0]
                    labels = disk_data.get('labels', [])
                    
                    read_ops = 0
                    write_ops = 0
                    
                    if 'in' in labels:
                        read_idx = labels.index('in')
                        read_ops = abs(latest[read_idx + 1]) if len(latest) > read_idx + 1 else 0
                    
                    if 'out' in labels:
                        write_idx = labels.index('out')
                        write_ops = abs(latest[write_idx + 1]) if len(latest) > write_idx + 1 else 0
                    
                    metrics['disk'] = {
                        'read_kbps': round(read_ops / 1024, 2),
                        'write_kbps': round(write_ops / 1024, 2)
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch disk metrics: {e}")
        
        # Cache the metrics for 30 seconds
        cache.set('netdata_metrics', metrics, 30)
        
        return JsonResponse(metrics)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to connect to Netdata: {e}")
        # Try to return cached data even if expired
        cached_metrics = cache.get('netdata_metrics_backup')
        if cached_metrics:
            cached_metrics['status'] = 'cached'
            return JsonResponse(cached_metrics)
        
        return JsonResponse({
            'cpu': None,
            'ram': None,
            'network': None,
            'disk': None,
            'status': 'unavailable',
            'error': 'Unable to connect to monitoring service'
        })
    except Exception as e:
        logger.error(f"Unexpected error fetching Netdata metrics: {e}")
        return JsonResponse({
            'cpu': None,
            'ram': None,
            'network': None,
            'disk': None,
            'status': 'error',
            'error': 'Internal error'
        })
