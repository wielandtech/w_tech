from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)


def homepage(request):
    return render(request, 'core/index.html')


def debug_netdata(request):
    """
    Debug endpoint to test Netdata connectivity and available charts.
    """
    netdata_url = settings.NETDATA_URL
    debug_info = {
        'netdata_url': netdata_url,
        'connectivity': 'unknown',
        'available_charts': [],
        'sample_data': {}
    }
    
    try:
        # Test basic connectivity
        response = requests.get(f"{netdata_url}/api/v1/info", timeout=3)
        if response.status_code == 200:
            debug_info['connectivity'] = 'success'
            debug_info['netdata_info'] = response.json()
        else:
            debug_info['connectivity'] = f'failed (status {response.status_code})'
            
        # Try to get available charts
        charts_response = requests.get(f"{netdata_url}/api/v1/charts", timeout=3)
        if charts_response.status_code == 200:
            charts_data = charts_response.json()
            debug_info['available_charts'] = list(charts_data.get('charts', {}).keys())[:20]  # First 20
            
        # Try fetching charts list for each host to see available metrics
        test_hosts = ['wtech7062', 'wtech7061', 'wtech7063']
        debug_info['host_charts'] = {}
        debug_info['sample_queries'] = {}
        
        for host in test_hosts:
            debug_info['host_charts'][host] = {}
            debug_info['sample_queries'][host] = {}
            
            # Try to get charts for this specific host
            try:
                host_charts_response = requests.get(
                    f"{netdata_url}/api/v1/charts",
                    params={'host': host},
                    timeout=3
                )
                if host_charts_response.status_code == 200:
                    host_charts_data = host_charts_response.json()
                    charts_list = list(host_charts_data.get('charts', {}).keys())
                    # Look for system charts
                    system_charts = [c for c in charts_list if c.startswith('system.')]
                    debug_info['host_charts'][host] = {
                        'status': 'OK',
                        'total_charts': len(charts_list),
                        'system_charts': system_charts[:10]  # First 10 system charts
                    }
                else:
                    debug_info['host_charts'][host] = {'status': f'Error {host_charts_response.status_code}'}
            except Exception as e:
                debug_info['host_charts'][host] = {'status': f'Exception: {str(e)}'}
            
            # Try different query methods
            for chart_name in ['system.cpu', 'system.ram']:
                debug_info['sample_queries'][host][chart_name] = {}
                
                # Method 1: host parameter
                try:
                    resp = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': chart_name, 'points': 1, 'host': host},
                        timeout=3
                    )
                    debug_info['sample_queries'][host][chart_name]['host_param'] = resp.status_code
                except Exception as e:
                    debug_info['sample_queries'][host][chart_name]['host_param'] = str(e)
                
                # Method 2: node parameter
                try:
                    resp = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': chart_name, 'points': 1, 'node': host},
                        timeout=3
                    )
                    debug_info['sample_queries'][host][chart_name]['node_param'] = resp.status_code
                except Exception as e:
                    debug_info['sample_queries'][host][chart_name]['node_param'] = str(e)
                
                # Method 3: Try with hostname prefix in chart name
                try:
                    prefixed_chart = f"{host}.{chart_name}"
                    resp = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': prefixed_chart, 'points': 1},
                        timeout=3
                    )
                    debug_info['sample_queries'][host][chart_name]['prefixed_chart'] = resp.status_code
                except Exception as e:
                    debug_info['sample_queries'][host][chart_name]['prefixed_chart'] = str(e)
                
    except Exception as e:
        debug_info['connectivity'] = f'failed: {str(e)}'
        
    return JsonResponse(debug_info, json_dumps_params={'indent': 2})


