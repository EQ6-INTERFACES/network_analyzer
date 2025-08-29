from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_socketio import SocketIO, emit
from pathlib import Path
import json
import time
from datetime import datetime
from network_core import NetworkCore
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

network = NetworkCore()

# Callback para enviar logs al frontend
def emit_log(message):
    socketio.emit('console_log', {'message': message})

network.set_log_callback(emit_log)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/reports')
def reports():
    """Vista de reportes"""
    reports_list = []
    reports_dir = Path('data/reports')
    
    if reports_dir.exists():
        for report_file in reports_dir.glob('*.json'):
            try:
                with open(report_file) as f:
                    data = json.load(f)
                    reports_list.append({
                        'id': report_file.stem,
                        'client': data.get('client_name', 'Unknown'),
                        'timestamp': data.get('timestamp', ''),
                        'devices': len(data.get('devices', []))
                    })
            except:
                continue
    
    return render_template('reports.html', reports=reports_list)

@app.route('/api/config')
def get_config():
    return jsonify(network.config)

@app.route('/api/analyze/<client_id>', methods=['POST'])
def analyze_client(client_id):
    data = request.json
    
    # IMPORTANTE: Usar el modo correcto
    analysis_mode = data.get('mode', 'checklist')
    
    if analysis_mode == 'custom':
        # Usar comandos personalizados
        commands = data.get('commands', [])
        checks = {'custom': commands}
    else:
        # Usar checklist
        selected_checks = data.get('checks', ['health'])
        checks = {}
        for check_name in selected_checks:
            if check_name in network.config['checks']:
                checks[check_name] = network.config['checks'][check_name]
    
    # Solo dispositivos seleccionados
    selected_devices = data.get('devices', [])
    
    client_info = network.config['clientes'].get(client_id)
    if not client_info:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    
    results = {
        'client_id': client_id,
        'client_name': client_info['nombre'],
        'timestamp': datetime.now().isoformat(),
        'devices': []
    }
    
    # Solo analizar dispositivos seleccionados
    for device in client_info['devices']:
        if device['id'] in selected_devices:
            socketio.emit('device_progress', {
                'device': device['hostname'],
                'status': 'connecting'
            })
            
            result = network.analyze_device(device, client_info, checks)
            results['devices'].append(result)
            
            socketio.emit('device_progress', {
                'device': device['hostname'],
                'status': result['status']
            })
    
    # Guardar reporte
    timestamp = int(time.time())
    report_id = f"{client_id}_{timestamp}"
    report_path = Path('data/reports') / f"{report_id}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    return jsonify({
        'success': True,
        'results': results,
        'report_id': report_id
    })

@app.route('/api/report/pdf/<report_id>')
def export_pdf(report_id):
    """Generar PDF real"""
    report_path = Path('data/reports') / f"{report_id}.json"
    
    if not report_path.exists():
        return jsonify({'error': 'Reporte no encontrado'}), 404
    
    with open(report_path) as f:
        data = json.load(f)
    
    # Crear PDF en memoria
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Título
    title = Paragraph(f"Reporte de Análisis - {data['client_name']}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Fecha
    info = Paragraph(f"Fecha: {data['timestamp']}", styles['Normal'])
    story.append(info)
    story.append(Spacer(1, 12))
    
    # Tabla de dispositivos
    table_data = [['Dispositivo', 'IP', 'Estado']]
    
    for device in data.get('devices', []):
        table_data.append([
            device.get('device', 'N/A'),
            device.get('ip', 'N/A'),
            device.get('status', 'N/A')
        ])
    
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 24))
    
    # Agregar outputs de comandos
    for device in data.get('devices', []):
        story.append(Paragraph(f"<b>{device.get('device', 'N/A')}</b>", styles['Heading2']))
        
        for check_name, check_data in device.get('checks', {}).items():
            story.append(Paragraph(f"Check: {check_name}", styles['Heading3']))
            
            for cmd, output in check_data.get('outputs', {}).items():
                story.append(Paragraph(f"<b>Comando:</b> {cmd}", styles['Normal']))
                
                # Limitar output para PDF
                output_text = output[:500] if output else "Sin salida"
                if len(output) > 500:
                    output_text += "... (output truncado)"
                
                output_para = Paragraph(f"<pre>{output_text}</pre>", styles['Code'])
                story.append(output_para)
                story.append(Spacer(1, 6))
    
    # Generar PDF
    doc.build(story)
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'report_{report_id}.pdf',
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    Path('data/reports').mkdir(parents=True, exist_ok=True)
    
    print("="*50)
    print("Network Analyzer v2.0")
    print("="*50)
    print("Servidor en: http://localhost:5000")
    print("="*50)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)