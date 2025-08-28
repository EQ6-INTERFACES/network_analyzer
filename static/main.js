// ============== static/main.js ==============
// Sistema de tema oscuro
const themeToggle = document.getElementById('theme-toggle');
const htmlElement = document.documentElement;

// Cargar tema guardado
const savedTheme = localStorage.getItem('theme') || 'light';
htmlElement.setAttribute('data-theme', savedTheme);
updateThemeIcon();

// Toggle tema
if (themeToggle) {
    themeToggle.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        
        htmlElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon();
    });
}

function updateThemeIcon() {
    const theme = htmlElement.getAttribute('data-theme');
    if (themeToggle) {
        themeToggle.innerHTML = theme === 'light' ? '🌙' : '☀️';
    }
}

// Sistema de consola
let consoleOutput = [];
let isAnalyzing = false;

function addToConsole(message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const consoleElement = document.getElementById('console-output');
    
    if (consoleElement) {
        const line = document.createElement('span');
        line.className = `console-line ${type}`;
        line.textContent = `[${timestamp}] ${message}\n`;
        consoleElement.appendChild(line);
        
        // Guardar en array para exportar
        consoleOutput.push({
            timestamp: timestamp,
            message: message,
            type: type
        });
        
        // Auto-scroll
        consoleElement.scrollTop = consoleElement.scrollHeight;
    }
}

// Limpiar consola
function clearConsole() {
    const consoleElement = document.getElementById('console-output');
    if (consoleElement) {
        consoleElement.innerHTML = '';
        consoleOutput = [];
        addToConsole('Console cleared', 'info');
    }
}

// Guardar consola como TXT
function saveConsoleToFile() {
    if (consoleOutput.length === 0) {
        alert('La consola está vacía');
        return;
    }
    
    let content = "NETWORK ANALYZER - CONSOLE OUTPUT\n";
    content += "=" + "=".repeat(49) + "\n";
    content += `Fecha: ${new Date().toLocaleString()}\n`;
    content += "=" + "=".repeat(49) + "\n\n";
    
    consoleOutput.forEach(entry => {
        content += `[${entry.timestamp}] [${entry.type.toUpperCase()}] ${entry.message}\n`;
    });
    
    // Crear blob y descargar
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `console_output_${new Date().getTime()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    addToConsole('Console output saved to file', 'success');
}

// Iniciar análisis
async function startAnalysis() {
    const clientSelect = document.getElementById('client-select');
    const profileSelect = document.getElementById('profile-select');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const analyzeBtn = document.getElementById('analyze-btn');
    
    if (!clientSelect || !profileSelect) {
        addToConsole('Error: Elementos de formulario no encontrados', 'error');
        return;
    }
    
    const clientId = clientSelect.value;
    const profile = profileSelect.value;
    
    if (!clientId) {
        alert('Por favor selecciona un cliente');
        return;
    }
    
    isAnalyzing = true;
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Analizando...';
    
    addToConsole(`Iniciando análisis de ${clientId} con perfil ${profile}`, 'info');
    
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                client_id: clientId,
                profile: profile
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addToConsole('Análisis iniciado correctamente', 'success');
            // Iniciar polling para obtener progreso
            pollProgress(data.task_id);
        } else {
            addToConsole(`Error: ${data.error}`, 'error');
            isAnalyzing = false;
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Iniciar Análisis';
        }
    } catch (error) {
        addToConsole(`Error de conexión: ${error}`, 'error');
        isAnalyzing = false;
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Iniciar Análisis';
    }
}

// Polling de progreso
async function pollProgress(taskId) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/progress/${taskId}`);
            const data = await response.json();
            
            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.textContent = `${data.progress}%`;
            }
            
            if (progressText) {
                progressText.textContent = data.message;
            }
            
            addToConsole(data.message, data.progress === 100 ? 'success' : 'info');
            
            if (data.progress >= 100) {
                clearInterval(interval);
                isAnalyzing = false;
                document.getElementById('analyze-btn').disabled = false;
                document.getElementById('analyze-btn').textContent = 'Iniciar Análisis';
                
                // Cargar resultados
                loadResults(taskId);
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }, 2000);
}

// Cargar resultados
async function loadResults(taskId) {
    try {
        const response = await fetch(`/api/results/${taskId}`);
        const data = await response.json();
        
        if (data.success) {
            displayResults(data.results);
        } else {
            addToConsole('Error cargando resultados', 'error');
        }
    } catch (error) {
        addToConsole(`Error: ${error}`, 'error');
    }
}

