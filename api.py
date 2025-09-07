import aiohttp
import logging
from bs4 import BeautifulSoup
import re
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import config
from utils import format_currency_message, split_text
# Використовуємо офіційну асинхронну бібліотеку для API Alerts
from alerts_in_ua import AsyncClient as AsyncAlertsClient
async def get_all_alerts(aiohttp_session) -> List[Dict[str, Any]]:
    """
    Отримує всі активні повітряні тривоги, використовуючи офіційну бібліотеку
    alerts_in-ua для стабільної роботи.
    """
    if not config.ALERTS_API_TOKEN:
        logging.warning("ALERTS_API_TOKEN не знайдено. Функція тривог не працює.")
        return []
    alerts_client = AsyncAlertsClient(token=config.ALERTS_API_TOKEN)
    try:
        # Запит обгорнуто в try/except для обробки можливих мережевих помилок
        active_alerts = await alerts_client.get_active_alerts()
        return active_alerts
    except aiohttp.ClientError as e:
        logging.error(f"Помилка HTTP-запиту до alerts.in.ua API: {e}", exc_info=True)
        return []
    except Exception as e:
        logging.error(f"Помилка отримання тривог: {e}", exc_info=True)
        return []
async def get_all_events(aiohttp_session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Парсить сайти, вказані в config.py, щоб отримати інформацію про події."""
    all_events = []
    # Користуємося aiohttp_session для підтримки однієї сесії
    for source_name, url_base in config.EVENTS_SOURCES.items():
        try:
            logging.info(f"Парсинг подій з джерела: {source_name}")
            async with aiohttp_session.get(url_base) as response:
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                # Логіка парсингу для internet-bilet.ua
                if source_name == "internet-bilet.ua":
                    event_containers = soup.find_all('div', class_='event-list-item')
                    for container in event_containers:
                        title_tag = container.find('a', class_='event-name')
                        date_tag = container.find('div', class_='event-date')
                        if title_tag and date_tag:
                            title = title_tag.text.strip()
                            url = "https://www.internet-bilet.ua" + title_tag['href']
                            # Парсинг дати у формат ДД.ММ.РРРР
                            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', date_tag.text)
                            event_date = date_match.group(0) if date_match else "Невідомо"
                            all_events.append({
                                'source': source_name,
                                'title': title,
                                'url': url,
                                'date': event_date
                            })
                # Логіка парсингу для karabas.com
                elif source_name == "karabas.com":
                    event_containers = soup.find_all('div', class_='event-block')
                    for container in event_containers:
                        title_tag = container.find('div', class_='title')
                        date_tag = container.find('div', class_='date')
                        if title_tag and date_tag:
                            title = title_tag.text.strip()
                            url = "https://karabas.com" + container.find('a', class_='event-image-link')['href']
                            # Парсинг дати
                            date_text = date_tag.text.strip().split(',')[0]
                            date_parts = re.findall(r'\b\d+\b', date_text)
                            event_date = f"{date_parts[0].zfill(2)}.{date_parts[1].zfill(2)}.{date.today().year}" if date_parts else "Невідомо"
                            all_events.append({
                                'source': source_name,
                                'title': title,
                                'url': url,
                                'date': event_date
                            })
                # Логіка парсингу для kino-teatr.ua
                elif source_name == "kino-teatr.ua":
                    movie_links = soup.select('div.poster_list_box.movies a')
                    for link in movie_links:
                        try:
                            movie_url = "https://kino-teatr.ua" + link['href']
                            async with aiohttp_session.get(movie_url) as film_response:
                                film_response.raise_for_status()
                                film_html = await film_response.text()
                                film_soup = BeautifulSoup(film_html, 'html.parser')
                                title_element = film_soup.find('h1', class_='name')
                                title = title_element.text.strip() if title_element else "Без назви"
                                date_element = film_soup.find(lambda tag: tag.name == "p" and "Дата прем'єри" in tag.text)
                                if date_element:
                                    date_text = date_element.find_next_sibling('p').text.strip()
                                    event_date = re.search(r'\d{2}\.\d{2}\.\d{4}', date_text).group(0)
                                else:
                                    event_date = "Невідомо"
                                all_events.append({
                                    'source': source_name,
                                    'title': title,
                                    'url': url,
                                    'date': event_date
                                })
                        except Exception as e:
                            logging.error(f"Помилка при парсингу детальної сторінки фільму {url}: {e}", exc_info=True)
        except Exception as e:
            logging.error(f"Помилка при парсингу подій з {source_name}: {e}", exc_info=True)
    return all_events
async def get_currency_rates(aiohttp_session) -> Optional[List[Dict[str, Any]]]:
    """Отримує актуальні курси валют від Monobank API."""
    url = config.CURRENCY_API_URL
    try:
        async with aiohttp_session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return data
    except Exception as e:
        logging.error(f"Помилка при отриманні курсів валют: {e}")
        return None

