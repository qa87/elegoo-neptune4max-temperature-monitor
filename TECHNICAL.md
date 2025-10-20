# Техническая документация - Elegoo Neptune 4 Max Temperature Monitor

## 🏗️ Архитектура приложения

### Структура классов

```python
class PrinterMonitorGUI:
    """
    Основной класс приложения с графическим интерфейсом
    Наследует от tkinter.Tk для создания GUI
    """
```

### Основные компоненты:

1. **GUI Manager** - управление интерфейсом
2. **Network Client** - HTTP запросы к принтеру
3. **Configuration Manager** - сохранение/загрузка настроек
4. **Logger** - система логирования
5. **Thread Manager** - управление потоками

## 🔌 API интеграция

### Moonraker API Endpoints

Программа использует следующие API endpoints:

#### 1. Проверка соединения
```http
GET http://[IP]/printer/objects/query?toolhead&heater_bed
```

#### 2. Мониторинг температуры
```http
GET http://[IP]/printer/objects/query?heater_bed
```

### Структура ответа API

```json
{
  "result": {
    "status": {
      "heater_bed": {
        "temperature": 25.3,    // Текущая температура
        "target": 60.0,         // Целевая температура
        "power": 0.0            // Мощность нагревателя (0-1)
      },
      "toolhead": {
        "position": [0, 0, 0, 0],
        "status": "Ready"
      }
    }
  }
}
```

## 🧵 Многопоточность

### Архитектура потоков:

```
Main Thread (GUI)
├── UI Updates
├── Event Handling
└── Thread Management

Worker Thread 1 (Connection Test)
├── HTTP Request
├── Response Processing
└── UI Callback

Worker Thread 2 (Temperature Monitor)
├── Periodic HTTP Requests
├── Temperature Processing
├── Alert Triggering
└── UI Updates
```

### Безопасность потоков:

Все обновления UI выполняются через `self.root.after()`:

```python
# Правильно - безопасное обновление из другого потока
self.root.after(0, lambda: self.update_status("Новый статус"))

# Неправильно - прямое обновление из другого потока
self.status_label.config(text="Новый статус")  # Может вызвать ошибки
```

## 📊 Обработка данных

### Парсинг температуры:

```python
def parse_temperature_data(self, response_data):
    """
    Извлекает данные о температуре из ответа API
    
    Args:
        response_data (dict): Ответ от Moonraker API
        
    Returns:
        tuple: (current_temp, target_temp) или (None, None) при ошибке
    """
    try:
        bed_status = response_data['result']['status']['heater_bed']
        current_temp = bed_status.get('temperature', 0)
        target_temp = bed_status.get('target', 0)
        return current_temp, target_temp
    except (KeyError, TypeError):
        return None, None
```

### Валидация данных:

```python
def validate_temperature(self, temp):
    """
    Проверяет корректность значения температуры
    
    Args:
        temp (float): Значение температуры
        
    Returns:
        bool: True если температура корректна
    """
    return isinstance(temp, (int, float)) and 0 <= temp <= 200
```

## 🔧 Конфигурация

### Структура конфигурационного файла:

```json
{
  "ip": "192.168.1.100",           // IP адрес принтера
  "target_temp": "60",             // Целевая температура
  "check_interval": 5,             // Интервал проверки (секунды)
  "log_interval": 30,              // Интервал логирования (секунды)
  "timeout": 10                    // Тайм-аут HTTP запросов
}
```

### Загрузка конфигурации:

```python
def load_config(self):
    """
    Загружает настройки из JSON файла
    Создает файл с настройками по умолчанию если не существует
    """
    config_path = os.path.join(os.path.dirname(__file__), 'printer_config.json')
    
    default_config = {
        'ip': '192.168.1.100',
        'target_temp': '60',
        'check_interval': 5,
        'log_interval': 30,
        'timeout': 10
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {**default_config, **config}
        else:
            self.save_config(default_config)
            return default_config
    except Exception as e:
        self.log_error(f"Ошибка загрузки конфигурации: {e}")
        return default_config
```

