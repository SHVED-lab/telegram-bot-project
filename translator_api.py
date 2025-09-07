import aiohttp
import asyncio
from typing import Dict, Optional, Any
import logging
import os
# Завантажуємо deep_translator. Це бібліотека для перекладу, яка надає багато можливостей.
from deep_translator import GoogleTranslator, LingueeTranslator
logger = logging.getLogger(__name__)
# =========================================================================
# Функція для отримання мов перекладу
# Це асинхронна функція для отримання доступних мов перекладу.
# Вона буде використовуватися для створення кнопок мов у боті.
# =========================================================================
async def get_supported_languages() -> Dict[str, str]:
    """
    Асинхронно отримує словник підтримуваних мов перекладу.
    :return: Словник, де ключ - це код мови (напр., 'uk', 'en'),
             а значення - це назва мови (напр., 'Ukrainian', 'English').
    """
    loop = asyncio.get_event_loop()
    # Використовуємо run_in_executor, щоб не блокувати основний цикл подій
    # оскільки get_supported_languages є синхронною функцією.
    return await loop.run_in_executor(None, GoogleTranslator(source='auto', target='en').get_supported_languages, as_dict=True)
# =========================================================================
# Функція для перекладу тексту
# Це асинхронна функція, яка використовує різні сервіси перекладу.
# Вона спробує перекласти текст за допомогою GoogleTranslator, а якщо
# виникне помилка, спробує використати LingueeTranslator.
# =========================================================================
async def translate_text(text: str, source_lang: str, target_lang: str) -> Optional[str]:
    """
    Асинхронно перекладає текст з однієї мови на іншу, використовуючи GoogleTranslator,
    а потім, у разі невдачі, LingueeTranslator як резервний варіант.
    :param text: Текст для перекладу.
    :param source_lang: Мова оригіналу (код, напр., 'uk').
    :param target_lang: Мова перекладу (код, напр., 'en').
    :return: Перекладений текст або None у разі помилки.
    """
    loop = asyncio.get_event_loop()
    translated_text = None
    # 1. Спроба перекладу за допомогою GoogleTranslator
    try:
        logger.info(f"Спроба перекладу тексту '{text}' з {source_lang} на {target_lang} за допомогою GoogleTranslator.")
        translated_text = await loop.run_in_executor(
            None,
            GoogleTranslator(source=source_lang, target=target_lang).translate,
            text
        )
        logger.info("Переклад через GoogleTranslator успішний.")
    except Exception as e:
        logger.error(f"Помилка при перекладі через GoogleTranslator: {e}")
    # 2. Якщо GoogleTranslator не спрацював, спробуємо LingueeTranslator
    if not translated_text:
        try:
            logger.info("Спроба перекладу за допомогою LingueeTranslator як резервного варіанту.")
            # LingueeTranslator вимагає точного співпадіння мов. Перевіряємо.
            supported_langs_linguee = await loop.run_in_executor(
                None,
                LingueeTranslator(source='en', target='uk').get_supported_languages,
                as_dict=True
            )
            if source_lang in supported_langs_linguee and target_lang in supported_langs_linguee:
                translated_text = await loop.run_in_executor(
                    None,
                    LingueeTranslator(source=source_lang, target=target_lang).translate,
                    text
                )
                logger.info("Переклад через LingueeTranslator успішний.")
            else:
                logger.warning(f"LingueeTranslator не підтримує мови {source_lang} та {target_lang}.")
        except Exception as e:
            logger.error(f"Помилка при перекладі через LingueeTranslator: {e}")
    return translated_text
