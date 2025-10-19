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

        # Aggregate k8s_state metrics from all nodes
        cpu_utilization_values = []
        memory_utilization_values = []
        pod_counts = []
        total_clients = 0
        total_requests = 0
        reachable_nodes = 0
        
        for host in netdata_hosts:
            try:
                # Fetch CPU utilization from k8s_state
                cpu_response = requests.get(
                    f"{k8s_state_url}/api/v1/data",
                    params={
                        'chart': f'k8s_state_k8s-metrics_node_{host}.allocatable_cpu_requests_utilization',
                        'points': 1
                    },
                    timeout=timeout
                )
                if cpu_response.status_code == 200:
                    cpu_data = cpu_response.json()
                    if 'data' in cpu_data and len(cpu_data['data']) > 0:
                        latest = cpu_data['data'][0]
                        cpu_util = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        cpu_utilization_values.append(cpu_util)
                        reachable_nodes += 1
                
                # Fetch memory utilization from k8s_state
                memory_response = requests.get(
                    f"{k8s_state_url}/api/v1/data",
                    params={
                        'chart': f'k8s_state_k8s-metrics_node_{host}.allocatable_mem_requests_utilization',
                        'points': 1
                    },
                    timeout=timeout
                )
                if memory_response.status_code == 200:
                    memory_data = memory_response.json()
                    if 'data' in memory_data and len(memory_data['data']) > 0:
                        latest = memory_data['data'][0]
                        memory_util = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        memory_utilization_values.append(memory_util)
                
                # Fetch pod count from k8s_state
                pods_response = requests.get(
                    f"{k8s_state_url}/api/v1/data",
                    params={
                        'chart': f'k8s_state_k8s-metrics_node_{host}.allocated_pods_usage',
                        'points': 1
                    },
                    timeout=timeout
                )
                if pods_response.status_code == 200:
                    pods_data = pods_response.json()
                    if 'data' in pods_data and len(pods_data['data']) > 0:
                        latest = pods_data['data'][0]
                        # latest[2] is the 'allocated' pods count
                        host_pods = latest[2] if len(latest) > 2 and isinstance(latest[2], (int, float)) else 0
                        pod_counts.append(host_pods)
                
                # Fetch network activity from netdata (fallback to netdata metrics for network)
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
        if cpu_utilization_values:
            avg_cpu_util = sum(cpu_utilization_values) / len(cpu_utilization_values)
            metrics['cpu'] = {
                'percentage': round(avg_cpu_util, 1),
                'total_cores': cluster_cores,
                'description': 'CPU Usage'
            }
        
        # Calculate cluster-wide memory metrics
        if memory_utilization_values and cluster_ram_gb > 0:
            avg_memory_util = sum(memory_utilization_values) / len(memory_utilization_values)
            # Convert percentage to actual GB usage
            estimated_cluster_usage_gb = round((avg_memory_util / 100) * cluster_ram_gb, 1)
            
            # Ensure we have a meaningful decimal value (at least 0.1 GB)
            if estimated_cluster_usage_gb < 0.1 and avg_memory_util > 0:
                estimated_cluster_usage_gb = 0.1
            
            metrics['memory'] = {
                'total_gb': cluster_ram_gb,
                'used_gb': estimated_cluster_usage_gb,
                'percentage': round(avg_memory_util, 1),
                'description': 'Memory Usage'
            }
        
        # Calculate total pod count
        total_pods = sum(pod_counts) if pod_counts else 0
        metrics['pods'] = {
            'count': int(total_pods),
            'description': 'Number of Pods'
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
