#!/usr/bin/env python3
"""
Обновленный тестовый скрипт для проверки API Daichi Comfort Cloud.
Использует правильные endpoints, найденные через анализ браузера.

Использование:
1. Установите зависимости: pip install aiohttp
2. Замените USERNAME и PASSWORD на свои данные
3. Запустите: python test_api_updated.py
"""
import asyncio
import json
import logging
import os
from typing import Any

import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Настройки (можно задать через переменные окружения)
USERNAME = os.getenv("DAICHI_USERNAME", "your_email@example.com")
PASSWORD = os.getenv("DAICHI_PASSWORD", "your_password")
BASE_URL = os.getenv("DAICHI_API_URL", "https://web.daichicloud.ru/api/v4")
CLIENT_ID = os.getenv("DAICHI_CLIENT_ID", "sOJO7B6SqgaKudTfCzqLAy540cCuDzpI")

# Function IDs для управления (см. FUNCTION_IDS.md)
FUNCTION_ID_POWER = 350
FUNCTION_ID_TEMPERATURE = 351
FUNCTION_ID_COOL = 352
FUNCTION_ID_HEAT = 353
FUNCTION_ID_AUTO = 354
FUNCTION_ID_DRY = 355
FUNCTION_ID_FAN = 356
FUNCTION_ID_FAN_SPEED_AUTO = 357
FUNCTION_ID_FAN_SPEED = 358
FUNCTION_ID_VERTICAL_SWING = 359
FUNCTION_ID_HORIZONTAL_SWING = 360
FUNCTION_ID_3D_SWING = 361
FUNCTION_ID_ECO = 363
FUNCTION_ID_TURBO = 364
FUNCTION_ID_SLEEP = 366


