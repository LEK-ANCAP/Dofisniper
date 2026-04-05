import os
import zipfile
import paramiko
import time

def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if 'venv' in dirs: dirs.remove('venv')
        if '.venv' in dirs: dirs.remove('.venv')
        if '__pycache__' in dirs: dirs.remove('__pycache__')
        if '.git' in dirs: dirs.remove('.git')
        if 'browser_data' in dirs: dirs.remove('browser_data')
        
        for file in files:
            if file.endswith('.zip') or file.endswith('.db') or file.endswith('.log') or file.endswith('.pyc'):
                continue
            ap = os.path.join(root, file)
            ziph.write(ap, os.path.relpath(ap, path))

print("Empaquetando proyecto...")
zipf = zipfile.ZipFile('deploy.zip', 'w', zipfile.ZIP_DEFLATED)
zipdir('.', zipf)
zipf.close()

host = '146.190.143.31'
user = 'root'
pwd = 'y@Siqu33stoyfeo'

print(f"Conectando a {host}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=pwd)

sftp = ssh.open_sftp()
print("Subiendo zip...")
sftp.put('deploy.zip', '/root/deploy.zip')

print("Ejecutando despliegue en VPS...")
commands = [
    "apt-get update && apt-get install -y docker.io docker-compose unzip",
    "mkdir -p /root/dofimall-sniper",
    "unzip -o /root/deploy.zip -d /root/dofimall-sniper",
    "cd /root/dofimall-sniper && docker-compose build",
    "cd /root/dofimall-sniper && docker-compose up -d"
]

for cmd in commands:
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    
    # Wait for completion and print output
    exit_status = stdout.channel.recv_exit_status()
    print(stdout.read().decode('utf-8'))
    err = stderr.read().decode('utf-8')
    if err:
        print(f"Stderr: {err}")

sftp.close()
ssh.close()
print("¡Despliegue completado!")
