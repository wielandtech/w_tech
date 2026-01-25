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


def homelab(request):
    """Homelab dashboard page displaying cluster metrics."""
    return render(request, 'core/homelab.html')


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
    cached_metrics = cache.get('netdata_metrics')
    if cached_metrics:
        cached_metrics['cache_hit'] = True
        return JsonResponse(cached_metrics)

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
            'disk_io': None,
            'uptime': None,
            'temperature': None,
            'deployments': None,
            'status': 'ok',
            'cache_hit': False,
            'errors': [],
            'nodes_count': 3,
            'reachable_nodes': 3,
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
                    'description': 'CPU Utilization'
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

            for node in netdata_hosts:
                try:
                    memory_response = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': 'system.ram', 'node': node, 'points': 1, 'after': -10},
                        timeout=timeout
                    )

                    logger.warning(f"Memory API call for node {node}: {netdata_url}/api/v1/data?chart=system.ram&node={node}&points=1&after=-10")
                    logger.warning(f"Memory response status for {node}: {memory_response.status_code}")

                    if memory_response.status_code == 200:
                        memory_data = memory_response.json()
                        logger.warning(f"Memory response data for {node}: {memory_data}")
                        if 'data' in memory_data and len(memory_data['data']) > 0:
                            latest = memory_data['data'][0]
                            logger.warning(f"Memory latest data for {node}: {latest}")
                            # Memory data format: [time, free, used, cached, buffers] (in MB)
                            if len(latest) >= 5:
                                memory_free_mb = latest[1] if isinstance(latest[1], (int, float)) else 0
                                memory_used_mb = latest[2] if isinstance(latest[2], (int, float)) else 0
                                memory_cached_mb = latest[3] if isinstance(latest[3], (int, float)) else 0
                                memory_buffers_mb = latest[4] if isinstance(latest[4], (int, float)) else 0

                                # Total memory = used + free + cached + buffers
                                node_total_mb = memory_used_mb + memory_free_mb + memory_cached_mb + memory_buffers_mb
                                logger.warning(f"Memory for {node} - free: {memory_free_mb}MB, used: {memory_used_mb}MB, cached: {memory_cached_mb}MB, buffers: {memory_buffers_mb}MB, total: {node_total_mb}MB")

                                total_used_memory_mb += memory_used_mb
                                total_total_memory_mb += node_total_mb
                                memory_node_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch RAM from node {node}: {e}")
                    continue

            if memory_node_count > 0:
                # Calculate cluster-wide memory metrics
                memory_used_gb = round(total_used_memory_mb / 1024, 1)
                memory_total_gb = round(total_total_memory_mb / 1024, 1)
                memory_percentage = round((total_used_memory_mb / total_total_memory_mb) * 100, 1) if total_total_memory_mb > 0 else 0
                logger.warning(f"Total Cluster Memory: {total_used_memory_mb}MB used, {total_total_memory_mb}MB total across {memory_node_count} nodes")

                metrics['memory'] = {
                    'total_gb': memory_total_gb,
                    'used_gb': memory_used_gb,
                    'percentage': memory_percentage,
                    'description': 'Memory Utilization'
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

        # Get pod count from k8s_state collector using API v2 with context aggregation
        try:
            # Use API v2 with contexts to get running pods across all nodes
            # The k8s_state.node_pods_phase context spans multiple nodes
            pods_response = requests.get(
                f"{netdata_url}/api/v2/data",
                params={
                    'contexts': 'k8s_state.node_pods_phase',
                    'dimensions': 'running',
                    'points': 1
                },
                timeout=timeout
            )

            if pods_response.status_code == 200:
                pods_data = pods_response.json()
                # API v2 returns summary.instances with per-node data
                # Sum the 'avg' (which is current value) from each instance
                running_pods = 0
                if 'summary' in pods_data and 'instances' in pods_data['summary']:
                    for instance in pods_data['summary']['instances']:
                        if 'sts' in instance and 'avg' in instance['sts']:
                            running_pods += int(instance['sts']['avg'])

                metrics['pods'] = {
                    'count': running_pods,
                    'description': 'Pods Running'
                }
            else:
                logger.warning(f"Pods API returned status {pods_response.status_code}")
                metrics['pods'] = {
                    'count': 0,
                    'description': 'Pods Running (unavailable)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch pod counts: {e}")
            metrics['pods'] = {
                'count': 0,
                'description': 'Pods Running (error)'
            }

        # Get network metrics using API v2 with net.net context (aggregates all interfaces)
        # Values are in kilobits/s, sent values are negative
        try:
            net_response = requests.get(
                f"{netdata_url}/api/v2/data",
                params={
                    'contexts': 'net.net',
                    'nodes': ','.join(netdata_hosts),
                    'points': 1,
                    'after': -10  # Get data from last 10 seconds for real-time values
                },
                timeout=timeout
            )

            if net_response.status_code == 200:
                net_data = net_response.json()
                # API v2 returns result.data with format [timestamp, [received, arp, pa], [sent, arp, pa]]
                if 'result' in net_data and 'data' in net_data['result'] and len(net_data['result']['data']) > 0:
                    latest = net_data['result']['data'][0]
                    # Format: [timestamp, [received_value, ...], [sent_value, ...]]
                    received_kbps = 0
                    sent_kbps = 0
                    if len(latest) >= 3:
                        # received is positive, sent is negative in netdata
                        if isinstance(latest[1], list) and len(latest[1]) > 0:
                            received_kbps = abs(latest[1][0]) if isinstance(latest[1][0], (int, float)) else 0
                        if isinstance(latest[2], list) and len(latest[2]) > 0:
                            sent_kbps = abs(latest[2][0]) if isinstance(latest[2][0], (int, float)) else 0

                    # Convert kilobits/s to Mbps (1 Mbps = 1000 kbps)
                    received_mbps = round(received_kbps / 1000, 2)
                    sent_mbps = round(sent_kbps / 1000, 2)

                    # Count how many nodes contributed
                    node_count = len(net_data.get('summary', {}).get('nodes', [])) or len(netdata_hosts)

                    metrics['network'] = {
                        'bandwidth_mbps': round(received_mbps + sent_mbps, 2),
                        'received_mbps': received_mbps,
                        'sent_mbps': sent_mbps,
                        'description': 'Network Utilization'
                    }
                else:
                    metrics['network'] = None
            else:
                logger.warning(f"Network API returned status {net_response.status_code}")
                metrics['network'] = None
        except Exception as e:
            logger.warning(f"Failed to fetch network metrics: {e}")
            metrics['network'] = None

        # Get disk I/O metrics aggregated across nodes
        try:
            total_read_kbps = 0
            total_write_kbps = 0
            disk_node_count = 0

            for node in netdata_hosts:
                try:
                    disk_response = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': 'system.io', 'node': node, 'points': 1, 'after': -10},
                        timeout=timeout
                    )

                    if disk_response.status_code == 200:
                        disk_data = disk_response.json()
                        if 'data' in disk_data and len(disk_data['data']) > 0:
                            latest = disk_data['data'][0]
                            # Disk I/O format: [time, in (read), out (write)] in KiB/s
                            if len(latest) >= 3:
                                read_kbps = abs(latest[1]) if isinstance(latest[1], (int, float)) else 0
                                write_kbps = abs(latest[2]) if isinstance(latest[2], (int, float)) else 0
                                total_read_kbps += read_kbps
                                total_write_kbps += write_kbps
                                disk_node_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fetch disk I/O from node {node}: {e}")
                    continue

            if disk_node_count > 0:
                # Convert KiB/s to MB/s
                read_mbps = round(total_read_kbps / 1024, 2)
                write_mbps = round(total_write_kbps / 1024, 2)
                metrics['disk_io'] = {
                    'read_mbps': read_mbps,
                    'write_mbps': write_mbps,
                    'total_mbps': round(read_mbps + write_mbps, 2),
                    'description': 'Disk I/O'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch disk I/O metrics: {e}")
            metrics['disk_io'] = None

        # Get uptime from the first reachable node (representative of cluster)
        try:
            max_uptime_seconds = 0
            min_uptime_seconds = float('inf')

            for node in netdata_hosts:
                try:
                    uptime_response = requests.get(
                        f"{netdata_url}/api/v1/data",
                        params={'chart': 'system.uptime', 'node': node, 'points': 1, 'after': -10},
                        timeout=timeout
                    )

                    if uptime_response.status_code == 200:
                        uptime_data = uptime_response.json()
                        if 'data' in uptime_data and len(uptime_data['data']) > 0:
                            latest = uptime_data['data'][0]
                            if len(latest) >= 2:
                                node_uptime = latest[1] if isinstance(latest[1], (int, float)) else 0
                                max_uptime_seconds = max(max_uptime_seconds, node_uptime)
                                min_uptime_seconds = min(min_uptime_seconds, node_uptime)
                except Exception as e:
                    logger.warning(f"Failed to fetch uptime from node {node}: {e}")
                    continue

            if max_uptime_seconds > 0:
                # Use minimum uptime (most recent reboot) for cluster uptime
                uptime_seconds = min_uptime_seconds if min_uptime_seconds != float('inf') else max_uptime_seconds
                # Convert to days, hours, minutes
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)

                if days > 0:
                    uptime_str = f"{days}d {hours}h"
                elif hours > 0:
                    uptime_str = f"{hours}h {minutes}m"
                else:
                    uptime_str = f"{minutes}m"

                metrics['uptime'] = {
                    'seconds': int(uptime_seconds),
                    'formatted': uptime_str,
                    'days': days,
                    'description': 'Cluster Uptime'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch uptime metrics: {e}")
            metrics['uptime'] = None

        # Get CPU temperature aggregated across nodes
        try:
            temps = []
            for node in netdata_hosts:
                try:
                    # Try different sensor chart names common on Intel systems
                    for chart_name in ['sensors.coretemp_isa_0000_temperature', 'sensors.coretemp-isa-0000_temperature']:
                        temp_response = requests.get(
                            f"{netdata_url}/api/v1/data",
                            params={'chart': chart_name, 'node': node, 'points': 1, 'after': -10},
                            timeout=timeout
                        )

                        if temp_response.status_code == 200:
                            temp_data = temp_response.json()
                            if 'data' in temp_data and len(temp_data['data']) > 0:
                                latest = temp_data['data'][0]
                                # Temperature data: [time, temp1, temp2, ...] - get max core temp
                                core_temps = [v for v in latest[1:] if isinstance(v, (int, float))]
                                if core_temps:
                                    temps.append(max(core_temps))
                                    break
                except Exception as e:
                    logger.warning(f"Failed to fetch temperature from node {node}: {e}")
                    continue

            if temps:
                avg_temp = round(sum(temps) / len(temps), 1)
                max_temp = round(max(temps), 1)
                metrics['temperature'] = {
                    'avg_celsius': avg_temp,
                    'max_celsius': max_temp,
                    'node_count': len(temps),
                    'description': 'CPU Temperature'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch temperature metrics: {e}")
            metrics['temperature'] = None

        # Get deployment status from k8s_state collector
        try:
            deployments_response = requests.get(
                f"{netdata_url}/api/v2/data",
                params={
                    'contexts': 'k8s_state.deployment_replicas_ready',
                    'points': 1
                },
                timeout=timeout
            )

            if deployments_response.status_code == 200:
                deploy_data = deployments_response.json()
                # Count deployments and check their status
                total_deployments = 0
                healthy_deployments = 0

                if 'summary' in deploy_data and 'instances' in deploy_data['summary']:
                    for instance in deploy_data['summary']['instances']:
                        total_deployments += 1
                        # If ready replicas > 0, consider it healthy
                        if 'sts' in instance and 'avg' in instance['sts']:
                            if instance['sts']['avg'] > 0:
                                healthy_deployments += 1

                metrics['deployments'] = {
                    'total': total_deployments,
                    'healthy': healthy_deployments,
                    'description': 'Deployments'
                }
            else:
                logger.warning(f"Deployments API returned status {deployments_response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to fetch deployment metrics: {e}")
            metrics['deployments'] = None

        cache.set('netdata_metrics', metrics, 1)

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
            'disk_io': None,
            'uptime': None,
            'temperature': None,
            'deployments': None,
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
            'disk_io': None,
            'uptime': None,
            'temperature': None,
            'deployments': None,
            'status': 'error',
            'error': 'Internal error'
        })
