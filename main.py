import paramiko
import time
import os
import calendar
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from netmiko import ConnectHandler
from email import encoders
from cryptography.fernet import Fernet
from credentials import encrypted_username, encrypted_password
from poa_olt_devices import devices

class OLTBackup:
    def __init__(self):
        # Configurações do servidor de e-mail
        self.smtp_server = ''  # Inserir servidor SMTP
        self.smtp_port = 587  # Inserir porta SMTP (ex.: 587)
        self.smtp_user = ''  # Inserir usuário SMTP
        self.smtp_password = ''  # Inserir senha SMTP
        self.email_sender = ''  # Inserir e-mail do remetente
        self.email_recipient = ''  # Inserir e-mail do destinatário

        # Carregar chave Fernet para descriptografar credenciais
        self.fernet_key = self.load_fernet_key("")  # Inserir caminho da chave Fernet
        self.username = self.decrypt_credentials(encrypted_username)
        self.password = self.decrypt_credentials(encrypted_password)

        # Caminho base para salvar os arquivos de backup
        self.base_path = r'INSERT_BASE_PATH'  # Inserir caminho base para salvar arquivos de backup

        # Comandos de backup para diferentes fabricantes
        self.commands = {
            'Zte': ['terminal length 0', 'show running-config'],
            'Huawei': ['enable', 'scroll', 'display current-configuration'],
            'Datacom': ['enable', 'scroll', 'display current-configuration'],
        }

        # Nomes dos meses para organizar os diretórios de backup
        self.month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }

    # Carregar chave Fernet para descriptografar as credenciais
    def load_fernet_key(self, path):
        with open(path, "r") as key_file:
            return key_file.read().encode()

    # Descriptografar credenciais usando a chave Fernet
    def decrypt_credentials(self, encrypted_credentials):
        fernet = Fernet(self.fernet_key)
        return fernet.decrypt(encrypted_credentials).decode()

    # Executar conexão SSH e coletar configuração do equipamento
    def execute_ssh(self, ip, device_name, device_group):
        # Definir as configurações do dispositivo para conexão SSH
        device = {
            'device_type': 'autodetect',
            'host': ip,
            'username': self.username,
            'password': self.password,
            'secret': self.password,
            'blocking_timeout': 30
        }
        
        # Obter comandos específicos do grupo do dispositivo
        commands = self.commands.get(device_group, [])
        output = ""
        uptime_exceeded = False

        try:
            # Estabelecer conexão SSH e executar comandos
            with ConnectHandler(**device) as connection:
                connection.enable()
                for command in commands:
                    print(f"Executing command: {command}")
                    command_result = connection.send_command(command, expect_string=fr"{device_name}#", delay_factor=12, read_timeout=120)
                    output += command_result
                    connection.send_command_timing(" ")
        except Exception as e:
            # Capturar e registrar qualquer erro durante a conexão SSH
            print(f"Error connecting to IP {ip}: {str(e)}")
        return output, uptime_exceeded

    # Salvar a saída dos comandos em um arquivo
    def save_output(self, output, filename, device_group, city):
        # Obter o nome do mês atual e definir o caminho completo do diretório para salvar o backup
        month_number = time.localtime().tm_mon
        month_name = self.month_names[month_number]
        current_date = time.strftime('%d-%m-%Y')
        full_path = os.path.join(self.base_path, month_name, city, current_date, device_group)

        # Criar o diretório se não existir e salvar o arquivo de backup
        os.makedirs(full_path, exist_ok=True)
        with open(os.path.join(full_path, filename), 'w', encoding='utf-8') as file:
            file.write(output)

    # Gerar um relatório em formato de texto com dispositivos bem-sucedidos e com falha
    def generate_txt_report(self, successful_devices, failed_devices):
        report_name = "backup_report.txt"
        with open(report_name, "w") as file:
            file.write("Successfully executed hosts:\n")
            for device in successful_devices:
                file.write(f"{device}\n")
            if failed_devices:
                file.write("\nHosts with errors:\n")
                for device in failed_devices:
                    file.write(f"{device}\n")
        return report_name

    # Enviar e-mail com o relatório de backup
    def send_email(self, subject, body, html_content=None, attachment_name=None):
        message = MIMEMultipart("alternative")
        message['From'] = self.email_sender
        message['To'] = self.email_recipient
        message['Subject'] = subject

        # Anexar o corpo do e-mail em formato texto e HTML
        message.attach(MIMEText(body, 'plain'))

        if html_content:
            message.attach(MIMEText(html_content, 'html'))

        # Anexar arquivo de relatório, se existir
        if attachment_name:
            with open(attachment_name, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
                message.attach(part)

        try:
            # Conectar ao servidor SMTP e enviar o e-mail
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.email_sender, self.email_recipient, message.as_string())
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Error sending email: {str(e)}")

    # Executar o backup de todos os dispositivos
    def execute_backup(self):
        start_time = time.time()
        successful_devices = []
        failed_devices = []
        
        # Percorrer todos os dispositivos e executar o backup
        for ip, device_info in devices.items():
            device_name = device_info['device_name']
            device_group = device_info['device_group']
            city = device_info['city']
            elif output:
                successful_devices.append(device_name)
                timestamp = time.strftime('%d%m%Y')
                filename = f'{device_name}_{timestamp}.txt'
                self.save_output(output, filename, device_group, city)
            else:
                failed_devices.append(device_name)

        # Gerar relatório em formato de texto
        report_name = self.generate_txt_report(successful_devices, failed_devices)

        # Calcular o tempo total de execução do backup
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_minutes, elapsed_seconds = divmod(elapsed_time, 60)
        
        # Criar e enviar e-mail de conclusão do backup
        date = datetime.now().strftime("%Y-%m-%d")
        completion_time = time.strftime('%H:%M:%S')
        execution_time = f"{elapsed_minutes:.0f} minutes and {elapsed_seconds:.0f} seconds"
        failures = len(failed_devices)

        subject = "Backup of Devices (OLT) Completed"
        body = f"Backup dos equipamentos ZTE executados com sucesso. Tempo de execução: {elapsed_minutes:.0f} minutos e {elapsed_seconds:.0f} segundos.\n\n"
        html_table = self.generate_html_report(successful_devices)
        self.send_email(subject, body, html_content=html_table, attachment_name=report_name)
        print(f"Backup conluído para {len(successful_devices)} equipamentos. Erros identificados em {len(failed_devices)}.")

    # Gerar relatório em formato HTML com dispositivos bem-sucedidos
    def generate_html_report(self, successful_devices):
        table_rows = ""
        for group, commands in self.commands.items():
            # Contar quantos dispositivos em cada grupo foram bem-sucedidos
            success_count = sum([1 for device_name in successful_devices if any(info["device_name"] == device_name and info["device_group"] == group for info in devices.values())])
            table_rows += f"""
            <tr>
                <td style="text-align: center;">{group}</td>
                <td style="text-align: center;">{success_count}</td>
            </tr>
            """
        # Criar tabela HTML com informações sobre os dispositivos bem-sucedidos
        html_table = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        table {{
            font-family: Arial, sans-serif;
            border-collapse: collapse;
            width: 100%;
        }}
        td, th {{
            border: 1px solid #dddddd;
            text-align: left;
            padding: 8px;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        </style>
        </head>
        <body>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr>
                    <th style="text-align: center;">Device</th>
                    <th style="text-align: center;">Executed</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        </body>
        </html>
        """
        return html_table

if __name__ == "__main__":
    # Inicializar a classe OLTBackup e executar o backup
    backup = OLTBackup()
    backup.execute_backup()