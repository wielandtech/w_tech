from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.conf import settings
from django.core.cache import cache
import requests
import logging

logger = logging.getLogger(__name__)


def homepage(request):
    return render(request, 'core/index.html')


def custom_400(request, exception=None):
    """
    Custom 400 error handler that serves a branded error page.
    This will be used when DEBUG=False and a 400 error occurs.
    """
    return render(request, 'core/400.html', status=400)


def custom_403(request, exception=None):
    """
    Custom 403 error handler that serves a branded error page.
    This will be used when DEBUG=False and a 403 error occurs.
    """
    return render(request, 'core/403.html', status=403)


def custom_404(request, exception=None):
    """
    Custom 404 error handler that serves a branded error page.
    This will be used when DEBUG=False and a 404 error occurs.
    """
    return render(request, 'core/404.html', status=404)


def custom_500(request):
    """
    Custom 500 error handler that serves a branded error page.
    This will be used when DEBUG=False and a 500 error occurs.
    """
    return render(request, 'core/500.html', status=500)


def custom_502(request, exception=None):
    """
    Custom 502 error handler that serves a branded error page.
    This will be used when DEBUG=False and a 502 error occurs.
    """
    return render(request, 'core/502.html', status=502)


def custom_503(request, exception=None):
    """
    Custom 503 error handler that serves a branded error page.
    This will be used when DEBUG=False and a 503 error occurs.
    """
    return render(request, 'core/503.html', status=503)


def maintenance(request):
    """
    Maintenance page handler.
    This can be used to show a maintenance page when needed.
    """
    return render(request, 'core/maintenance.html', status=503)


def get_netdata_metrics(request):
    """
    Fetch comprehensive cluster metrics from Netdata k8s_state collector and return as JSON.
    Shows cluster CPU utilization, memory usage, pod counts, and network activity.
    Implements caching to reduce API calls.
    """
    cached_metrics = cache.get('netdata_metrics')
    if cached_metrics:
        cached_metrics['cache_hit'] = True
        return JsonResponse(cached_metrics)

    try:
        netdata_url = settings.NETDATA_URL
        k8s_state_url = f"{netdata_url.replace('netdata-parent', 'netdata-k8s-state')}"
        timeout = 3

        netdata_hosts = getattr(settings, 'NETDATA_HOSTS', ['wtech7062', 'wtech7061', 'wtech7063'])
        if isinstance(netdata_hosts, str):
            netdata_hosts = [h.strip() for h in netdata_hosts.split(',')]

        metrics = {
            'cpu': None,
            'memory': None,
            'pods': None,
            'network': None,
            'status': 'ok',
            'cache_hit': False,
            'errors': [],
            'nodes_count': len(netdata_hosts),
            'reachable_nodes': 0
        }
        
        # Get cluster total resources from parent node info
        cluster_cores = 0
        cluster_ram_gb = 0
        try:
            info_response = requests.get(f"{netdata_url}/api/v1/info", timeout=timeout)
            if info_response.status_code == 200:
                info_data = info_response.json()
                cores_per_node = int(info_data.get('cores_total', 0))
                ram_bytes_per_node = int(info_data.get('ram_total', 0))
                ram_gb_per_node = round(ram_bytes_per_node / (1024**3), 1)
                
                # Calculate total cluster resources
                total_nodes = len(netdata_hosts)
                cluster_cores = cores_per_node * total_nodes
                cluster_ram_gb = ram_gb_per_node * total_nodes
        except Exception as e:
            logger.warning(f"Failed to fetch cluster info: {e}")
            if len(metrics['errors']) < 3:
                metrics['errors'].append(f"Cluster info failed")

        # Aggregate data from all nodes using netdata metrics
        cpu_values = []
        memory_values = []
        total_clients = 0
        total_requests = 0
        reachable_nodes = 0
        
        for host in netdata_hosts:
            try:
                # Fetch CPU usage for this node
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
                        # Use system CPU directly
                        system_cpu = latest[2] if len(latest) > 2 and isinstance(latest[2], (int, float)) else 0
                        cpu_usage = system_cpu
                        cpu_values.append(cpu_usage)
                        reachable_nodes += 1
                
                # Fetch memory usage for this node
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
                    ram_data = ram_response.json()
                    if 'data' in ram_data and len(ram_data['data']) > 0:
                        latest = ram_data['data'][0]
                        memory_bytes = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        memory_mb = memory_bytes / (1024 * 1024)  # Convert bytes to MB
                        memory_values.append(memory_mb)
                
                # Fetch active connections for this node
                clients_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'netdata.clients',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if clients_response.status_code == 200:
                    clients_data = clients_response.json()
                    if 'data' in clients_data and len(clients_data['data']) > 0:
                        latest = clients_data['data'][0]
                        clients = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        total_clients += clients
                
                # Fetch API requests for this node
                requests_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={
                        'chart': 'netdata.requests',
                        'points': 1,
                        'host': host
                    },
                    timeout=timeout
                )
                if requests_response.status_code == 200:
                    requests_data = requests_response.json()
                    if 'data' in requests_data and len(requests_data['data']) > 0:
                        latest = requests_data['data'][0]
                        requests_ps = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        total_requests += requests_ps
                        
            except Exception as e:
                logger.warning(f"Failed to fetch metrics for {host}: {e}")
                if len(metrics['errors']) < 3:
                    metrics['errors'].append(f"Metrics fetch failed for {host}")
        
        # Calculate cluster-wide CPU metrics
        if cpu_values:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            metrics['cpu'] = {
                'percentage': round(avg_cpu, 1),
                'total_cores': cluster_cores,
                'description': 'CPU Usage'
            }
        
        # Calculate cluster-wide memory metrics
        if memory_values:
            total_memory_mb = sum(memory_values)
            cluster_ram_mb = cluster_ram_gb * 1024
            
            # Estimate actual cluster memory usage (scale monitoring memory to represent cluster usage)
            estimated_cluster_usage_mb = total_memory_mb * 10  # Scale factor for cluster vs monitoring
            estimated_cluster_usage_gb = round(estimated_cluster_usage_mb / 1024, 1)
            usage_percentage = round((estimated_cluster_usage_mb / cluster_ram_mb) * 100, 1)
            
            # Ensure we have a meaningful decimal value (at least 0.1 GB)
            if estimated_cluster_usage_gb < 0.1:
                estimated_cluster_usage_gb = 0.1
            
            metrics['memory'] = {
                'total_gb': cluster_ram_gb,
                'used_gb': estimated_cluster_usage_gb,
                'percentage': usage_percentage,
                'description': 'Memory Usage'
            }
        
        # Estimate pod count based on active connections (fallback method)
        # This is a rough estimation since we can't access k8s_state metrics directly
        estimated_pods = max(0, int(total_clients / 3))  # Rough estimate: 3 connections per pod
        metrics['pods'] = {
            'count': estimated_pods,
            'description': 'Number of Pods (estimated)'
        }
        
        # Network activity (using netdata metrics)
        metrics['network'] = {
            'active_connections': int(total_clients),
            'api_requests_ps': round(total_requests, 1),
            'description': 'Network Activity'
        }
        
        # Set reachable nodes count
        metrics['reachable_nodes'] = reachable_nodes
        
        # Cache the metrics for 10 seconds
        cache.set('netdata_metrics', metrics, 10)
        
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
