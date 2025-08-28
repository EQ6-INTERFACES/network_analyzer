from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from pathlib import Path
import json
from network_core import NetworkCore

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

network = NetworkCore()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/api/config')
def get_config():
    return jsonify(network.config)

@app.route('/api/analyze/<client_id>', methods=['POST'])
def analyze_client(client_id):
    data = request.json
    selected_checks = data.get('checks', ['health', 'interfaces'])
    
    client_info = network.config['clientes'].get(client_id)
    if not client_info:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    # Preparar checks
    checks = {}
    for check_name in selected_checks:
        if check_name in network.config['checks']:
            checks[check_name] = network.config['checks'][check_name]
    
    # Analizar cada dispositivo
    results = []
    for device in client_info['devices']:
        result = network.analyze_device(device, client_info, checks)
        results.append(result)
        
        # Emitir progreso
        socketio.emit('device_progress', {
            'device': device['hostname'],
            'status': result['status']
        }, broadcast=True)
    
    # Guardar resultados
    report_path = Path('data/reports') / f"{client_id}_{int(time.time())}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    return jsonify({
        'success': True,
        'results': results,
        'report_path': str(report_path)
    })

@app.route('/api/test/<client_id>')
def test_connection(client_id):
    """Prueba rápida de conexión"""
    client_info = network.config['clientes'].get(client_id)
    if not client_info or not client_info['devices']:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    device = client_info['devices'][0]
    conn = network.connect_device(device, client_info)
    
    if conn:
        output = network.send_command('show version | include uptime')
        network.disconnect()
        return jsonify({
            'success': True,
            'device': device['hostname'],
            'output': output
        })
    
    return jsonify({'success': False, 'error': 'No se pudo conectar'})

if __name__ == '__main__':
    # Crear directorios necesarios
    Path('data/reports').mkdir(parents=True, exist_ok=True)
    
    print("="*50)
    print("Network Analyzer - Versión Simplificada")
    print("="*50)
    print("Servidor en: http://localhost:5000")
    print("="*50)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)