## 📝 Система логирования

### Уровни логирования:

1. **INFO** - общая информация
2. **WARNING** - предупреждения
3. **ERROR** - ошибки
4. **DEBUG** - отладочная информация

### Формат лога:

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] Сообщение
```

### Примеры логов:

```
[2024-01-15 12:34:56] [INFO] Запуск программы
[2024-01-15 12:34:57] [INFO] Тестирование соединения с принтером
[2024-01-15 12:34:58] [INFO] Соединение установлено успешно
[2024-01-15 12:35:00] [INFO] Начат мониторинг температуры
[2024-01-15 12:35:30] [DEBUG] Температура стола: 35.2°C (целевая: 60.0°C)
[2024-01-15 12:36:00] [WARNING] Высокая температура: 85.0°C
[2024-01-15 12:36:30] [ERROR] Ошибка соединения с принтером
```

## 🚨 Система уведомлений

### Типы уведомлений:

1. **Системные уведомления Windows** - нативные toast уведомления
2. **Звуковые сигналы** - системные звуки
3. **Логирование** - запись в файл/консоль

### Реализация уведомлений:

```python
def show_system_notification(self, current_temp, target_temp):
    """
    Показывает системное уведомление Windows
    
    Args:
        current_temp (float): Текущая температура
        target_temp (float): Целевая температура
    """
    title = "🎯 Цель достигнута!"
    message = f"Температура стола достигла {current_temp:.1f}°C\nЦелевая температура: {target_temp}°C"
    
    if TOAST_AVAILABLE:
        try:
            # Используем win10toast для системных уведомлений
            toaster = ToastNotifier()
            toaster.show_toast(
                title=title,
                msg=message,
                duration=10,  # Показывать 10 секунд
                icon_path=None,  # Можно добавить иконку
                threaded=True
            )
        except Exception as e:
            # Fallback к обычному окну
            self.show_fallback_notification(current_temp, target_temp)
    else:
        # Fallback к обычному окну
        self.show_fallback_notification(current_temp, target_temp)
