// ============== static/main.js COMPLETO ==============

// Sistema de tema oscuro CORREGIDO
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Actualizar icono
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = newTheme === 'light' ? 'bi bi-moon-stars' : 'bi bi-sun';
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

// Exportar consola a TXT CORREGIDO
function exportConsole() {
    const consoleElement = document.getElementById('console-output');
    if (!consoleElement) {
        alert('No hay consola disponible');
        return;
    }
    
    // Obtener todo el texto de la consola
    let content = "NETWORK ANALYZER - CONSOLE OUTPUT\n";
    content += "=" + "=".repeat(49) + "\n";
    content += `Fecha: ${new Date().toLocaleString()}\n`;
    content += "=" + "=".repeat(49) + "\n\n";
    
    // Agregar cada línea del output
    consoleOutput.forEach(entry => {
        content += `[${entry.timestamp}] [${entry.type.toUpperCase()}] ${entry.message}\n`;
    });
    
    // Si no hay contenido en el array, usar el texto directo del elemento
    if (consoleOutput.length === 0) {
        content += consoleElement.innerText || consoleElement.textContent;
    }
    
    // Crear timestamp para el nombre del archivo
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `console_output_${timestamp}.txt`;
    
    // Crear blob y descargar
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    addToConsole('Console output exported to ' + filename, 'success');
}

// Iniciar análisis
async function startAnalysis() {
    const clientSelect = document.getElementById('client-select');
    const profileSelect = document.getElementById('profile-select');
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
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analizando...';
    }
    
    addToConsole(`Iniciando análisis de ${clientId} con perfil ${profile}`, 'info');
    
    try {
        const response = await fetch(`/api/analyze/${clientId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                checks: ['health', 'interfaces', 'vlans']
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            addToConsole('Análisis completado correctamente', 'success');
            displayResults(data.results);
        } else {
            addToConsole(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        addToConsole(`Error de conexión: ${error}`, 'error');
    } finally {
        isAnalyzing = false;
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Iniciar Análisis';
        }
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
                    <button class="btn btn-success" onclick="exportPDF('${results.report_id}')">
                        📥 Exportar PDF
                    </button>
                </div>
            </div>
            
            <div class="dashboard-grid">
                <div class="stat-card">
                    <div class="stat-value">${results.devices ? results.devices.length : 0}</div>
                    <div class="stat-label">Dispositivos Analizados</div>
                </div>
            </div>
            
            ${renderDeviceTable(results.devices || [])}
        </div>
    `;
    
    resultsDiv.innerHTML = html;
}

// Renderizar tabla de dispositivos
function renderDeviceTable(devices) {
    if (!devices || devices.length === 0) {
        return '<p>No hay dispositivos para mostrar</p>';
    }
    
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
                        <th>Estado</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    devices.forEach(device => {
        const statusClass = device.status === 'completed' ? 'success' : 
                          device.status === 'unreachable' ? 'danger' : 'warning';
        
        html += `
            <tr>
                <td>${device.device}</td>
                <td>${device.ip}</td>
                <td><span class="badge badge-${statusClass}">${device.status}</span></td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="viewDeviceDetails('${device.device}')">
                        Ver Detalles
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    return html;
}

// Ver detalles del dispositivo
function viewDeviceDetails(deviceId) {
    console.log('Ver detalles de:', deviceId);
    // Aquí puedes implementar un modal o expandir la información
}

// Ver reporte detallado
function viewDetailedReport(clientId) {
    window.location.href = `/reports`;
}

// Exportar a PDF
async function exportPDF(reportId) {
    if (!reportId) {
        addToConsole('No hay reporte para exportar', 'error');
        return;
    }
    
    try {
        addToConsole('Generando PDF...', 'info');
        window.location.href = `/api/report/pdf/${reportId}`;
        addToConsole('PDF generado correctamente', 'success');
    } catch (error) {
        addToConsole(`Error generando PDF: ${error}`, 'error');
    }
}

// WebSocket para actualizaciones en tiempo real
let socket = null;

function connectWebSocket() {
    // Solo conectar si Socket.IO está disponible
    if (typeof io !== 'undefined') {
        socket = io();
        
        socket.on('connect', () => {
            console.log('WebSocket conectado');
            addToConsole('Conectado al servidor', 'success');
        });
        
        socket.on('device_progress', (data) => {
            addToConsole(`${data.device}: ${data.status}`, 'info');
            updateDeviceStatus(data.device, data.status);
        });
        
        socket.on('analysis_progress', (data) => {
            updateProgress(data.progress, data.message);
        });
        
        socket.on('disconnect', () => {
            console.log('WebSocket desconectado');
            addToConsole('Desconectado del servidor', 'warning');
        });
    }
}

// Actualizar estado del dispositivo
function updateDeviceStatus(device, status) {
    const statusElement = document.querySelector(`[data-device="${device}"]`);
    if (statusElement) {
        statusElement.textContent = status;
        statusElement.className = `badge badge-${getStatusClass(status)}`;
    }
}

// Obtener clase CSS para estado
function getStatusClass(status) {
    const statusMap = {
        'connecting': 'info',
        'completed': 'success',
        'unreachable': 'danger',
        'error': 'danger',
        'analyzing': 'warning'
    };
    return statusMap[status] || 'secondary';
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
    // Cargar tema guardado
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = savedTheme === 'light' ? 'bi bi-moon-stars' : 'bi bi-sun';
    }
    
    // Conectar WebSocket
    connectWebSocket();
    
    // Inicializar consola
    addToConsole('Sistema iniciado', 'success');
    addToConsole('Network Analyzer v2.0 Ready', 'info');
    
    // Event listeners para botones
    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', startAnalysis);
    }
    
    const clearBtn = document.getElementById('clear-console-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearConsole);
    }
    
    const exportBtn = document.getElementById('export-console-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportConsole);
    }
    
    // Agregar botón de exportar si no existe
    const consoleContainer = document.querySelector('.console-output');
    if (consoleContainer && !document.getElementById('export-console-btn')) {
        const exportButton = document.createElement('button');
        exportButton.id = 'export-console-btn';
        exportButton.className = 'btn btn-sm btn-success mt-2';
        exportButton.innerHTML = '<i class="bi bi-download"></i> Exportar TXT';
        exportButton.onclick = exportConsole;
        consoleContainer.parentElement.appendChild(exportButton);
    }
});

// Funciones auxiliares para compatibilidad
function showToast(message, type = 'info') {
    // Si existe función Bootstrap toast, usarla
    if (typeof bootstrap !== 'undefined' && document.getElementById('liveToast')) {
        const toast = document.getElementById('liveToast');
        const toastBody = document.getElementById('toastMessage');
        toastBody.textContent = message;
        
        toast.classList.remove('bg-success', 'bg-danger', 'bg-warning');
        if (type === 'success') toast.classList.add('bg-success', 'text-white');
        else if (type === 'error') toast.classList.add('bg-danger', 'text-white');
        else if (type === 'warning') toast.classList.add('bg-warning');
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    } else {
        // Fallback a console
        addToConsole(message, type);
    }
}