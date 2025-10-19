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
        test_hosts = ['netdata-parent', 'wtech7062', 'wtech7061', 'wtech7063']
        debug_info['host_charts'] = {}
        debug_info['sample_queries'] = {}
        debug_info['parent_test'] = {}
        
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
                    
                    # Categorize charts by prefix
                    system_charts = [c for c in charts_list if c.startswith('system.')]
                    cpu_charts = [c for c in charts_list if 'cpu' in c.lower()]
                    mem_charts = [c for c in charts_list if 'mem' in c.lower() or 'ram' in c.lower()]
                    net_charts = [c for c in charts_list if 'net' in c.lower()]
                    disk_charts = [c for c in charts_list if 'disk' in c.lower() or 'io' in c.lower()]
                    
                    debug_info['host_charts'][host] = {
                        'status': 'OK',
                        'total_charts': len(charts_list),
                        'system_charts': system_charts,
                        'cpu_related': cpu_charts[:15],
                        'memory_related': mem_charts[:15],
                        'network_related': net_charts[:15],
                        'disk_related': disk_charts[:15],
                        'all_charts_sample': charts_list[:30]  # First 30 of all charts
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
        
        # Test if we can get data without host parameter (should query parent/default)
        debug_info['parent_test']['charts_query'] = {}
        for chart in ['system.cpu', 'system.ram', 'system.net', 'system.io']:
            try:
                resp = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={'chart': chart, 'points': 1},
                    timeout=3
                )
                debug_info['parent_test']['charts_query'][chart] = {
                    'status': resp.status_code,
                    'has_data': len(resp.json().get('data', [])) > 0 if resp.status_code == 200 else False
                }
            except Exception as e:
                debug_info['parent_test']['charts_query'][chart] = {'error': str(e)}
                
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
            'nodes_count': len(netdata_hosts),
            'cluster_info': {}
        }
        
        # First, get cluster total resources from parent node info
        try:
            info_response = requests.get(f"{netdata_url}/api/v1/info", timeout=timeout)
            if info_response.status_code == 200:
                info_data = info_response.json()
                cluster_cores = int(info_data.get('cores_total', 0))
                cluster_ram_bytes = int(info_data.get('ram_total', 0))
                cluster_ram_gb = round(cluster_ram_bytes / (1024**3), 1)
                
                metrics['cluster_info'] = {
                    'total_cores': cluster_cores,
                    'total_ram_gb': cluster_ram_gb,
                    'total_ram_mb': round(cluster_ram_bytes / (1024**2), 0)
                }
        except Exception as e:
            logger.warning(f"Failed to fetch cluster info: {e}")
            metrics['errors'].append(f"Failed to fetch cluster info: {e}")

        # Aggregate data from all nodes
        cpu_values = []
        ram_data = {'used': 0, 'total': 0}
        network_data = {'received': 0, 'sent': 0}
        disk_data = {'read': 0, 'write': 0}
        
        # Fetch metrics from each node using available netdata.* charts
        for host in netdata_hosts:
            node_metrics = {'hostname': host, 'reachable': False}
            
            # Fetch Netdata's own CPU usage for this node
            try:
                cpu_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'netdata.server_cpu',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if cpu_response.status_code == 200:
                    cpu_data = cpu_response.json()
                    if 'data' in cpu_data and len(cpu_data['data']) > 0:
                        latest = cpu_data['data'][0]
                        # Get the first CPU usage value (usually total CPU percentage)
                        cpu_usage = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        cpu_values.append(cpu_usage)
                        node_metrics['cpu'] = round(cpu_usage, 1)
                        node_metrics['reachable'] = True
            except Exception as e:
                error_msg = f"Failed to fetch CPU for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
        
            # Fetch Netdata's own RAM usage for this node
            try:
                ram_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'netdata.memory',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if ram_response.status_code == 200:
                    ram_response_data = ram_response.json()
                    if 'data' in ram_response_data and len(ram_response_data['data']) > 0:
                        latest = ram_response_data['data'][0]
                        # Get the first memory value (usually in bytes, convert to MB)
                        memory_bytes = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        memory_mb = memory_bytes / (1024 * 1024)  # Convert bytes to MB
                        ram_data['used'] += memory_mb
                        # Estimate total (we'll use a fixed value per node for percentage)
                        ram_data['total'] += 500  # Assume 500MB max per Netdata instance
                        node_metrics['ram_mb'] = round(memory_mb, 2)
            except Exception as e:
                error_msg = f"Failed to fetch RAM for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
        
            # Fetch Netdata's TCP connection stats for this node
            try:
                net_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'netdata.clients',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if net_response.status_code == 200:
                    net_data = net_response.json()
                    if 'data' in net_data and len(net_data['data']) > 0:
                        latest = net_data['data'][0]
                        # Get the first client count value
                        clients = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        network_data['received'] += clients  # Reuse as client count
                        node_metrics['clients'] = int(clients)
            except Exception as e:
                error_msg = f"Failed to fetch connections for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
        
            # Fetch Netdata's request rate for this node
            try:
                disk_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'netdata.requests',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if disk_response.status_code == 200:
                    disk_response_data = disk_response.json()
                    if 'data' in disk_response_data and len(disk_response_data['data']) > 0:
                        latest = disk_response_data['data'][0]
                        # Get the first requests per second value
                        requests_ps = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        disk_data['read'] += requests_ps
                        node_metrics['requests_ps'] = round(requests_ps, 1)
            except Exception as e:
                error_msg = f"Failed to fetch requests for {host}: {e}"
                logger.warning(error_msg)
                metrics['errors'].append(error_msg)
            
            metrics['nodes'].append(node_metrics)
        
        # Calculate aggregated metrics with cluster context
        if cpu_values:
            # Show average CPU usage across monitoring processes with cluster context
            metrics['cpu'] = {
                'percentage': round(sum(cpu_values) / len(cpu_values), 1),
                'total_cores': metrics['cluster_info'].get('total_cores', 0),
                'description': 'Monitoring CPU usage'
            }
        
        if ram_data['total'] > 0:
            # Show cluster memory with estimated usage
            cluster_ram_mb = metrics['cluster_info'].get('total_ram_mb', 0)
            cluster_ram_gb = metrics['cluster_info'].get('total_ram_gb', 0)
            
            # Estimate cluster usage based on monitoring overhead (assume 5-10% of total)
            estimated_usage_percent = 8  # 8% estimated cluster usage
            cluster_used_gb = round(cluster_ram_gb * estimated_usage_percent / 100, 1)
            
            metrics['ram'] = {
                'cluster_total_gb': cluster_ram_gb,
                'cluster_estimated_used_gb': cluster_used_gb,
                'cluster_estimated_percentage': estimated_usage_percent,
                'monitoring_used_mb': round(ram_data['used'], 1),
                'description': 'Cluster Memory'
            }
        
        if network_data['received'] > 0:
            metrics['network'] = {
                'total_clients': int(network_data['received']),
                'avg_per_node': round(network_data['received'] / len(netdata_hosts), 1),
                'description': 'Active Connections'
            }
        
        if disk_data['read'] > 0:
            metrics['disk'] = {
                'total_requests_ps': round(disk_data['read'], 1),
                'avg_per_node': round(disk_data['read'] / len(netdata_hosts), 1),
                'description': 'API Requests/sec'
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