```

### Зависимости для уведомлений:

```python
# Автоматический импорт с fallback
try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False
```

## 🌐 Сетевое взаимодействие

### HTTP клиент:

```python
class PrinterHTTPClient:
    """
    HTTP клиент для взаимодействия с принтером
    """
    
    def __init__(self, base_url, timeout=10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
    
    def get_temperature(self):
        """
        Получает текущую температуру стола
        
        Returns:
            dict: Данные о температуре или None при ошибке
        """
        try:
            url = f"{self.base_url}/printer/objects/query?heater_bed"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.log_error(f"HTTP ошибка: {e}")
            return None
```

### Обработка ошибок сети:

```python
def handle_network_error(self, error):
    """
    Обрабатывает ошибки сетевого взаимодействия
    
    Args:
        error (Exception): Ошибка сети
    """
    if isinstance(error, requests.exceptions.ConnectionError):
        return "Ошибка соединения с принтером"
    elif isinstance(error, requests.exceptions.Timeout):
        return "Тайм-аут соединения"
    elif isinstance(error, requests.exceptions.HTTPError):
        return f"HTTP ошибка: {error.response.status_code}"
    else:
        return f"Неизвестная ошибка сети: {error}"
```

## 🔒 Безопасность

### Валидация входных данных:

```python
def validate_ip_address(self, ip):
    """
    Проверяет корректность IP адреса
    
    Args:
        ip (str): IP адрес для проверки
        
    Returns:
        bool: True если IP корректный
    """
    import re
    pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    return re.match(pattern, ip) is not None

def validate_temperature(self, temp_str):
    """
    Проверяет корректность значения температуры
    
    Args:
        temp_str (str): Строка с температурой
        
    Returns:
        float or None: Температура или None при ошибке
    """
    try:
        temp = float(temp_str)
        if 0 <= temp <= 200:
            return temp
        return None
    except ValueError:
        return None
```

### Защита от атак:

1. **Валидация всех входных данных**
2. **Ограничение тайм-аутов**
3. **Проверка формата ответов API**
4. **Безопасное логирование**

## 🧪 Тестирование

### Модульные тесты:

```python
import unittest
from unittest.mock import patch, Mock

class TestPrinterMonitor(unittest.TestCase):
    
    def setUp(self):
        self.app = PrinterMonitorGUI(tk.Tk())
    
    def test_validate_ip_address(self):
        """Тест валидации IP адресов"""
        self.assertTrue(self.app.validate_ip_address("192.168.1.100"))
        self.assertFalse(self.app.validate_ip_address("invalid_ip"))
        self.assertFalse(self.app.validate_ip_address("256.256.256.256"))
    
    def test_validate_temperature(self):
        """Тест валидации температуры"""
        self.assertEqual(self.app.validate_temperature("60"), 60.0)
        self.assertIsNone(self.app.validate_temperature("invalid"))
        self.assertIsNone(self.app.validate_temperature("300"))
    
    @patch('requests.get')
    def test_connection_test(self, mock_get):
        """Тест проверки соединения"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': {
                'status': {
                    'heater_bed': {
                        'temperature': 25.0,
                        'target': 60.0
                    }
                }
            }
        }
        mock_get.return_value = mock_response
        
        # Тест логики соединения
        self.app.test_connection()
        # Проверка результатов...
```

### Интеграционные тесты:

```python
def test_full_monitoring_cycle():
    """
    Тест полного цикла мониторинга
    """
    # Создание mock принтера
    # Запуск мониторинга
    # Проверка уведомлений
    # Остановка мониторинга
    pass
```

## 📈 Производительность

### Оптимизации:

1. **Кэширование HTTP сессий**
2. **Минимизация обновлений UI**
3. **Эффективное логирование**
4. **Оптимальные интервалы проверки**

### Мониторинг производительности:

```python
import time
import psutil

class PerformanceMonitor:
    """
    Мониторинг производительности приложения
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()
    
    def get_stats(self):
        """
        Получает статистику производительности
        
        Returns:
            dict: Статистика производительности
        """
        return {
            'uptime': time.time() - self.start_time,
            'memory_usage': self.process.memory_info().rss / 1024 / 1024,  # MB
            'cpu_percent': self.process.cpu_percent(),
            'thread_count': self.process.num_threads()
        }
```

## 🔄 Обновления и версионирование

### Схема версионирования:

```
MAJOR.MINOR.PATCH
```

- **MAJOR** - кардинальные изменения API
- **MINOR** - новые функции
- **PATCH** - исправления ошибок

### История версий:

#### v1.0.0
- Первоначальный релиз
- Базовый мониторинг температуры
- GUI интерфейс
- Звуковые уведомления

#### v1.1.0 (планируется)
- Поддержка множественных принтеров
- Экспорт логов
- Настраиваемые звуковые сигналы
- Темная тема интерфейса

## 🐛 Отладка

### Включение отладочного режима:

```python
import logging

# Настройка логирования для отладки
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
```

### Типичные проблемы и решения:

1. **Проблема:** Программа не может подключиться к принтеру
   **Решение:** Проверить IP адрес, сетевое соединение, настройки брандмауэра

2. **Проблема:** Высокое потребление CPU
   **Решение:** Увеличить интервал проверки температуры

3. **Проблема:** Проблемы с кодировкой
   **Решение:** Использовать UTF-8 для всех текстовых файлов

## 📚 Дополнительные ресурсы

### Полезные ссылки:

- [Klipper Documentation](https://www.klipper3d.org/)
- [Moonraker API](https://moonraker.readthedocs.io/)
- [Elegoo Neptune 4 Max Manual](https://www.elegoo.com/)

### Сообщество:

- [Klipper Discord](https://discord.gg/klipper)
- [Reddit r/klippers](https://www.reddit.com/r/klippers/)
- [Elegoo Community](https://community.elegoo.com/)
