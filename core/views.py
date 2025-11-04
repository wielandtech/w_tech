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


def discover_netdata_charts(netdata_url, chart_patterns, timeout=3):
    """
    Discover available Netdata charts matching given patterns.
    Returns a dict mapping pattern names to lists of matching chart names.
    """
    try:
        charts_response = requests.get(f"{netdata_url}/api/v1/charts", timeout=timeout)
        if charts_response.status_code != 200:
            logger.warning(f"Failed to fetch charts list: {charts_response.status_code}")
            return {}

        charts_data = charts_response.json()
        available_charts = charts_data.get('charts', {})

        discovered = {}
        for pattern_name, pattern in chart_patterns.items():
            matching_charts = [chart for chart in available_charts.keys() if pattern in chart]
            discovered[pattern_name] = matching_charts
            logger.info(f"Discovered {len(matching_charts)} charts for {pattern_name}: {matching_charts[:3]}{'...' if len(matching_charts) > 3 else ''}")

        return discovered
    except Exception as e:
        logger.warning(f"Failed to discover charts: {e}")
        return {}


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
            'reachable_nodes': 0,
            'debug': {}  # Add debug info for troubleshooting
        }

        # Discover available system charts
        chart_patterns = {
            'cpu': 'system.cpu',
            'ram': 'system.ram',
            'net': 'system.net'
        }
        discovered_charts = discover_netdata_charts(netdata_url, chart_patterns, timeout)
        metrics['debug']['discovered_charts'] = discovered_charts
        
        # Get cluster resources and pod count from k8s_state
        cluster_cores = 18  # 3 nodes * 6 cores per node
        cluster_ram_gb = 48  # 3 nodes * 16GB per node
        metrics['nodes_count'] = 3
        
        # Get pod count from k8s_state aggregate charts
        try:
            k8s_state_url = f"{netdata_url.replace('netdata-parent', 'netdata-k8s-state')}"

            # Try to get running pods directly from aggregate chart
            running_pods_response = requests.get(
                f"{k8s_state_url}/api/v1/data",
                params={'chart': 'k8s_state.pod_status.running', 'points': 1},
                timeout=timeout
            )

            if running_pods_response.status_code == 200:
                running_pods_data = running_pods_response.json()
                if 'data' in running_pods_data and len(running_pods_data['data']) > 0:
                    latest = running_pods_data['data'][0]
                    running_pods = int(latest[1]) if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                else:
                    running_pods = 0
            else:
                # Fallback: try total pods chart
                total_pods_response = requests.get(
                    f"{k8s_state_url}/api/v1/data",
                    params={'chart': 'k8s_state.pods', 'points': 1},
                    timeout=timeout
                )
                if total_pods_response.status_code == 200:
                    total_pods_data = total_pods_response.json()
                    if 'data' in total_pods_data and len(total_pods_data['data']) > 0:
                        latest = total_pods_data['data'][0]
                        running_pods = int(latest[1]) if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
                    else:
                        running_pods = 0
                else:
                    running_pods = 0

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

        # Get CPU utilization metrics from discovered charts
        try:
            cpu_charts = discovered_charts.get('cpu', [])
            if cpu_charts:
                # Aggregate CPU metrics from all discovered charts
                total_cpu_percentage = 0
                chart_count = 0

                for chart_name in cpu_charts:
                    try:
                        cpu_response = requests.get(
                            f"{netdata_url}/api/v1/data",
                            params={'chart': chart_name, 'points': 1, 'format': 'json'},
                            timeout=timeout
                        )

                        if cpu_response.status_code == 200:
                            cpu_data = cpu_response.json()
                            if 'data' in cpu_data and len(cpu_data['data']) > 0:
                                latest = cpu_data['data'][0]
                                # Log the raw data for debugging
                                logger.debug(f"CPU chart {chart_name} raw data: {latest}")

                                # Try to parse CPU percentage (different formats possible)
                                cpu_value = None
                                if len(latest) >= 2:
                                    cpu_value = latest[1] if isinstance(latest[1], (int, float)) else None

                                if cpu_value is not None:
                                    # If value is > 100, it's likely milliseconds, convert to percentage
                                    if cpu_value > 100:
                                        cpu_percentage = min(100.0, max(0.0, cpu_value / 10.0))
                                    else:
                                        cpu_percentage = min(100.0, max(0.0, cpu_value))

                                    total_cpu_percentage += cpu_percentage
                                    chart_count += 1
                                    logger.debug(f"Parsed CPU {cpu_percentage}% from {chart_name}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch CPU from {chart_name}: {e}")
                        continue

                if chart_count > 0:
                    # Average CPU across all nodes
                    avg_cpu_percentage = total_cpu_percentage / chart_count
                    metrics['cpu'] = {
                        'percentage': round(avg_cpu_percentage, 1),
                        'total_cores': int(cluster_cores),
                        'description': f'CPU Utilization ({chart_count} nodes)'
                    }
                    metrics['debug']['cpu_charts_used'] = cpu_charts
                    metrics['debug']['cpu_chart_count'] = chart_count
                else:
                    metrics['cpu'] = {
                        'percentage': 0.0,
                        'total_cores': int(cluster_cores),
                        'description': 'CPU Utilization (no data)'
                    }
            else:
                logger.warning("No CPU charts discovered")
                metrics['cpu'] = {
                    'percentage': 0.0,
                    'total_cores': int(cluster_cores),
                    'description': 'CPU Utilization (charts not found)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch CPU utilization metrics: {e}")
            metrics['cpu'] = {
                'percentage': 0.0,
                'total_cores': int(cluster_cores),
                'description': 'CPU Utilization (error)'
            }

        try:
            # Get memory utilization metrics from discovered charts
            ram_charts = discovered_charts.get('ram', [])
            if ram_charts:
                # Aggregate memory metrics from all discovered charts
                total_used_memory = 0
                total_free_memory = 0
                chart_count = 0

                for chart_name in ram_charts:
                    try:
                        memory_response = requests.get(
                            f"{netdata_url}/api/v1/data",
                            params={'chart': chart_name, 'points': 1, 'format': 'json'},
                            timeout=timeout
                        )

                        if memory_response.status_code == 200:
                            memory_data = memory_response.json()
                            if 'data' in memory_data and len(memory_data['data']) > 0:
                                latest = memory_data['data'][0]
                                # Log the raw data for debugging
                                logger.debug(f"RAM chart {chart_name} raw data: {latest}")

                                # Try to parse memory values (different formats possible)
                                if len(latest) >= 3:  # Ensure we have timestamp, used, free
                                    memory_used_bytes = latest[1] if isinstance(latest[1], (int, float)) else 0
                                    memory_free_bytes = latest[2] if isinstance(latest[2], (int, float)) else 0

                                    total_used_memory += memory_used_bytes
                                    total_free_memory += memory_free_bytes
                                    chart_count += 1
                                    logger.debug(f"Parsed RAM {memory_used_bytes/1024**3:.1f}GB used, {memory_free_bytes/1024**3:.1f}GB free from {chart_name}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch RAM from {chart_name}: {e}")
                        continue

                if chart_count > 0:
                    # Average memory across all nodes (or sum if we want cluster total)
                    avg_used_memory = total_used_memory / chart_count
                    avg_free_memory = total_free_memory / chart_count

                    # Convert to GB
                    memory_used_gb = round(avg_used_memory / (1024**3), 1)
                    memory_free_gb = round(avg_free_memory / (1024**3), 1)
                    memory_total_gb = memory_used_gb + memory_free_gb

                    # Calculate percentage
                    memory_percentage = round((memory_used_gb / memory_total_gb) * 100, 1) if memory_total_gb > 0 else 0

                    metrics['memory'] = {
                        'total_gb': round(memory_total_gb, 1),
                        'used_gb': memory_used_gb,
                        'percentage': memory_percentage,
                        'description': f'Memory Utilization ({chart_count} nodes)'
                    }
                    metrics['debug']['ram_charts_used'] = ram_charts
                    metrics['debug']['ram_chart_count'] = chart_count
                else:
                    metrics['memory'] = {
                        'total_gb': cluster_ram_gb,
                        'used_gb': 0.0,
                        'percentage': 0.0,
                        'description': 'Memory Utilization (no data)'
                    }
            else:
                logger.warning("No RAM charts discovered")
                metrics['memory'] = {
                    'total_gb': cluster_ram_gb,
                    'used_gb': 0.0,
                    'percentage': 0.0,
                    'description': 'Memory Utilization (charts not found)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch memory utilization metrics: {e}")
            metrics['memory'] = {
                'total_gb': cluster_ram_gb,
                'used_gb': 0.0,
                'percentage': 0.0,
                'description': 'Memory Utilization (error)'
            }

        # Get network traffic metrics (actual bandwidth usage)
        try:
            # Try system.net first (aggregated network interface traffic)
            net_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={'chart': 'system.net', 'points': 1},
                timeout=timeout
            )

            if net_response.status_code == 200:
                net_data = net_response.json()
                if 'data' in net_data and len(net_data['data']) > 0:
                    latest = net_data['data'][0]
                    # system.net typically has: [timestamp, received, sent] in bytes/s
                    if len(latest) >= 3:
                        received_bps = latest[1] if isinstance(latest[1], (int, float)) else 0
                        sent_bps = latest[2] if isinstance(latest[2], (int, float)) else 0

                        # Convert to Mbps for display
                        received_mbps = round(received_bps / (1024**2), 1)
                        sent_mbps = round(sent_bps / (1024**2), 1)
                        total_mbps = round(received_mbps + sent_mbps, 1)

                        metrics['network'] = {
                            'bandwidth_mbps': total_mbps,
                            'received_mbps': received_mbps,
                            'sent_mbps': sent_mbps,
                            'description': 'Network Bandwidth (Mbps)'
                        }
                    else:
                        # Fallback: try TCP connection count
                        tcp_response = requests.get(
                            f"{netdata_url}/api/v1/data",
                            params={'chart': 'system.ip.tcp', 'points': 1},
                            timeout=timeout
                        )
                        if tcp_response.status_code == 200:
                            tcp_data = tcp_response.json()
                            if 'data' in tcp_data and len(tcp_data['data']) > 0:
                                latest = tcp_data['data'][0]
                                # system.ip.tcp has active connections count
                                active_connections = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0

                                metrics['network'] = {
                                    'active_connections': int(active_connections),
                                    'description': 'Active TCP Connections'
                                }
                            else:
                                metrics['network'] = None
                        else:
                            metrics['network'] = None
                else:
                    metrics['network'] = None
            else:
                # Fallback to original metrics if system.net unavailable
                clients_response = requests.get(
                    f"{netdata_url}/api/v1/data",
                    params={'chart': 'netdata.clients', 'points': 1},
                    timeout=timeout
                )

                total_clients = 0
                if clients_response.status_code == 200:
                    clients_data = clients_response.json()
                    if 'data' in clients_data and len(clients_data['data']) > 0:
                        latest = clients_data['data'][0]
                        total_clients = latest[1] if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0

                metrics['network'] = {
                    'active_connections': int(total_clients),
                    'description': 'Active Connections'
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