// Mostrar resultados
function displayResults(results) {
    const resultsDiv = document.getElementById('results-container');
    if (!resultsDiv) return;
    
    let html = `
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">📊 Resultados del Análisis</h3>
                <div>
                    <button class="btn btn-primary" onclick="viewDetailedReport('${results.client_id}')">
                        📄 Ver Reporte
                    </button>
                    <button class="btn btn-success" onclick="exportPDF('${results.client_id}')">
                        📥 Exportar PDF
                    </button>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="stat-card">
                    <div class="stat-value">${results.summary.overall_score}/100</div>
                    <div class="stat-label">Score General</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${results.summary.total_devices}</div>
                    <div class="stat-label">Dispositivos Totales</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${results.kpis.availability_rate}%</div>
                    <div class="stat-label">Disponibilidad</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${results.kpis.critical_issues}</div>
                    <div class="stat-label">Issues Críticos</div>
                </div>
            </div>
            
            ${renderAlerts(results.alerts)}
            ${renderDeviceTable(results.devices)}
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

// Renderizar alertas
function renderAlerts(alerts) {
    if (!alerts || alerts.length === 0) {
        return '<div class="alert alert-success">✅ No hay alertas críticas</div>';
    }
    
    let html = '<div class="alerts-container">';
    alerts.forEach(alert => {
        const alertClass = alert.type === 'critical' ? 'danger' : alert.type;
        html += `
            <div class="alert alert-${alertClass}">
                <strong>${alert.message}</strong>
                ${alert.details ? `<br><small>${JSON.stringify(alert.details)}</small>` : ''}
            </div>
        `;
    });
    html += '</div>';
    return html;
}

// Renderizar tabla de dispositivos
function renderDeviceTable(devices) {
    let html = `
        <div class="card">
            <div class="card-header">
                <h4 class="card-title">Estado de Dispositivos</h4>
            </div>
            <table class="table">
                <thead>
                    <tr>
                        <th>Dispositivo</th>
                        <th>IP</th>
                        <th>Tipo</th>
                        <th>Estado</th>
                        <th>Score</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    for (const [id, device] of Object.entries(devices)) {
        const badgeClass = device.severity === 'ok' ? 'success' : 
                          device.severity === 'warning' ? 'warning' : 'danger';
        
        html += `
            <tr>
                <td>${device.nombre}</td>
                <td>${device.ip}</td>
                <td>${device.tipo}</td>
                <td><span class="badge badge-${badgeClass}">${device.severity}</span></td>
                <td>${device.score}/100</td>
                <td>
                    <button class="btn btn-secondary" onclick="viewDeviceDetails('${id}')">
                        Ver Detalles
                    </button>
                </td>
            </tr>
        `;
    }
    
    html += '</tbody></table></div>';
    return html;
}

// Ver detalles del dispositivo
function viewDeviceDetails(deviceId) {
    // Implementar modal o navegación para ver detalles
    console.log('Ver detalles de:', deviceId);
}

// Ver reporte detallado
function viewDetailedReport(clientId) {
    window.location.href = `/report/${clientId}`;
}

// Exportar a PDF
async function exportPDF(clientId) {
    try {
        addToConsole('Generando PDF...', 'info');
        
        const response = await fetch(`/api/export/pdf/${clientId}`, {
            method: 'GET',
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${clientId}_${new Date().getTime()}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            addToConsole('PDF generado correctamente', 'success');
        } else {
            addToConsole('Error generando PDF', 'error');
        }
    } catch (error) {
        addToConsole(`Error: ${error}`, 'error');
    }
}

// WebSocket para actualizaciones en tiempo real
let socket = null;

function connectWebSocket() {
    socket = new WebSocket(`ws://${window.location.host}/ws`);
    
    socket.onopen = () => {
        console.log('WebSocket conectado');
    };
    
    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'progress') {
            updateProgress(data.progress, data.message);
        } else if (data.type === 'console') {
            addToConsole(data.message, data.level || 'info');
        }
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    socket.onclose = () => {
        console.log('WebSocket desconectado');
        // Reconectar después de 5 segundos
        setTimeout(connectWebSocket, 5000);
    };
}

// Actualizar progreso
function updateProgress(progress, message) {
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${progress}%`;
    }
    
    if (progressText) {
        progressText.textContent = message;
    }
}

// Inicialización cuando carga la página
document.addEventListener('DOMContentLoaded', () => {
    // Conectar WebSocket
    // connectWebSocket(); // Comentado por ahora, activar cuando implementes WebSocket
    
    // Inicializar consola
    addToConsole('Sistema iniciado', 'success');
    addToConsole('Esperando comandos...', 'info');
    
    // Event listeners para botones
    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', startAnalysis);
    }
    
    const clearBtn = document.getElementById('clear-console-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearConsole);
    }
    
    const saveBtn = document.getElementById('save-console-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveConsoleToFile);
    }
});