async def test_authentication(session: aiohttp.ClientSession) -> tuple[bool, str | None]:
    """Тестирование двухэтапной аутентификации."""
    logger.info("=== Тестирование аутентификации ===")
    
    try:
        # Шаг 1: Проверка email
        logger.info("Шаг 1: Проверка email...")
        credentials_url = f"{BASE_URL}/user/credentials"
        credentials_payload = {"email": USERNAME}
        
        async with session.post(
            credentials_url,
            json=credentials_payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            logger.info(f"Credentials check status: {response.status}")
            if response.status not in (200, 201):
                text = await response.text()
                logger.error(f"Credentials check failed: {text}")
                return False, None
            
            logger.info("✓ Email проверен успешно")
        
        # Шаг 2: Получение токена
        logger.info("Шаг 2: Получение токена...")
        token_url = f"{BASE_URL}/token"
        token_payload = {
            "email": USERNAME,
            "password": PASSWORD,
            "clientId": CLIENT_ID,
        }
        
        async with session.post(
            token_url,
            json=token_payload,
            headers={"Content-Type": "application/json"}
        ) as response:
            logger.info(f"Token request status: {response.status}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status == 401:
                logger.error("Неверные учетные данные")
                return False, None
            
            if response.status != 200:
                text = await response.text()
                logger.error(f"Token request failed: {text}")
                return False, None
            
            # Парсинг ответа
            try:
                data = await response.json()
                logger.info(f"Token response data: {json.dumps(data, indent=2, ensure_ascii=False)}")
            except Exception as e:
                text = await response.text()
                logger.warning(f"Response is not JSON: {text}")
                logger.warning(f"Error: {e}")
                data = {}
            
            # Извлечение токена
            # Токен может быть в data.access_token или в корне
            token_data = data.get("data", {})
            token = (
                token_data.get("access_token")
                or token_data.get("token")
                or data.get("access_token")
                or data.get("token")
                or data.get("accessToken")
                or data.get("access")
            )
            
            # Проверка cookies
            if not token:
                cookies = response.cookies
                logger.info(f"Cookies: {dict(cookies)}")
                for cookie in cookies:
                    if "token" in cookie.key.lower() or "auth" in cookie.key.lower():
                        token = cookie.value
                        logger.info(f"Found token in cookie: {cookie.key}")
                        break
            
            if token:
                if token.startswith("Bearer "):
                    token = token[7:]
                logger.info(f"✓ Токен получен: {token[:20]}...")
                return True, token
            else:
                logger.warning("Токен не найден в ответе, но возможно используется session-based auth")
                logger.info("Продолжаем с session-based аутентификацией (cookies)")
                return True, None
    
    except Exception as e:
        logger.exception(f"Ошибка при аутентификации: {e}")
        return False, None


async def test_get_buildings(session: aiohttp.ClientSession, token: str | None) -> list[dict[str, Any]]:
    """Тестирование получения списка зданий."""
    logger.info("\n=== Тестирование получения зданий ===")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{BASE_URL}/buildings"
    
    try:
        async with session.get(url, headers=headers) as response:
            logger.info(f"Status: {response.status}")
            
            if response.status == 401:
                logger.error("Не авторизован")
                return []
            
            if response.status != 200:
                text = await response.text()
                logger.error(f"Ошибка: {text}")
                return []
            
            response_data = await response.json()
            logger.info(f"Здания: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
            
            # Данные могут быть в формате {done: true, data: [...]} или просто [...]
            if isinstance(response_data, dict) and "data" in response_data:
                data = response_data["data"]
            else:
                data = response_data
            
            logger.info(f"✓ Получено зданий: {len(data) if isinstance(data, list) else 'N/A'}")
            return data if isinstance(data, list) else []
    
    except Exception as e:
        logger.exception(f"Ошибка при получении зданий: {e}")
        return []


async def test_get_devices(
    session: aiohttp.ClientSession,
    token: str | None,
    building_id: int | None = None
) -> list[dict[str, Any]]:
    """Тестирование получения устройств."""
    logger.info("\n=== Тестирование получения устройств ===")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    if building_id:
        url = f"{BASE_URL}/buildings/{building_id}/places"
    else:
        # Сначала получим здания
        buildings = await test_get_buildings(session, token)
        if not buildings:
            logger.warning("Нет зданий для получения устройств")
            return []
        
        # Получим устройства из всех зданий
        # Устройства уже есть в поле "places" каждого здания
        all_devices = []
        for building in buildings:
            places = building.get("places", [])
            if places:
                all_devices.extend(places)
                logger.info(f"  Здание '{building.get('title')}': {len(places)} устройств")
        
        logger.info(f"✓ Получено устройств: {len(all_devices)}")
        for device in all_devices:
            logger.info(f"  - {device.get('title', 'Unknown')} (ID: {device.get('id')}, Status: {device.get('status')})")
        return all_devices
    
    try:
        async with session.get(url, headers=headers) as response:
            logger.info(f"Status: {response.status}")
            
            if response.status != 200:
                text = await response.text()
                logger.error(f"Ошибка: {text}")
                return []
            
            data = await response.json()
            if isinstance(data, list):
                devices = data
            elif isinstance(data, dict) and "places" in data:
                devices = data["places"]
            else:
                devices = [data] if data else []
            
            logger.info(f"✓ Получено устройств: {len(devices)}")
            for device in devices:
                logger.info(f"  - {device.get('title', 'Unknown')} (ID: {device.get('id')})")
            return devices
    
    except Exception as e:
        logger.exception(f"Ошибка при получении устройств: {e}")
        return []


async def test_get_device_state(
    session: aiohttp.ClientSession,
    token: str | None,
    device_id: int
) -> dict[str, Any] | None:
    """Тестирование получения состояния устройства."""
    logger.info(f"\n=== Тестирование получения состояния устройства {device_id} ===")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{BASE_URL}/devices/{device_id}"
    
    try:
        async with session.get(url, headers=headers) as response:
            logger.info(f"Status: {response.status}")
            
            if response.status == 404:
                logger.error(f"Устройство {device_id} не найдено")
                return None
            
            if response.status != 200:
                text = await response.text()
                logger.error(f"Ошибка: {text}")
                return None
            
            response_data = await response.json()
            
            # Данные могут быть в формате {done: true, data: {...}} или просто {...}
            if isinstance(response_data, dict) and "data" in response_data:
                data = response_data["data"]
            else:
                data = response_data
            
            logger.info(f"✓ Получено состояние устройства")
            
            # Выводим структурированную информацию
            logger.info("\n--- Основная информация ---")
            logger.info(f"  Title: {data.get('title')}")
            logger.info(f"  Status: {data.get('status')}")
            logger.info(f"  Serial: {data.get('serial')}")
            
            # State info
            state = data.get("state", {})
            if state:
                logger.info("\n--- State ---")
                logger.info(f"  isOn: {state.get('isOn')}")
                info = state.get("info", {})
                logger.info(f"  info.text: {info.get('text')}")
                logger.info(f"  info.iconNames: {info.get('iconNames')}")
            
            # Pult (functions)
            pult = data.get("pult", [])
            if pult:
                logger.info("\n--- Pult (Functions) ---")
                for section in pult:
                    section_title = section.get("title", "Unknown")
                    logger.info(f"\n  Section: {section_title}")
                    functions = section.get("functions", [])
                    for func in functions:
                        func_id = func.get("id")
                        func_title = func.get("title", "Unknown")
                        func_state = func.get("state", {})
                        is_on = func_state.get("isOn")
                        value = func_state.get("value")
                        logger.info(f"    - [{func_id}] {func_title}: isOn={is_on}, value={value}")
            
            # Save full response for analysis
            with open(f"device_{device_id}_state.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"\n  Полный ответ сохранен в device_{device_id}_state.json")
            
            return data
    
    except Exception as e:
        logger.exception(f"Ошибка при получении состояния устройства: {e}")
        return None


async def test_control_device(
    session: aiohttp.ClientSession,
    token: str | None,
    device_id: int,
    function_id: int,
    value: int | bool | None
) -> dict[str, Any] | None:
    """Тестирование управления устройством."""
    logger.info(f"\n=== Тестирование управления устройством {device_id} ===")
    logger.info(f"Function ID: {function_id}, Value: {value}")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    import random
    cmd_id = random.randint(10000000, 99999999)
    
    payload = {
        "cmdId": cmd_id,
        "value": {
            "functionId": function_id,
            "value": value,
            "parameters": None,
        },
        "conflictResolveData": None,
    }
    
    url = f"{BASE_URL}/devices/{device_id}/ctrl?ignoreConflicts=false"
    
    try:
        async with session.post(url, json=payload, headers=headers) as response:
            logger.info(f"Status: {response.status}")
            
            if response.status != 200:
                text = await response.text()
                logger.error(f"Ошибка: {text}")
                return None
            
            data = await response.json()
            logger.info(f"✓ Команда отправлена")
            logger.info(f"Ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if not data.get("done", False):
                logger.warning("Команда не выполнена (done=false)")
                errors = data.get("errors")
                if errors:
                    logger.warning(f"Ошибки: {errors}")
                update_required = data.get("updateRequired")
                if update_required:
                    logger.info("Требуется обновление состояния")
            
            return data
    
    except Exception as e:
        logger.exception(f"Ошибка при управлении устройством: {e}")
        return None


async def interactive_control(
    session: aiohttp.ClientSession,
    token: str | None,
    device_id: int
):
    """Интерактивное управление устройством."""
    logger.info("\n=== Интерактивное управление ===")
    logger.info("Команды:")
    logger.info("  1 - Включить устройство")
    logger.info("  0 - Выключить устройство")
    logger.info("  t <value> - Установить температуру (например: t 25)")
    logger.info("  cool - Режим охлаждения")
    logger.info("  heat - Режим обогрева")
    logger.info("  auto - Автоматический режим")
    logger.info("  dry - Режим осушения")
    logger.info("  fan - Режим вентиляции")
    logger.info("  eco - Эко режим")
    logger.info("  turbo - Турбо режим")
    logger.info("  s - Получить текущее состояние")
    logger.info("  q - Выход")
    
    while True:
        try:
            cmd = input("\nВведите команду: ").strip().lower()
            
            if cmd == "q":
                break
            elif cmd == "s":
                await test_get_device_state(session, token, device_id)
            elif cmd == "1":
                await test_control_device(session, token, device_id, FUNCTION_ID_POWER, True)
            elif cmd == "0":
                await test_control_device(session, token, device_id, FUNCTION_ID_POWER, False)
            elif cmd.startswith("t "):
                try:
                    temp = int(cmd.split()[1])
                    await test_control_device(session, token, device_id, FUNCTION_ID_TEMPERATURE, temp)
                except (ValueError, IndexError):
                    logger.error("Неверный формат. Используйте: t <число>")
            elif cmd == "cool":
                await test_control_device(session, token, device_id, FUNCTION_ID_COOL, None)
            elif cmd == "heat":
                await test_control_device(session, token, device_id, FUNCTION_ID_HEAT, None)
            elif cmd == "auto":
                await test_control_device(session, token, device_id, FUNCTION_ID_AUTO, None)
            elif cmd == "dry":
                await test_control_device(session, token, device_id, FUNCTION_ID_DRY, None)
            elif cmd == "fan":
                await test_control_device(session, token, device_id, FUNCTION_ID_FAN, None)
            elif cmd == "eco":
                await test_control_device(session, token, device_id, FUNCTION_ID_ECO, True)
            elif cmd == "turbo":
                await test_control_device(session, token, device_id, FUNCTION_ID_TURBO, True)
            else:
                logger.warning(f"Неизвестная команда: {cmd}")
        except KeyboardInterrupt:
            break


async def main():
    """Основная функция тестирования."""
    logger.info("=" * 60)
    logger.info("Тестирование API Daichi Comfort Cloud")
    logger.info("=" * 60)
    
    if USERNAME == "your_email@example.com" or PASSWORD == "your_password":
        logger.error("Пожалуйста, укажите ваши учетные данные!")
        logger.info("Варианты:")
        logger.info("  1. Отредактируйте переменные USERNAME и PASSWORD в скрипте")
        logger.info("  2. Установите переменные окружения:")
        logger.info("     export DAICHI_USERNAME='your_email@example.com'")
        logger.info("     export DAICHI_PASSWORD='your_password'")
        return
    
    async with aiohttp.ClientSession() as session:
        # 1. Аутентификация
        auth_success, token = await test_authentication(session)
        if not auth_success:
            logger.error("Аутентификация не удалась. Прекращаем тестирование.")
            return
        
        # 2. Получение зданий
        buildings = await test_get_buildings(session, token)
        
        # 3. Получение устройств
        devices = await test_get_devices(session, token)
        
        if not devices:
            logger.warning("Устройства не найдены. Прекращаем тестирование.")
            return
        
        # 4. Получение состояния первого устройства
        first_device = devices[0]
        device_id = first_device.get("id")
        if device_id:
            await test_get_device_state(session, token, device_id)
            
            # 5. Интерактивное управление (опционально)
            try:
                choice = input("\nЗапустить интерактивное управление? (y/n): ").strip().lower()
                if choice == "y":
                    await interactive_control(session, token, device_id)
            except EOFError:
                pass
    
    logger.info("\n" + "=" * 60)
    logger.info("Тестирование завершено")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
