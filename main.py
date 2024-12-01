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
        self.smtp_server = ''  # Insert SMTP server
        self.smtp_port = 587  # Insert SMTP port here (e.g., 587)
        self.smtp_user = ''  # Insert SMTP user
        self.smtp_password = ''  # Insert SMTP password
        self.email_sender = ''  # Insert sender email
        self.email_recipient = ''  # Insert recipient email
        self.fernet_key = self.load_fernet_key("")  # Insert Fernet key path
        self.username = self.decrypt_credentials(encrypted_username)
        self.password = self.decrypt_credentials(encrypted_password)
        self.base_path = r'INSERT_BASE_PATH'  # Insert base path to save backup files
        self.commands = {
            'Zte': ['terminal length 0', 'show running-config'],
            'Huawei': ['enable', 'scroll', 'display current-configuration'],
            'Datacom': ['enable', 'scroll', 'display current-configuration'],
        }
        self.month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }

    def load_fernet_key(self, path):
        with open(path, "r") as key_file:
            return key_file.read().encode()

    def decrypt_credentials(self, encrypted_credentials):
        fernet = Fernet(self.fernet_key)
        return fernet.decrypt(encrypted_credentials).decode()

    def execute_ssh(self, ip, device_name, device_group):
        device = {
            'device_type': 'autodetect',
            'host': ip,
            'username': self.username,
            'password': self.password,
            'secret': self.password,
            'blocking_timeout': 30
        }
        
        commands = self.commands.get(device_group, [])
        output = ""
        uptime_exceeded = False

        try:
            with ConnectHandler(**device) as connection:
                connection.enable()
                for command in commands:
                    print(f"Executing command: {command}")
                    command_result = connection.send_command(command, expect_string=fr"{device_name}#", delay_factor=12, read_timeout=120)
                    output += command_result
                    connection.send_command_timing(" ")
        except Exception as e:
            print(f"Error connecting to IP {ip}: {str(e)}")
        return output, uptime_exceeded

    def save_output(self, output, filename, device_group, city):
        month_number = time.localtime().tm_mon
        month_name = self.month_names[month_number]
        current_date = time.strftime('%d-%m-%Y')
        full_path = os.path.join(self.base_path, month_name, city, current_date, device_group)

        os.makedirs(full_path, exist_ok=True)
        with open(os.path.join(full_path, filename), 'w', encoding='utf-8') as file:
            file.write(output)

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

    def send_email(self, subject, body, html_content=None, attachment_name=None):
        message = MIMEMultipart("alternative")
        message['From'] = self.email_sender
        message['To'] = self.email_recipient
        message['Subject'] = subject

        message.attach(MIMEText(body, 'plain'))

        if html_content:
            message.attach(MIMEText(html_content, 'html'))

        if attachment_name:
            with open(attachment_name, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={attachment_name}")
                message.attach(part)

        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.email_sender, self.email_recipient, message.as_string())
            server.quit()
            print("Email sent successfully.")
        except Exception as e:
            print(f"Error sending email: {str(e)}")

    def execute_backup(self):
        start_time = time.time()
        successful_devices = []
        failed_devices = []
        
        for ip, device_info in devices.items():
            device_name = device_info['device_name']
            device_group = device_info['device_group']
            city = device_info['city']
            output, uptime_exceeded = self.execute_ssh(ip, device_name, device_group)

            if uptime_exceeded:
                failed_devices.append(f"{device_name} (uptime over 300 days)")
            elif output:
                successful_devices.append(device_name)
                timestamp = time.strftime('%d%m%Y')
                filename = f'{device_name}_{timestamp}.txt'
                self.save_output(output, filename, device_group, city)
            else:
                failed_devices.append(device_name)

        report_name = self.generate_txt_report(successful_devices, failed_devices)

        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_minutes, elapsed_seconds = divmod(elapsed_time, 60)
        
        date = datetime.now().strftime("%Y-%m-%d")
        completion_time = time.strftime('%H:%M:%S')
        execution_time = f"{elapsed_minutes:.0f} minutes and {elapsed_seconds:.0f} seconds"
        failures = len(failed_devices)

        subject = "Backup of Devices (OLT) Completed"
        body = f"Backup of ZTE | Huawei OLTs in the Porto Alegre Cluster successfully completed. Execution time: {elapsed_minutes:.0f} minutes and {elapsed_seconds:.0f} seconds.\n\nDirectory path: \\\\201.21.192.139\\Files\\Save\\Backup\\OLT\n\n"
        html_table = self.generate_html_report(successful_devices)
        self.send_email(subject, body, html_content=html_table, attachment_name=report_name)
        print(f"Backup completed successfully for {len(successful_devices)} devices. Errors on {len(failed_devices)} devices.")

    def generate_html_report(self, successful_devices):
        table_rows = ""
        for group, commands in self.commands.items():
            success_count = sum([1 for device_name in successful_devices if any(info["device_name"] == device_name and info["device_group"] == group for info in devices.values())])
            table_rows += f"""
            <tr>
                <td style="text-align: center;">{group}</td>
                <td style="text-align: center;">{success_count}</td>
            </tr>
            """
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
    backup = OLTBackup()
    backup.execute_backup()
