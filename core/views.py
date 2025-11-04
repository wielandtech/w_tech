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
    cached_metrics = cache.get('netdata_metrics')
    if cached_metrics:
        cached_metrics['cache_hit'] = True
        return JsonResponse(cached_metrics)

    try:
        netdata_url = settings.NETDATA_URL
        timeout = 3

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
            k8s_state_url = f"{netdata_url.replace('netdata-parent', 'netdata-k8s-state')}"
            pods_response = requests.get(
                f"{k8s_state_url}/api/v1/data",
                params={'chart': 'k8s_state.pod_status.running', 'points': 1},
                timeout=timeout
            )

            if pods_response.status_code == 200:
                pods_data = pods_response.json()
                if 'data' in pods_data and len(pods_data['data']) > 0:
                    latest = pods_data['data'][0]
                    running_pods = int(latest[1]) if len(latest) > 1 and isinstance(latest[1], (int, float)) else 0
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

        # Get CPU utilization
        try:
            cpu_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={'chart': 'system.cpu', 'points': 1},
                timeout=timeout
            )

            if cpu_response.status_code == 200:
                cpu_data = cpu_response.json()
                if 'data' in cpu_data and len(cpu_data['data']) > 0:
                    latest = cpu_data['data'][0]
                    if len(latest) >= 2:
                        cpu_value = latest[1] if isinstance(latest[1], (int, float)) else None
                        if cpu_value is not None:
                            # Convert to percentage if needed
                            cpu_percentage = min(100.0, max(0.0, cpu_value if cpu_value <= 100 else cpu_value / 10.0))
                            metrics['cpu'] = {
                                'percentage': round(cpu_percentage, 1),
                                'total_cores': cluster_cores,
                                'description': 'CPU Utilization'
                            }
                        else:
                            metrics['cpu'] = {
                                'percentage': 0.0,
                                'total_cores': cluster_cores,
                                'description': 'CPU Utilization (invalid data)'
                            }
                    else:
                        metrics['cpu'] = {
                            'percentage': 0.0,
                            'total_cores': cluster_cores,
                            'description': 'CPU Utilization (no data)'
                        }
                else:
                    metrics['cpu'] = {
                        'percentage': 0.0,
                        'total_cores': cluster_cores,
                        'description': 'CPU Utilization (empty response)'
                    }
            else:
                metrics['cpu'] = {
                    'percentage': 0.0,
                    'total_cores': cluster_cores,
                    'description': 'CPU Utilization (unavailable)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch CPU metrics: {e}")
            metrics['cpu'] = {
                'percentage': 0.0,
                'total_cores': cluster_cores,
                'description': 'CPU Utilization (error)'
            }

        # Get memory utilization
        try:
            memory_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={'chart': 'system.ram', 'points': 1},
                timeout=timeout
            )

            if memory_response.status_code == 200:
                memory_data = memory_response.json()
                if 'data' in memory_data and len(memory_data['data']) > 0:
                    latest = memory_data['data'][0]
                    if len(latest) >= 3:  # timestamp, used, free
                        memory_used_bytes = latest[1] if isinstance(latest[1], (int, float)) else 0
                        memory_free_bytes = latest[2] if isinstance(latest[2], (int, float)) else 0

                        memory_used_gb = round(memory_used_bytes / (1024**3), 1)
                        memory_free_gb = round(memory_free_bytes / (1024**3), 1)
                        memory_total_gb = memory_used_gb + memory_free_gb
                        memory_percentage = round((memory_used_gb / memory_total_gb) * 100, 1) if memory_total_gb > 0 else 0

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
                            'description': 'Memory Utilization (invalid data)'
                        }
                else:
                    metrics['memory'] = {
                        'total_gb': cluster_ram_gb,
                        'used_gb': 0.0,
                        'percentage': 0.0,
                        'description': 'Memory Utilization (no data)'
                    }
            else:
                metrics['memory'] = {
                    'total_gb': cluster_ram_gb,
                    'used_gb': 0.0,
                    'percentage': 0.0,
                    'description': 'Memory Utilization (unavailable)'
                }
        except Exception as e:
            logger.warning(f"Failed to fetch memory metrics: {e}")
            metrics['memory'] = {
                'total_gb': cluster_ram_gb,
                'used_gb': 0.0,
                'percentage': 0.0,
                'description': 'Memory Utilization (error)'
            }

        # Get network metrics
        try:
            net_response = requests.get(
                f"{netdata_url}/api/v1/data",
                params={'chart': 'system.net', 'points': 1},
                timeout=timeout
            )

            if net_response.status_code == 200:
                net_data = net_response.json()
                if 'data' in net_data and len(net_data['data']) > 0:
                    latest = net_data['data'][0]
                    if len(latest) >= 3:  # timestamp, received, sent
                        received_bps = latest[1] if isinstance(latest[1], (int, float)) else 0
                        sent_bps = latest[2] if isinstance(latest[2], (int, float)) else 0

                        received_mbps = round(received_bps / (1024**2), 1)
                        sent_mbps = round(sent_bps / (1024**2), 1)

                        metrics['network'] = {
                            'bandwidth_mbps': round(received_mbps + sent_mbps, 1),
                            'received_mbps': received_mbps,
                            'sent_mbps': sent_mbps,
                            'description': 'Network Bandwidth (Mbps)'
                        }
                    else:
                        metrics['network'] = None
                else:
                    metrics['network'] = None
            else:
                metrics['network'] = None
        except Exception as e:
            logger.warning(f"Failed to fetch network metrics: {e}")
            metrics['network'] = None

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
