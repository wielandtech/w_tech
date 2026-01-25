// Fetch and display Netdata metrics
function fetchMetrics() {
    fetch('/api/metrics/')
        .then(response => response.json())
        .then(data => {
            console.log('Metrics response:', data);  // Debug logging
            
            if (data.status === 'unavailable' || data.status === 'error') {
                let errorMsg = 'Metrics temporarily unavailable';
                if (data.error) {
                    errorMsg += ': ' + data.error;
                }
                if (data.errors && data.errors.length > 0) {
                    errorMsg += ' (' + data.errors.join(', ') + ')';
                }
                document.getElementById('metrics-content').innerHTML = 
                    '<div class="metrics-error">' + errorMsg + '</div>';
                return;
            }
            
            let html = '<div class="metrics-grid">';

            // Row 1: Utilization metrics
            // CPU Utilization Card
            if (data.cpu !== null) {
                const cpuClass = data.cpu.percentage > 80 ? 'critical' : (data.cpu.percentage > 60 ? 'warning' : '');
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.cpu.description}</div>
                        <div class="metric-value">${data.cpu.percentage}%</div>
                        <div class="metric-detail">${data.cpu.total_cores} cores total</div>
                        <div class="metric-bar">
                            <div class="metric-bar-fill ${cpuClass}" style="width: ${Math.min(data.cpu.percentage, 100)}%"></div>
                        </div>
                    </div>
                `;
            }

            // Memory Utilization Card
            if (data.memory !== null) {
                const memoryClass = data.memory.percentage > 85 ? 'critical' : (data.memory.percentage > 70 ? 'warning' : '');
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.memory.description}</div>
                        <div class="metric-value">${data.memory.percentage}%</div>
                        <div class="metric-detail">${data.memory.used_gb} / ${data.memory.total_gb} GB</div>
                        <div class="metric-bar">
                            <div class="metric-bar-fill ${memoryClass}" style="width: ${Math.min(data.memory.percentage, 100)}%"></div>
                        </div>
                    </div>
                `;
            }

            // Disk I/O Card
            if (data.disk_io !== null) {
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.disk_io.description}</div>
                        <div class="metric-value">${data.disk_io.total_mbps} MB/s</div>
                        <div class="metric-detail">↑ ${data.disk_io.write_mbps} · ↓ ${data.disk_io.read_mbps} MB/s</div>
                    </div>
                `;
            }

            // Network Utilization Card
            if (data.network !== null) {
                let networkValue, networkDetail;
                if (data.network.bandwidth_mbps !== undefined) {
                    networkValue = `${data.network.bandwidth_mbps} Mbps`;
                    networkDetail = `↑ ${data.network.sent_mbps} · ↓ ${data.network.received_mbps} Mbps`;
                } else {
                    networkValue = 'N/A';
                    networkDetail = 'metrics unavailable';
                }

                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.network.description}</div>
                        <div class="metric-value">${networkValue}</div>
                        <div class="metric-detail">${networkDetail}</div>
                    </div>
                `;
            }

            // Row 2: Other metrics (CPU Temp under CPU Util)
            // CPU Temperature Card
            if (data.temperature !== null) {
                const tempClass = data.temperature.max_celsius > 80 ? 'critical' : (data.temperature.max_celsius > 65 ? 'warning' : '');
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.temperature.description}</div>
                        <div class="metric-value ${tempClass}">${data.temperature.avg_celsius}°C</div>
                        <div class="metric-detail">peak ${data.temperature.max_celsius}°C</div>
                    </div>
                `;
            }

            // Pods Running Card
            if (data.pods !== null) {
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.pods.description}</div>
                        <div class="metric-value">${data.pods.count}</div>
                        <div class="metric-detail">in cluster</div>
                    </div>
                `;
            }

            // Deployments Card
            if (data.deployments !== null) {
                const deployClass = data.deployments.healthy < data.deployments.total ? 'warning' : '';
                const deployDetail = data.deployments.healthy === data.deployments.total ? 'all healthy' : `${data.deployments.total - data.deployments.healthy} unhealthy`;
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.deployments.description}</div>
                        <div class="metric-value ${deployClass}">${data.deployments.healthy}/${data.deployments.total}</div>
                        <div class="metric-detail">${deployDetail}</div>
                    </div>
                `;
            }

            // Cluster Uptime Card
            if (data.uptime !== null) {
                html += `
                    <div class="metric-card">
                        <div class="metric-label">${data.uptime.description}</div>
                        <div class="metric-value">${data.uptime.formatted}</div>
                        <div class="metric-detail">since last reboot</div>
                    </div>
                `;
            }

            html += '</div>';
            
            // Add status indicator
            let statusParts = [];
            if (data.nodes_count) {
                const reachable = data.reachable_nodes || 0;
                statusParts.push(reachable + '/' + data.nodes_count + ' nodes');
            }
            if (data.errors && data.errors.length > 0) {
                statusParts.push(data.errors.length + ' warnings');
            }
            if (statusParts.length > 0) {
                html += '<div class="metrics-status">' + statusParts.join(' • ') + '</div>';
            }
            
            document.getElementById('metrics-content').innerHTML = html;
        })
        .catch(error => {
            console.error('Error fetching metrics:', error);
            document.getElementById('metrics-content').innerHTML = 
                '<div class="metrics-error">Unable to load metrics</div>';
        });
}

// Initial fetch
fetchMetrics();

// Refresh every second
setInterval(fetchMetrics, 1000);
