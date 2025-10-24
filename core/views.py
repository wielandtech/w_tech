from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.conf import settings
from django.core.cache import cache
import requests
import logging
# from kubernetes import client, config  # No longer needed - using k8s_state metrics

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
    Fetch cluster metrics from Netdata k8s_state collector.
    Shows cluster CPU utilization, memory usage, pod counts, and network activity.
    Implements caching to reduce API calls.
    """
    cached_metrics = cache.get('netdata_metrics')
    if cached_metrics:
        cached_metrics['cache_hit'] = True
        return JsonResponse(cached_metrics)

    try:
        netdata_url = settings.NETDATA_URL
        timeout = 3

        metrics = {
            'cpu': None,
            'memory': None,
            'pods': None,
            'network': None,
            'status': 'ok',
            'cache_hit': False,
            'errors': [],
            'nodes_count': 0,
            'reachable_nodes': 0
        }
        
        # Get cluster resources and pod count from k8s_state
        cluster_cores = 18  # 3 nodes * 6 cores per node
        cluster_ram_gb = 48  # 3 nodes * 16GB per node
        metrics['nodes_count'] = 3
        
        # Get pod count from k8s_state by counting running pods
        try:
            k8s_state_url = f"{netdata_url.replace('netdata-parent', 'netdata-k8s-state')}"
            
            # Get all pod phase charts and count running pods
            charts_response = requests.get(
                f"{k8s_state_url}/api/v1/charts",
                timeout=timeout
            )
            if charts_response.status_code == 200:
                charts_data = charts_response.json()
                running_pods = 0
                
                # Count pods with phase=running
                for chart_name in charts_data.get('charts', {}):
                    if chart_name.endswith('.phase'):
                        # Get the phase data for this pod
                        phase_response = requests.get(
                            f"{k8s_state_url}/api/v1/data",
                            params={'chart': chart_name, 'points': 1},
                            timeout=timeout
                        )
                        if phase_response.status_code == 200:
                            phase_data = phase_response.json()
                            if 'data' in phase_data and len(phase_data['data']) > 0:
                                latest = phase_data['data'][0]
                                # Check if this pod is running (phase=1 typically means running)
                                if len(latest) > 1 and latest[1] == 1:
                                    running_pods += 1
                
                # If no pods found via phase charts, try alternative approaches
                if running_pods == 0:
                    # Method 1: Count pod-related charts
                    pod_charts = [name for name in charts_data.get('charts', {}) if 'pod_' in name and not name.startswith('k8s_state_k8s-metrics')]
                    if pod_charts:
                        running_pods = len(pod_charts)
                        logger.info(f"Found {running_pods} pod charts: {pod_charts[:5]}...")  # Log first 5
                    else:
                        # Method 2: Count any charts that look like individual resources
                        resource_charts = [name for name in charts_data.get('charts', {}) if '.' in name and not name.startswith('k8s_state_k8s-metrics')]
                        # Estimate pods as a fraction of total charts (rough heuristic)
                        running_pods = max(1, len(resource_charts) // 10)  # Rough estimate
                        logger.info(f"Estimated {running_pods} pods from {len(resource_charts)} resource charts")
                
                metrics['pods'] = {
                    'count': running_pods,
                    'description': 'Running Pods'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch pod counts from k8s_state: {e}")
            metrics['pods'] = {
                'count': 0,
                'description': 'Running Pods (unavailable)'
            }

        # Try to get system metrics from netdata (if available)
        try:
                # Get netdata info for cluster resources
                info_response = requests.get(f"{netdata_url}/api/v1/info", timeout=timeout)
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    # Use netdata info if available, but prefer our hardcoded values for accuracy
                    # Only use netdata info if it seems reasonable (not single node values)
                    if 'cores_total' in info_data and info_data['cores_total'] and int(info_data['cores_total']) >= 18:
                        cluster_cores = int(info_data['cores_total'])
                    if 'ram_total' in info_data and info_data['ram_total']:
                        netdata_ram_gb = round(int(info_data['ram_total']) / (1024**3), 1)
                        # Only use if it's reasonable (not single node values)
                        if netdata_ram_gb >= 40:
                            cluster_ram_gb = netdata_ram_gb
        except Exception as e:
            logger.warning(f"Failed to fetch netdata info: {e}")

        # Get CPU utilization metrics from k8s_state
        try:
            k8s_state_url = f"{netdata_url.replace('netdata-parent', 'netdata-k8s-state')}"
            
            # Try to get CPU utilization - first try the specific chart
            cpu_response = requests.get(
                f"{k8s_state_url}/api/v1/data",
                params={'chart': 'k8s_state.node_allocatable_cpu_requests_utilization', 'points': 1},
                timeout=timeout
            )
            
            if cpu_response.status_code == 200:
                cpu_data = cpu_response.json()
                if 'data' in cpu_data and len(cpu_data['data']) > 0:
                    latest = cpu_data['data'][0]
                    cpu_utilization = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                    
                    metrics['cpu'] = {
                        'percentage': round(cpu_utilization, 1),
                        'total_cores': int(cluster_cores),
                        'description': 'CPU Utilization (requests)'
                    }
            else:
                # Fallback: try to aggregate CPU usage from individual pods
                logger.warning(f"CPU utilization chart not found, trying pod aggregation")
                # For now, set a default value
                metrics['cpu'] = {
                    'percentage': 0.0,
                    'total_cores': int(cluster_cores),
                    'description': 'CPU Utilization (unavailable)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch CPU utilization metrics: {e}")
            metrics['cpu'] = {
                'percentage': 0.0,
                'total_cores': int(cluster_cores),
                'description': 'CPU Utilization (unavailable)'
            }

        try:
            # Get memory utilization metrics from k8s_state
            memory_response = requests.get(
                f"{k8s_state_url}/api/v1/data",
                params={'chart': 'k8s_state.node_allocatable_memory_requests_utilization', 'points': 1},
                timeout=timeout
            )
            if memory_response.status_code == 200:
                memory_data = memory_response.json()
                if 'data' in memory_data and len(memory_data['data']) > 0:
                    latest = memory_data['data'][0]
                    memory_utilization = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                    
                    # Calculate used GB based on utilization percentage
                    memory_used_gb = round((memory_utilization / 100) * cluster_ram_gb, 1)
                    
                    metrics['memory'] = {
                        'total_gb': cluster_ram_gb,
                        'used_gb': memory_used_gb,
                        'percentage': round(memory_utilization, 1),
                        'description': 'Memory Utilization (requests)'
                    }
            else:
                # Fallback: set default values
                logger.warning(f"Memory utilization chart not found")
                metrics['memory'] = {
                    'total_gb': cluster_ram_gb,
                    'used_gb': 0.0,
                    'percentage': 0.0,
                    'description': 'Memory Utilization (unavailable)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch memory utilization metrics: {e}")
            metrics['memory'] = {
                'total_gb': cluster_ram_gb,
                'used_gb': 0.0,
                'percentage': 0.0,
                'description': 'Memory Utilization (unavailable)'
            }

        # Get network activity from netdata
        try:
            clients_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={'chart': 'netdata.clients', 'points': 1},
                timeout=timeout
            )
            requests_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={'chart': 'netdata.requests', 'points': 1},
                timeout=timeout
            )
            
            total_clients = 0
            total_requests = 0
            
            if clients_response.status_code == 200:
                clients_data = clients_response.json()
                if 'data' in clients_data and len(clients_data['data']) > 0:
                    latest = clients_data['data'][0]
                    total_clients = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
            
            if requests_response.status_code == 200:
                requests_data = requests_response.json()
                if 'data' in requests_data and len(requests_data['data']) > 0:
                    latest = requests_data['data'][0]
                    total_requests = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
            
            metrics['network'] = {
                'active_connections': int(total_clients),
                'api_requests_ps': round(total_requests, 1),
                'description': 'Network Activity'
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch network metrics: {e}")

        # Set reachable nodes count
        metrics['reachable_nodes'] = metrics['nodes_count'] if metrics['nodes_count'] > 0 else 3
        
        # Cache the metrics for 5 seconds
        cache.set('netdata_metrics', metrics, 5)
        
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
            'memory': None,
            'pods': None,
            'network': None,
            'status': 'unavailable',
            'error': 'Unable to connect to monitoring service'
        })
    except Exception as e:
        logger.error(f"Unexpected error fetching metrics: {e}")
        return JsonResponse({
            'cpu': None,
            'memory': None,
            'pods': None,
            'network': None,
            'status': 'error',
            'error': 'Internal error'
        })
