import paramiko
import socket
import time
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from netmiko import ConnectHandler

class NetworkCore:
    def __init__(self):
        self.config = self.load_config()
        self.connection = None
        self.jump_client = None
        
    def load_config(self):
        config_path = Path('config/config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def get_credentials(self, credential_name):
        """Obtiene credenciales sin encriptación"""
        return self.config['credentials'].get(credential_name, {})
    
    def connect_device(self, device_info, client_info):
        """Conecta a un dispositivo con o sin jump host"""
        creds = self.get_credentials(client_info.get('credential', 'default'))
        
        if not creds:
            return None
            
        # Si hay jump host configurado
        if client_info.get('jump_host'):
            jump_info = self.config['jump_hosts'][client_info['jump_host']]
            jump_creds = self.get_credentials(jump_info['credential'])
            
            return self._connect_via_jump(
                device_info, creds,
                jump_info, jump_creds
            )
        
        # Conexión directa
        return self._connect_direct(device_info, creds)
    
    def _connect_direct(self, device_info, creds):
        """Conexión directa sin jump host"""
        try:
            device = {
                'device_type': device_info['type'],
                'host': device_info['ip'],
                'username': creds['username'],
                'password': creds['password'],
                'port': 22,
                'timeout': 30
            }
            
            self.connection = ConnectHandler(**device)
            return self.connection
            
        except Exception as e:
            print(f"Error conectando: {e}")
            return None
    
    def _connect_via_jump(self, device_info, device_creds, jump_info, jump_creds):
        """Conexión a través de jump host"""
        try:
            # Conectar al jump host
            self.jump_client = paramiko.SSHClient()
            self.jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.jump_client.connect(
                hostname=jump_info['host'],
                username=jump_creds['username'],
                password=jump_creds['password'],
                port=jump_info.get('port', 22)
            )
            
            # Crear túnel
            transport = self.jump_client.get_transport()
            dest_addr = (device_info['ip'], 22)
            local_addr = ('127.0.0.1', 0)
            channel = transport.open_channel("direct-tcpip", dest_addr, local_addr)
            
            # Conectar al dispositivo final
            device = {
                'device_type': device_info['type'],
                'host': device_info['ip'],
                'username': device_creds['username'],
                'password': device_creds['password'],
                'sock': channel,
                'timeout': 30
            }
            
            self.connection = ConnectHandler(**device)
            return self.connection
            
        except Exception as e:
            print(f"Error en jump connection: {e}")
            if self.jump_client:
                self.jump_client.close()
            return None
    
    def send_command(self, command):
        """Envía comando al dispositivo"""
        if self.connection:
            return self.connection.send_command(command)
        return ""
    
    def disconnect(self):
        """Cierra conexiones"""
        if self.connection:
            self.connection.disconnect()
        if self.jump_client:
            self.jump_client.close()
    
    def analyze_device(self, device_info, client_info, checks):
        """Analiza un dispositivo ejecutando los checks"""
        results = {
            'device': device_info['hostname'],
            'ip': device_info['ip'],
            'status': 'analyzing',
            'checks': {}
        }
        
        # Conectar
        conn = self.connect_device(device_info, client_info)
        if not conn:
            results['status'] = 'unreachable'
            return results
        
        # Ejecutar checks
        for check_name, commands in checks.items():
            check_result = {'outputs': {}}
            for cmd in commands:
                output = self.send_command(cmd)
                check_result['outputs'][cmd] = output
            results['checks'][check_name] = check_result
        
        # Parsear resultados básicos
        results['parsed'] = self.parse_outputs(results['checks'])
        results['status'] = 'completed'
        
        self.disconnect()
        return results
    
    def parse_outputs(self, checks):
        """Parseo básico de outputs"""
        parsed = {}
        
        # Buscar errores comunes
        for check_name, check_data in checks.items():
            for cmd, output in check_data['outputs'].items():
                if 'show interface' in cmd and 'errors' in cmd:
                    # Contar líneas con errores
                    error_count = len([l for l in output.split('\n') 
                                     if re.search(r'[1-9]\d*\s+(CRC|error)', l)])
                    parsed[f'{check_name}_errors'] = error_count
                
                elif 'show processes cpu' in cmd:
                    # Extraer CPU
                    match = re.search(r'CPU utilization.*?(\d+)%', output)
                    if match:
                        parsed['cpu_usage'] = int(match.group(1))
        
        return parsed