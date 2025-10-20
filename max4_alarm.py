import tkinter as tk
from tkinter import messagebox
import requests
import threading
import time
import json
import os
from datetime import datetime

# Импорт для системных уведомлений Windows
try:
    import win32api
    import win32con
    import win32gui
    WINDOWS_NOTIFICATIONS_AVAILABLE = True
except ImportError:
    WINDOWS_NOTIFICATIONS_AVAILABLE = False

class PrinterMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Elegoo Neptune 4 Max Temperature Monitor")
        self.root.geometry("400x300")
        
        # Загрузка настроек
        self.config_file = "printer_config.json"
        
        # Элементы интерфейса
        tk.Label(root, text="IP принтера:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ip_entry = tk.Entry(root, width=20)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(root, text="Целевая температура:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.temp_entry = tk.Entry(root, width=20)
        self.temp_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Кнопка тестирования соединения
        self.test_btn = tk.Button(root, text="Тест соединения", command=self.test_connection)
        self.test_btn.grid(row=2, column=0, padx=5, pady=5)
        
        self.start_btn = tk.Button(root, text="Старт мониторинг", command=self.start_monitoring)
        self.start_btn.grid(row=2, column=1, padx=5, pady=5)
        
        self.stop_btn = tk.Button(root, text="Стоп", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.grid(row=2, column=2, padx=5, pady=5)
        
        # Статус
        self.status_label = tk.Label(root, text="Статус: Остановлен", font=("Arial", 10, "bold"))
        self.status_label.grid(row=3, column=0, columnspan=3, pady=10)
        
        # Температура
        self.temp_label = tk.Label(root, text="Текущая температура: --°C", font=("Arial", 12))
        self.temp_label.grid(row=4, column=0, columnspan=3, pady=5)
        
        # Лог
        tk.Label(root, text="Лог:").grid(row=5, column=0, sticky="nw", padx=5, pady=5)
        self.log_text = tk.Text(root, height=8, width=50)
        scrollbar = tk.Scrollbar(root, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=6, column=0, columnspan=2, padx=5, pady=5)
        scrollbar.grid(row=6, column=2, sticky="ns", pady=5)
        
        self.monitoring = False
        self.monitor_thread = None
        
        # Загружаем настройки после создания всех элементов интерфейса
        self.load_config()
    
    def load_config(self):
        """Загрузка настроек из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.ip_entry.insert(0, config.get('ip', '192.168.1.100'))
                    self.temp_entry.insert(0, config.get('target_temp', '60'))
            else:
                # Значения по умолчанию
                self.ip_entry.insert(0, '192.168.1.100')
                self.temp_entry.insert(0, '60')
        except Exception as e:
            # Если есть log_text, используем его, иначе просто print
            if hasattr(self, 'log_text'):
                self.log_message(f"Ошибка загрузки настроек: {e}")
            else:
                print(f"Ошибка загрузки настроек: {e}")
            self.ip_entry.insert(0, '192.168.1.100')
            self.temp_entry.insert(0, '60')
    
    def save_config(self):
        """Сохранение настроек в файл"""
        try:
            config = {
                'ip': self.ip_entry.get(),
                'target_temp': self.temp_entry.get()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"Ошибка сохранения настроек: {e}")
    
    def log_message(self, message):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        # Безопасный вывод в консоль с обработкой кодировки
        try:
            print(log_entry.strip())
        except UnicodeEncodeError:
            # Убираем эмодзи для консоли
            safe_message = message.encode('ascii', 'ignore').decode('ascii')
            safe_log_entry = f"[{timestamp}] {safe_message}\n"
            print(safe_log_entry.strip())
    
    def test_connection(self):
        """Тестирование соединения с принтером"""
        printer_ip = self.ip_entry.get().strip()
        if not printer_ip:
            messagebox.showerror("Ошибка", "Введите IP адрес принтера")
            return
        
        self.log_message("Тестирование соединения...")
        
        def test_thread():
            try:
                # Тестируем соединение с Moonraker API
                url = f"http://{printer_ip}/printer/objects/query?toolhead&heater_bed"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and 'status' in data['result']:
                        self.root.after(0, lambda: self.log_message("OK Соединение успешно!"))
                        self.root.after(0, lambda: self.update_status("Статус: Соединение установлено"))
                        
                        # Показываем текущую температуру
                        try:
                            bed_status = data['result']['status']['heater_bed']
                            current_temp = bed_status.get('temperature', 0)
                            target_temp = bed_status.get('target', 0)
                            self.root.after(0, lambda: self.log_message(f"Текущая температура стола: {current_temp}°C (целевая: {target_temp}°C)"))
                        except:
                            pass
                    else:
                        self.root.after(0, lambda: self.log_message("ERROR Неверный ответ от принтера"))
                else:
                    self.root.after(0, lambda: self.log_message(f"ERROR Ошибка HTTP: {response.status_code}"))
                    
            except requests.exceptions.ConnectTimeout:
                self.root.after(0, lambda: self.log_message("ERROR Тайм-аут соединения"))
            except requests.exceptions.ConnectionError:
                self.root.after(0, lambda: self.log_message("ERROR Ошибка соединения"))
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"ERROR Ошибка: {e}"))
        
        thread = threading.Thread(target=test_thread)
        thread.daemon = True
        thread.start()
    
    def update_status(self, status):
        """Безопасное обновление статуса из другого потока"""
        self.status_label.config(text=status)
        
    def start_monitoring(self):
        printer_ip = self.ip_entry.get().strip()
        if not printer_ip:
            messagebox.showerror("Ошибка", "Введите IP адрес принтера")
            return
        
        try:
            target_temp = float(self.temp_entry.get())
            if target_temp <= 0:
                messagebox.showerror("Ошибка", "Температура должна быть больше 0")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректную температуру")
            return
        
        self.monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.test_btn.config(state=tk.DISABLED)
        self.update_status("Статус: Мониторинг...")
        self.save_config()  # Сохраняем настройки
        
        self.log_message(f"Начат мониторинг. Целевая температура: {target_temp}°C")
        
        # Запуск в отдельном потоке
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.test_btn.config(state=tk.NORMAL)
        self.update_status("Статус: Остановлен")
        self.log_message("Мониторинг остановлен")
    
    def monitor_loop(self):
        printer_ip = self.ip_entry.get().strip()
        target_temp = float(self.temp_entry.get())
        
        while self.monitoring:
            try:
                # Используем правильный API endpoint для Klipper/Moonraker
                url = f"http://{printer_ip}/printer/objects/query?heater_bed"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'result' in data and 'status' in data['result']:
                        bed_status = data['result']['status']['heater_bed']
                        current_temp = bed_status.get('temperature', 0)
                        target_bed_temp = bed_status.get('target', 0)
                        
                        # Обновляем интерфейс безопасно
                        self.root.after(0, lambda: self.temp_label.config(
                            text=f"Текущая температура: {current_temp:.1f}°C"
                        ))
                        
                        # Логируем каждые 30 секунд
                        if int(time.time()) % 30 == 0:
                            self.root.after(0, lambda: self.log_message(
                                f"Температура стола: {current_temp:.1f}°C (целевая: {target_bed_temp}°C)"
                            ))
                        
                        # Проверяем условие
                        if current_temp >= target_temp:
                            self.root.after(0, lambda: self.show_alert(current_temp, target_temp))
                            self.root.after(0, self.stop_monitoring)
                            break
                    else:
                        self.root.after(0, lambda: self.log_message("ERROR Неверный формат ответа от принтера"))
                
                else:
                    self.root.after(0, lambda: self.log_message(f"ERROR HTTP ошибка: {response.status_code}"))
                    
            except requests.exceptions.ConnectTimeout:
                self.root.after(0, lambda: self.log_message("ERROR Тайм-аут соединения"))
            except requests.exceptions.ConnectionError:
                self.root.after(0, lambda: self.log_message("ERROR Ошибка соединения с принтером"))
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"ERROR Ошибка мониторинга: {e}"))
            
            time.sleep(5)  # Проверяем каждые 5 секунд
    
    def show_alert(self, current_temp, target_temp):
        """Показ уведомления о достижении температуры"""
        self.log_message(f"ЦЕЛЬ ДОСТИГНУТА! Температура: {current_temp:.1f}°C (цель: {target_temp}°C)")
        
        # Показываем системное уведомление Windows
        self.show_system_notification(current_temp, target_temp)
        
        # Звуковой сигнал
        try:
            import winsound
            # Играем мелодию из 3 звуков
            winsound.Beep(1000, 500)
            time.sleep(0.1)
            winsound.Beep(1200, 500)
            time.sleep(0.1)
            winsound.Beep(1400, 1000)
        except ImportError:
            # Если winsound недоступен (например, на Linux/Mac)
            print("\a" * 3)  # Звуковой сигнал терминала
    
    def show_system_notification(self, current_temp, target_temp):
        """Показывает системное уведомление Windows"""
        title = "🎯 Цель достигнута!"
        message = f"Температура стола достигла {current_temp:.1f}°C\nЦелевая температура: {target_temp}°C"
        
        if WINDOWS_NOTIFICATIONS_AVAILABLE:
            try:
                # Используем MessageBox для системного уведомления
                win32api.MessageBox(
                    0,  # hwnd
                    message,
                    title,
                    win32con.MB_OK | win32con.MB_ICONINFORMATION | win32con.MB_TOPMOST
                )
                self.log_message("Системное уведомление отправлено")
            except Exception as e:
                self.log_message(f"Ошибка системного уведомления: {e}")
                # Fallback к обычному окну
                self.show_fallback_notification(current_temp, target_temp)
        else:
            self.log_message("Windows API недоступен, используем fallback")
            # Fallback к обычному окну
            self.show_fallback_notification(current_temp, target_temp)
    
    def show_fallback_notification(self, current_temp, target_temp):
        """Fallback уведомление через обычное окно"""
        messagebox.showinfo("ЦЕЛЬ ДОСТИГНУТА!", 
                           f"Температура стола достигла {current_temp:.1f}°C!\n"
                           f"Целевая температура: {target_temp}°C")

# Запуск приложения
if __name__ == "__main__":
    root = tk.Tk()
    app = PrinterMonitorGUI(root)
    
    # Обработка закрытия приложения
    def on_closing():
        if app.monitoring:
            app.stop_monitoring()
        app.save_config()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()