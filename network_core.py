import paramiko
import socket
import time
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from netmiko import ConnectHandler
from datetime import datetime

class NetworkCore:
    def __init__(self):
        self.config = self.load_config()
        self.connection = None
        self.jump_client = None
        self.jump_channel = None
        self.log_callback = None  # Para enviar logs al frontend
        
        # Crear directorio de logs
        self.log_dir = Path('data/logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de log para la sesión actual
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = self.log_dir / f"session_{timestamp}.txt"
        self.full_log = []
    
    def set_log_callback(self, callback):
        """Establece callback para enviar logs al frontend"""
        self.log_callback = callback
    
    def log(self, message, level="INFO", show_in_gui=True):
        """Registra todo en archivo y memoria"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Imprimir en consola
        print(log_entry)
        
        # Enviar al frontend si hay callback y está habilitado
        if self.log_callback and show_in_gui:
            # Filtrar solo salidas importantes para el GUI
            if any(x in message for x in ['>', '#', 'Password:', 'BANNER', 'EJECUTANDO', '✓', 'ERROR']):
                self.log_callback(message)
        
        # Guardar en memoria
        self.full_log.append(log_entry)
        
        # Escribir en archivo
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
    
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
        self.log(f"INICIANDO CONEXIÓN A {device_info['hostname']} ({device_info['ip']})")
        
        creds = self.get_credentials(client_info.get('credential', 'default'))
        
        if not creds:
            self.log(f"ERROR: No se encontraron credenciales", "ERROR")
            return None
            
        # Si hay jump host configurado (bridgenet)
        if client_info.get('jump_host'):
            jump_info = self.config['jump_hosts'][client_info['jump_host']]
            jump_creds = self.get_credentials(jump_info['credential'])
            
            self.log(f"Usando Jump Host: {jump_info['host']}")
            
            return self._connect_via_jump_manual(
                device_info, creds,
                jump_info, jump_creds
            )
        
        # Conexión directa
        self.log(f"Conectando directamente a {device_info['ip']}")
        return self._connect_direct(device_info, creds)
    
    def _connect_via_jump_manual(self, device_info, device_creds, jump_info, jump_creds):
        """Conexión manual a través de Bridgenet sin Netmiko"""
        try:
            self.log("="*60)
            self.log("CONEXIÓN VÍA BRIDGENET")
            self.log("="*60)
            
            # 1. Conectar a Bridgenet
            self.log(f"Paso 1: Conectando a Bridgenet {jump_info['host']}")
            self.jump_client = paramiko.SSHClient()
            self.jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.jump_client.connect(
                hostname=jump_info['host'],
                username=jump_creds['username'],
                password=jump_creds['password'],
                port=jump_info.get('port', 22),
                timeout=30
            )
            
            self.log("✓ Conectado a Bridgenet")
            
            # 2. Abrir shell interactivo
            self.jump_channel = self.jump_client.invoke_shell()
            time.sleep(2)
            
            # Leer banner de Bridgenet
            output = self._read_channel(self.jump_channel)
            self.log("BANNER BRIDGENET:", show_in_gui=False)
            self.log("-"*40, show_in_gui=False)
            self.log(output)
            self.log("-"*40, show_in_gui=False)
            
            # 3. Conectar al dispositivo final
            ssh_cmd = f"ssh {device_creds['username']}@{device_info['ip']}"
            self.log(f"Ejecutando: {ssh_cmd}")
            self.jump_channel.send(ssh_cmd + '\n')
            time.sleep(3)
            
            # Leer respuesta
            output = self._read_channel(self.jump_channel)
            self.log(f"Respuesta SSH: {output}", show_in_gui=False)
            
            # 4. Enviar contraseña si la pide
            if 'password' in output.lower():
                self.log("Enviando contraseña...")
                self.jump_channel.send(device_creds['password'] + '\n')
                time.sleep(3)
                output = self._read_channel(self.jump_channel)
                self.log("BANNER DEL DISPOSITIVO:")
                self.log(output)
            
            # 5. Verificar que estamos en el dispositivo
            self.jump_channel.send('\n')
            time.sleep(1)
            prompt = self._read_channel(self.jump_channel)
            self.log(f"PROMPT DETECTADO: {prompt}")
            
            # 6. Intentar entrar a modo enable si es necesario
            if '>' in prompt:
                self.log("Entrando a modo enable...")
                self.jump_channel.send('enable\n')
                time.sleep(2)
                output = self._read_channel(self.jump_channel)
                
                if 'password' in output.lower():
                    self.log("Enviando enable password...")
                    self.jump_channel.send(device_creds.get('enable_password', device_creds['password']) + '\n')
                    time.sleep(2)
                    output = self._read_channel(self.jump_channel)
                    
                    # Verificar si entró a enable
                    self.jump_channel.send('\n')
                    time.sleep(1)
                    new_prompt = self._read_channel(self.jump_channel)
                    if '#' in new_prompt:
                        self.log("✓ Modo enable activado")
                    else:
                        self.log("Continuando en modo usuario")
            
            # Usar el canal manual como conexión
            self.connection = self.jump_channel
            self.log(f"✓ Conexión establecida con {device_info['hostname']}")
            return self.connection
            
        except Exception as e:
            self.log(f"ERROR en conexión: {str(e)}", "ERROR")
            if self.jump_client:
                self.jump_client.close()
            return None
    
    def _read_channel(self, channel, timeout=1):
        """Lee datos del canal SSH"""
        channel.settimeout(timeout)
        output = ""
        try:
            while True:
                if channel.recv_ready():
                    data = channel.recv(4096).decode('utf-8', errors='ignore')
                    output += data
                else:
                    time.sleep(0.1)
                    if not channel.recv_ready():
                        break
        except socket.timeout:
            pass
        return output
    
    def send_command(self, command):
        """Envía comando al dispositivo"""
        if self.connection and isinstance(self.connection, paramiko.Channel):
            self.log(f"EJECUTANDO COMANDO: {command}")
            
            try:
                # Limpiar buffer
                self._read_channel(self.connection, 0.5)
                
                # Enviar comando
                self.connection.send(command + '\n')
                time.sleep(2)
                
                # Leer respuesta completa
                output = ""
                max_attempts = 10
                for _ in range(max_attempts):
                    chunk = self._read_channel(self.connection, 1)
                    if chunk:
                        output += chunk
                    else:
                        break
                    
                    # Si encontramos el prompt o --More--, procesamos
                    if '>' in chunk or '#' in chunk:
                        break
                    elif '--More--' in chunk:
                        self.connection.send(' ')  # Enviar espacio para continuar
                        time.sleep(0.5)
                
                # Limpiar output
                lines = output.split('\n')
                # Remover el comando echo y el prompt
                if lines and command in lines[0]:
                    lines = lines[1:]
                if lines and ('>' in lines[-1] or '#' in lines[-1]):
                    lines = lines[:-1]
                
                clean_output = '\n'.join(lines)
                
                # Mostrar en GUI solo primeras líneas importantes
                preview = clean_output[:500] if clean_output else "Sin salida"
                self.log(f"RESPUESTA: {preview}")
                
                return clean_output
                
            except Exception as e:
                self.log(f"ERROR ejecutando comando: {str(e)}", "ERROR")
                return ""
        
        return ""
    
    def disconnect(self):
        """Cierra conexiones"""
        self.log("Cerrando conexiones...")
        
        if self.jump_channel:
            try:
                self.jump_channel.send('exit\n')
                time.sleep(1)
                self.jump_channel.send('exit\n')  # Salir del dispositivo y de Bridgenet
                time.sleep(1)
            except:
                pass
            self.jump_channel.close()
            
        if self.jump_client:
            self.jump_client.close()
            
        self.log("✓ Conexiones cerradas")
    
    def analyze_device(self, device_info, client_info, checks):
        """Analiza un dispositivo ejecutando los checks"""
        self.log("="*60)
        self.log(f"ANÁLISIS DE {device_info['hostname']}")
        self.log("="*60)
        
        results = {
            'device': device_info['hostname'],
            'ip': device_info['ip'],
            'status': 'analyzing',
            'checks': {},
            'log_file': str(self.log_file)
        }
        
        # Conectar
        conn = self.connect_device(device_info, client_info)
        if not conn:
            results['status'] = 'unreachable'
            self.log("Dispositivo inalcanzable", "ERROR")
            return results
        
        # Ejecutar checks o comandos
        for check_name, commands in checks.items():
            self.log(f"\nEJECUTANDO: {check_name}")
            check_result = {'outputs': {}}
            
            # Si es custom, los comandos vienen directamente
            if check_name == 'custom':
                for cmd in commands:
                    output = self.send_command(cmd)
                    check_result['outputs'][cmd] = output
            else:
                # Es un checklist normal
                for cmd in commands:
                    output = self.send_command(cmd)
                    check_result['outputs'][cmd] = output
                
            results['checks'][check_name] = check_result
        
        results['status'] = 'completed'
        self.log(f"✓ Análisis completado para {device_info['hostname']}")
        
        self.disconnect()
        
        # Guardar log completo en el resultado
        results['full_log'] = self.full_log
        
        return results
    
    def get_session_log(self):
        """Retorna el path del log de la sesión"""
        return str(self.log_file)