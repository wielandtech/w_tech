from django.shortcuts import render
from django.http import JsonResponse, Http404
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.html import format_html
import requests
import logging
# from kubernetes import client, config  # No longer needed - using k8s_state metrics

logger = logging.getLogger(__name__)


def homepage(request):
    return render(request, 'core/index.html')


def contact(request):
    """Contact page view with form handling and email sending."""
    from .forms import ContactForm

    # Check ReCaptcha configuration
    if not settings.RECAPTCHA_PUBLIC_KEY or not settings.RECAPTCHA_PRIVATE_KEY:
        messages.warning(request, 'Anti-spam verification is not configured. Please contact the administrator if this persists.')
        logger.warning("ReCaptcha keys not configured: RECAPTCHA_PUBLIC_KEY or RECAPTCHA_PRIVATE_KEY missing")
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Get form data
            cd = form.cleaned_data
            name = cd['name']
            email = cd['email']
            subject = cd['subject']
            message = cd['message']
            
            # Prepare email content
            email_subject = f"Contact Form: {subject}"
            email_message = f"""
New contact form submission from {name} ({email})

Subject: {subject}

Message:
{message}

---
This message was sent from the contact form on wielandtech.com
            """.strip()
            
            try:
                # Check if email configuration is available
                if not settings.EMAIL_HOST_PASSWORD:
                    messages.error(request, 'Email service is not configured. Please contact the administrator.')
                    logger.error("Email configuration missing: EMAIL_HOST_PASSWORD not set")
                else:
                    # Send email with timeout
                    send_mail(
                        email_subject,
                        email_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.CONTACT_EMAIL],
                        fail_silently=False
                    )
                    messages.success(request, 'Thank you for your message! I will get back to you as soon as possible.')
                    logger.info(f"Contact form email sent successfully from {email}")
                    
                    # Clear the form after successful submission
                    form = ContactForm()
            except Exception as e:
                logger.error(f"Failed to send contact form email: {str(e)}")
                messages.error(request, f'Failed to send message. Please try again later or contact me directly at {settings.CONTACT_EMAIL}')
    else:
        form = ContactForm()
    
    return render(request, 'core/contact.html', {'form': form})


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
    # Temporarily disable caching for debugging
    # cached_metrics = cache.get('netdata_metrics')
    # if cached_metrics:
    #     cached_metrics['cache_hit'] = True
    #     return JsonResponse(cached_metrics)

    try:
        netdata_url = settings.NETDATA_URL
        timeout = 3
        logger.warning(f"Using Netdata URL: {netdata_url}")

        # Cluster constants
        cluster_cores = 18  # 3 nodes * 6 cores per node
        cluster_ram_gb = 48  # 3 nodes * 16GB per node

        metrics = {
            'cpu': None,
            'memory': None,
            'pods': None,
            'network': None,
            'status': 'ok',
            'cache_hit': False,
            'errors': [],
            'nodes_count': 3,
            'reachable_nodes': 3,
        }

        # Get pod count from k8s_state
        try:
            # Try the k8s_state service first
            k8s_state_url = f"{netdata_url.replace('netdata-parent', 'netdata-k8s-state')}"
            pods_url = f"{k8s_state_url}/api/v1/data?chart=k8s_state.pod_status.running&points=1"
            logger.warning(f"Pods API call (k8s_state): {pods_url}")
            pods_response = requests.get(
                f"{k8s_state_url}/api/v1/data",
                params={'chart': 'k8s_state.pod_status.running', 'points': 1},
                timeout=timeout
            )

            logger.warning(f"Pods response status (k8s_state): {pods_response.status_code}")

            if pods_response.status_code == 200:
                pods_data = pods_response.json()
                logger.warning(f"Pods response data: {pods_data}")
                if 'data' in pods_data and len(pods_data['data']) > 0:
                    latest = pods_data['data'][0]
                    logger.warning(f"Pods latest data: {latest}")
                    running_pods = int(latest[1]) if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                    logger.warning(f"Pods count: {running_pods}")
                    metrics['pods'] = {
                        'count': running_pods,
                        'description': 'Running Pods'
                    }
                else:
                    logger.warning("Pods response has no data from k8s_state")
                    # Try fallback chart on main netdata
                    pods_response = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': 'k8s_state.pods', 'points': 1},
                        timeout=timeout
                    )
                    logger.warning(f"Pods fallback API call: {netdata_url}/api/v1/data?chart=k8s_state.pods&points=1")
                    logger.warning(f"Pods fallback response status: {pods_response.status_code}")

                    if pods_response.status_code == 200:
                        pods_data = pods_response.json()
                        logger.warning(f"Pods fallback response data: {pods_data}")
                        if 'data' in pods_data and len(pods_data['data']) > 0:
                            latest = pods_data['data'][0]
                            logger.warning(f"Pods fallback latest data: {latest}")
                            running_pods = int(latest[1]) if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                            logger.warning(f"Pods fallback count: {running_pods}")
                            metrics['pods'] = {
                                'count': running_pods,
                                'description': 'Running Pods'
                            }
                        else:
                            metrics['pods'] = {
                                'count': 0,
                                'description': 'Running Pods (no data)'
                            }
                    else:
                        metrics['pods'] = {
                            'count': 0,
                            'description': 'Running Pods (unavailable)'
                        }
            else:
                logger.warning(f"Pods API returned status {pods_response.status_code}, trying fallback")
                # Try fallback chart on main netdata
                pods_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={'chart': 'k8s_state.pods', 'points': 1},
                    timeout=timeout
                )
                logger.warning(f"Pods fallback API call: {netdata_url}/api/v1/data?chart=k8s_state.pods&points=1")
                logger.warning(f"Pods fallback response status: {pods_response.status_code}")

                if pods_response.status_code == 200:
                    pods_data = pods_response.json()
                    logger.warning(f"Pods fallback response data: {pods_data}")
                    if 'data' in pods_data and len(pods_data['data']) > 0:
                        latest = pods_data['data'][0]
                        logger.warning(f"Pods fallback latest data: {latest}")
                        running_pods = int(latest[1]) if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                        logger.warning(f"Pods fallback count: {running_pods}")
                        metrics['pods'] = {
                            'count': running_pods,
                            'description': 'Running Pods'
                        }
                    else:
                        metrics['pods'] = {
                            'count': 0,
                            'description': 'Running Pods (no data)'
                        }
                else:
                    metrics['pods'] = {
                        'count': 0,
                        'description': 'Running Pods (unavailable)'
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch pod counts: {e}")
            metrics['pods'] = {
                'count': 0,
                'description': 'Running Pods (error)'
            }

        # Get list of nodes to query
        netdata_hosts = settings.NETDATA_HOSTS
        logger.warning(f"Querying nodes: {netdata_hosts}")

        # Get CPU utilization aggregated across nodes
        try:
            total_cpu_percentage = 0
            node_count = 0

            for node in netdata_hosts:
                try:
                    cpu_response = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': 'system.cpu', 'node': node, 'points': 1, 'after': -10},
                        timeout=timeout
                    )

                    logger.warning(f"CPU API call for node {node}: {netdata_url}/api/v1/data?chart=system.cpu&node={node}&points=1&after=-10")
                    logger.warning(f"CPU response status for {node}: {cpu_response.status_code}")

                    if cpu_response.status_code == 200:
                        cpu_data = cpu_response.json()
                        logger.warning(f"CPU response data for {node}: {cpu_data}")
                        if 'data' in cpu_data and len(cpu_data['data']) > 0:
                            latest = cpu_data['data'][0]
                            logger.warning(f"CPU latest data for {node}: {latest}")
                            if len(latest) >= 2:
                                # CPU data is an array of different CPU usage types, sum them for total usage
                                # Skip timestamp (index 0) and sum all CPU values including iowait
                                cpu_values = [v for v in latest[1:] if isinstance(v, (int, float))]
                                node_cpu_usage = sum(cpu_values)
                                logger.warning(f"CPU values for {node}: {cpu_values}, total: {node_cpu_usage}")
                                total_cpu_percentage += node_cpu_usage
                                node_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch CPU from node {node}: {e}")
                    continue

            if node_count > 0:
                # Average CPU across all nodes
                avg_cpu_percentage = total_cpu_percentage / node_count
                logger.warning(f"Aggregated CPU: {total_cpu_percentage} total from {node_count} nodes, average: {avg_cpu_percentage}")
                metrics['cpu'] = {
                    'percentage': round(avg_cpu_percentage, 1),
                    'total_cores': cluster_cores,
                    'description': f'CPU Utilization ({node_count} nodes)'
                }
            else:
                metrics['cpu'] = {
                    'percentage': 0.0,
                    'total_cores': cluster_cores,
                    'description': 'CPU Utilization (no nodes available)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch CPU metrics: {e}")
            metrics['cpu'] = {
                'percentage': 0.0,
                'total_cores': cluster_cores,
                'description': 'CPU Utilization (error)'
            }

            # Get memory utilization aggregated across nodes
            try:
                total_used_memory_mb = 0
                total_total_memory_mb = 0
                memory_node_count = 0
                memory_data_points = []

                for node in netdata_hosts:
                    try:
                        memory_response = requests.get(
                            f"{netdata_url}/api/v1/data",
                            params={'chart': 'system.ram', 'node': node, 'points': 1, 'after': 0},
                            timeout=timeout
                        )

                        logger.warning(f"Memory API call for node {node}: {netdata_url}/api/v1/data?chart=system.ram&node={node}&points=1&after=0")
                        logger.warning(f"Memory response status for {node}: {memory_response.status_code}")

                        if memory_response.status_code == 200:
                            memory_data = memory_response.json()
                            logger.warning(f"Memory response data for {node}: {memory_data}")
                            if 'data' in memory_data and len(memory_data['data']) > 0:
                                latest = memory_data['data'][0]
                                logger.warning(f"Memory latest data for {node}: {latest}")
                                # Memory data format: [time, free, used, cached, buffers] (in MB)
                                if len(latest) >= 5:
                                    timestamp = latest[0]
                                    memory_free_mb = latest[1] if isinstance(latest[1], (int, float)) else 0
                                    memory_used_mb = latest[2] if isinstance(latest[2], (int, float)) else 0
                                    memory_cached_mb = latest[3] if isinstance(latest[3], (int, float)) else 0
                                    memory_buffers_mb = latest[4] if isinstance(latest[4], (int, float)) else 0

                                    # Total memory = used + free + cached + buffers
                                    node_total_mb = memory_used_mb + memory_free_mb + memory_cached_mb + memory_buffers_mb
                                    logger.warning(f"Memory for {node} (timestamp: {timestamp}) - free: {memory_free_mb}MB, used: {memory_used_mb}MB, cached: {memory_cached_mb}MB, buffers: {memory_buffers_mb}MB, total: {node_total_mb}MB")

                                    total_used_memory_mb += memory_used_mb
                                    total_total_memory_mb += node_total_mb
                                    memory_node_count += 1

                                    # Store data point for analysis
                                    memory_data_points.append({
                                        'node': node,
                                        'timestamp': timestamp,
                                        'used_mb': memory_used_mb,
                                        'total_mb': node_total_mb
                                    })
                    except Exception as e:
                        logger.warning(f"Failed to fetch RAM from node {node}: {e}")
                        continue

                if memory_node_count > 0:
                    # Check if all nodes have identical data
                    if len(memory_data_points) > 1:
                        first_point = memory_data_points[0]
                        all_identical = all(
                            point['timestamp'] == first_point['timestamp'] and
                            point['used_mb'] == first_point['used_mb'] and
                            point['total_mb'] == first_point['total_mb']
                            for point in memory_data_points[1:]
                        )
                        if all_identical:
                            logger.warning(f"WARNING: All {len(memory_data_points)} nodes have identical memory data! This suggests node-specific memory charts may not be working properly.")
                            for point in memory_data_points:
                                logger.warning(f"  {point['node']}: timestamp={point['timestamp']}, used={point['used_mb']}MB, total={point['total_mb']}MB")

                    # Sum memory across all nodes (total cluster memory)
                    cluster_used_memory_mb = total_used_memory_mb
                    cluster_total_memory_mb = total_total_memory_mb

                    # Convert MB to GB
                    memory_used_gb = round(cluster_used_memory_mb / 1024, 1)
                    memory_total_gb = round(cluster_total_memory_mb / 1024, 1)
                    memory_percentage = round((cluster_used_memory_mb / cluster_total_memory_mb) * 100, 1) if cluster_total_memory_mb > 0 else 0
                    logger.warning(f"Total Cluster Memory: {cluster_used_memory_mb}MB used, {cluster_total_memory_mb}MB total across {memory_node_count} nodes, {memory_used_gb}GB used, {memory_total_gb}GB total, {memory_percentage}%")

                    metrics['memory'] = {
                        'total_gb': memory_total_gb,
                        'used_gb': memory_used_gb,
                        'percentage': memory_percentage,
                        'description': f'Cluster Memory ({memory_node_count} nodes)'
                    }
                else:
                    metrics['memory'] = {
                        'total_gb': cluster_ram_gb,
                        'used_gb': 0.0,
                        'percentage': 0.0,
                        'description': 'Memory Utilization (no nodes available)'
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch memory metrics: {e}")
            metrics['memory'] = {
                'total_gb': cluster_ram_gb,
                'used_gb': 0.0,
                'percentage': 0.0,
                'description': 'Memory Utilization (error)'
            }

        # Get network metrics aggregated across nodes
        try:
            total_received_bps = 0
            total_sent_bps = 0
            node_count = 0

            for node in netdata_hosts:
                try:
                    net_response = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': 'system.net', 'node': node, 'points': 1, 'after': -10},
                        timeout=timeout
                    )

                    logger.warning(f"Network API call for node {node}: {netdata_url}/api/v1/data?chart=system.net&node={node}&points=1&after=-10")
                    logger.warning(f"Network response status for {node}: {net_response.status_code}")

                    if net_response.status_code == 200:
                        net_data = net_response.json()
                        logger.warning(f"Network response data for {node}: {net_data}")
                        if 'data' in net_data and len(net_data['data']) > 0:
                            latest = net_data['data'][0]
                            logger.warning(f"Network latest data for {node}: {latest}")
                            if len(latest) >= 3:  # timestamp, received, sent
                                received_bps = latest[1] if isinstance(latest[1], (int, float)) else 0
                                sent_bps = latest[2] if isinstance(latest[2], (int, float)) else 0
                                logger.warning(f"Network for {node} - received: {received_bps}bps, sent: {sent_bps}bps")

                                total_received_bps += received_bps
                                total_sent_bps += sent_bps
                                node_count += 1
                                logger.warning(f"Network node {node} added successfully - running total: {total_received_bps}bps received, {total_sent_bps}bps sent")
                            else:
                                logger.warning(f"Network data for {node} has insufficient fields: {len(latest)}")
                        else:
                            logger.warning(f"Network response for {node} has no data array")
                    else:
                        logger.warning(f"Network API for {node} returned status {net_response.status_code}")
                except Exception as e:
                    logger.warning(f"Failed to fetch network from node {node}: {e}")
                    continue

            if node_count > 0:
                # Sum network metrics across all nodes (total cluster network traffic)
                cluster_received_bps = total_received_bps
                cluster_sent_bps = total_sent_bps

                received_mbps = round(cluster_received_bps / (1024**2), 1)
                sent_mbps = round(cluster_sent_bps / (1024**2), 1)
                logger.warning(f"Total Cluster Network: {cluster_received_bps}bps received, {cluster_sent_bps}bps sent across {node_count} nodes, {received_mbps}Mbps received, {sent_mbps}Mbps sent")

                metrics['network'] = {
                    'bandwidth_mbps': round(received_mbps + sent_mbps, 1),
                    'received_mbps': received_mbps,
                    'sent_mbps': sent_mbps,
                    'description': f'Cluster Network ({node_count} nodes)'
                }
            else:
                logger.warning("No network data from any nodes")
                metrics['network'] = None
        except Exception as e:
            logger.warning(f"Failed to fetch network metrics: {e}")
            metrics['network'] = None

        # Temporarily disable caching for debugging
        # cache.set('netdata_metrics', metrics, 5)

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