def get_netdata_metrics(request):
    """
    Fetch system metrics from Netdata API and return as JSON.
    Aggregates metrics from all physical nodes in the cluster.
    Implements caching to reduce API calls.
    """
    # Try to get cached metrics first
    cached_metrics = cache.get('netdata_metrics')
    if cached_metrics:
        cached_metrics['cache_hit'] = True
        return JsonResponse(cached_metrics)
    
    try:
        netdata_url = settings.NETDATA_URL
        timeout = 3  # 3 second timeout
        
        # Monitor all physical nodes
        netdata_hosts = getattr(settings, 'NETDATA_HOSTS', ['wtech7062', 'wtech7061', 'wtech7063'])
        if isinstance(netdata_hosts, str):
            netdata_hosts = [h.strip() for h in netdata_hosts.split(',')]
        
        metrics = {
            'cpu': None,
            'ram': None,
            'network': None,
            'disk': None,
            'status': 'ok',
            'cache_hit': False,
            'errors': [],
            'nodes': [],
            'nodes_count': len(netdata_hosts)
        }
        
        # Aggregate data from all nodes
        cpu_values = []
        ram_data = {'used': 0, 'total': 0}
        network_data = {'received': 0, 'sent': 0}
        disk_data = {'read': 0, 'write': 0}
        
        # Fetch metrics from each node
        for host in netdata_hosts:
            node_metrics = {'hostname': host, 'reachable': False}
            
            # Fetch CPU usage for this node
            try:
                cpu_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'system.cpu',
                        'points': 1,
                        'options': 'percentage',
                        'host': host
                    },
                    timeout=timeout
                )
                if cpu_response.status_code == 200:
                    cpu_data = cpu_response.json()
                    if 'data' in cpu_data and len(cpu_data['data']) > 0:
                        latest = cpu_data['data'][0]
                        labels = cpu_data.get('labels', [])
                        if 'idle' in labels:
                            idle_idx = labels.index('idle')
                            idle_value = latest[idle_idx + 1] if len(latest) > idle_idx + 1 else 0
                            cpu_usage = 100 - idle_value
                        else:
                            cpu_usage = sum([v for v in latest[1:] if isinstance(v, (int, float))])
                        cpu_values.append(cpu_usage)
                        node_metrics['cpu'] = round(cpu_usage, 1)
                        node_metrics['reachable'] = True
            except Exception as e:
                error_msg = f"Failed to fetch CPU for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
        
            # Fetch RAM usage for this node
            try:
                ram_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'system.ram',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if ram_response.status_code == 200:
                    ram_response_data = ram_response.json()
                    if 'data' in ram_response_data and len(ram_response_data['data']) > 0:
                        latest = ram_response_data['data'][0]
                        labels = ram_response_data.get('labels', [])
                        
                        total_ram = sum([v for v in latest[1:] if isinstance(v, (int, float))])
                        free_ram = 0
                        
                        if 'free' in labels:
                            free_idx = labels.index('free')
                            free_ram = latest[free_idx + 1] if len(latest) > free_idx + 1 else 0
                        
                        used_ram = total_ram - free_ram
                        ram_data['used'] += used_ram
                        ram_data['total'] += total_ram
                        node_metrics['ram_gb'] = round(total_ram / 1024, 2)
            except Exception as e:
                error_msg = f"Failed to fetch RAM for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
        
            # Fetch Network I/O for this node
            try:
                net_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'system.net',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if net_response.status_code == 200:
                    net_data = net_response.json()
                    if 'data' in net_data and len(net_data['data']) > 0:
                        latest = net_data['data'][0]
                        labels = net_data.get('labels', [])
                        
                        if 'received' in labels:
                            recv_idx = labels.index('received')
                            received = abs(latest[recv_idx + 1]) if len(latest) > recv_idx + 1 else 0
                            network_data['received'] += received
                        
                        if 'sent' in labels:
                            sent_idx = labels.index('sent')
                            sent = abs(latest[sent_idx + 1]) if len(latest) > sent_idx + 1 else 0
                            network_data['sent'] += sent
            except Exception as e:
                error_msg = f"Failed to fetch network for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
        
            # Fetch Disk I/O for this node
            try:
                disk_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'system.io',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if disk_response.status_code == 200:
                    disk_response_data = disk_response.json()
                    if 'data' in disk_response_data and len(disk_response_data['data']) > 0:
                        latest = disk_response_data['data'][0]
                        labels = disk_response_data.get('labels', [])
                        
                        if 'in' in labels:
                            read_idx = labels.index('in')
                            read_ops = abs(latest[read_idx + 1]) if len(latest) > read_idx + 1 else 0
                            disk_data['read'] += read_ops
                        
                        if 'out' in labels:
                            write_idx = labels.index('out')
                            write_ops = abs(latest[write_idx + 1]) if len(latest) > write_idx + 1 else 0
                            disk_data['write'] += write_ops
            except Exception as e:
                error_msg = f"Failed to fetch disk for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
            
            metrics['nodes'].append(node_metrics)
        
        # Calculate aggregated metrics
        if cpu_values:
            metrics['cpu'] = round(sum(cpu_values) / len(cpu_values), 1)  # Average CPU
        
        if ram_data['total'] > 0:
            ram_percentage = (ram_data['used'] / ram_data['total'] * 100)
            metrics['ram'] = {
                'percentage': round(ram_percentage, 1),
                'used_gb': round(ram_data['used'] / 1024, 2),  # Convert MB to GB
                'total_gb': round(ram_data['total'] / 1024, 2)
            }
        
        if network_data['received'] > 0 or network_data['sent'] > 0:
            metrics['network'] = {
                'received_mbps': round(network_data['received'] / 1024, 2),  # Convert to Mbps
                'sent_mbps': round(network_data['sent'] / 1024, 2)
            }
        
        if disk_data['read'] > 0 or disk_data['write'] > 0:
            metrics['disk'] = {
                'read_kbps': round(disk_data['read'] / 1024, 2),
                'write_kbps': round(disk_data['write'] / 1024, 2)
            }
        
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
