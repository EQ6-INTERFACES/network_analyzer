import json
from pathlib import Path
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ReportGenerator:
    def __init__(self):
        self.reports_dir = Path('data/reports')
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def save_report(self, results):
        """Guarda un reporte en JSON"""
        timestamp = int(time.time())
        report_id = f"{results['client_id']}_{timestamp}"
        report_path = self.reports_dir / f"{report_id}.json"
        
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        return report_id
    
    def get_reports_list(self):
        """Obtiene lista de todos los reportes"""
        reports = []
        for report_file in self.reports_dir.glob('*.json'):
            try:
                with open(report_file) as f:
                    data = json.load(f)
                    reports.append({
                        'id': report_file.stem,
                        'client': data.get('client_name'),
                        'timestamp': data.get('timestamp'),
                        'devices': len(data.get('devices', []))
                    })
            except:
                continue
        
        return sorted(reports, key=lambda x: x['timestamp'], reverse=True)
    
    def get_report(self, report_id):
        """Obtiene un reporte específico"""
        report_path = self.reports_dir / f"{report_id}.json"
        if report_path.exists():
            with open(report_path) as f:
                return json.load(f)
        return None
    
    def generate_pdf(self, report_id):
        """Genera PDF de un reporte"""
        report = self.get_report(report_id)
        if not report:
            return None
        
        pdf_path = self.reports_dir / f"{report_id}.pdf"
        
        # Crear PDF
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Título
        title = Paragraph(f"Reporte de Análisis - {report['client_name']}", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Información general
        info = Paragraph(f"Fecha: {report['timestamp']}<br/>Dispositivos: {len(report['devices'])}", 
                        styles['Normal'])
        story.append(info)
        story.append(Spacer(1, 12))
        
        # Tabla de dispositivos
        data = [['Dispositivo', 'IP', 'Estado']]
        for device in report['devices']:
            data.append([
                device.get('device'),
                device.get('ip'),
                device.get('status')
            ])
        
        table = Table(data)
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
        
        # Generar PDF
        doc.build(story)
        
        return str(pdf_path)