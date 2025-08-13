#!/usr/bin/env python3
"""
Скрипт для генерации NFT изображений для Solana Mafia бизнесов
Использует OpenAI DALL-E API для создания 3D изометрических объектов
"""

import os
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List
import argparse
from PIL import Image
import torch
from transformers import pipeline
try:
    from rembg import remove as rembg_remove, new_session
    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False
    rembg_remove = None
    new_session = None
import requests
import base64

# Конфигурация бизнесов (из app/frontend/src/data/businesses.ts)
BUSINESSES = {
    "tobacco": {
        "name": "Lucky Strike Cigars",
        "description": "A distinguished tobacco shop specializing in premium cigars and vintage smoking accessories.",
        "emoji": "🚬",
        "levels": [
            {
                "level": 0,
                "name": "Corner Stand",
                "description": "A humble kiosk specializing in tobacco products and classic smoking accessories."
            },
            {
                "level": 1,
                "name": "Smoke & Secrets",
                "description": "Premium tobacco shop with exclusive smoking lounge area."
            },
            {
                "level": 2,
                "name": "Cigar Lounge",
                "description": "Elite club for the chosen ones."
            },
            {
                "level": 3,
                "name": "Empire of Smoke",
                "description": "Citywide network of operations."
            }
        ]
    },
    "funeral": {
        "name": "Eternal Rest Funeral",
        "description": "A funeral parlor providing discreet services for those who need to 'disappear'.",
        "emoji": "⚰️",
        "levels": [
            {
                "level": 0,
                "name": "Quiet Departure",
                "description": "Simple funeral services with no questions asked."
            },
            {
                "level": 1,
                "name": "Silent Service",
                "description": "Premium services for sensitive situations."
            },
            {
                "level": 2,
                "name": "Final Solution",
                "description": "VIP funerals for the most elite clients."
            },
            {
                "level": 3,
                "name": "Legacy of Silence",
                "description": "Empire of silence spanning the entire city."
            }
        ]
    },
    "car": {
        "name": "Midnight Motors Garage",
        "description": "An auto shop specializing in untraceable vehicle modifications.",
        "emoji": "🔧",
        "levels": [
            {
                "level": 0,
                "name": "Street Repair",
                "description": "Regular automotive workshop services."
            },
            {
                "level": 1,
                "name": "Custom Works",
                "description": "Tuning and special modifications available."
            },
            {
                "level": 2,
                "name": "Underground Garage",
                "description": "Secret conversions and untraceable work."
            },
            {
                "level": 3,
                "name": "Ghost Fleet",
                "description": "Empire of invisible vehicles across the city."
            }
        ]
    },
    "restaurant": {
        "name": "Nonna's Secret Kitchen",
        "description": "An Italian restaurant where important family meetings take place.",
        "emoji": "🍝",
        "levels": [
            {
                "level": 0,
                "name": "Family Recipe",
                "description": "Home kitchen serving traditional dishes."
            },
            {
                "level": 1,
                "name": "Mama's Table",
                "description": "Popular trattoria in the neighborhood."
            },
            {
                "level": 2,
                "name": "Don's Dining",
                "description": "Restaurant for important family meetings."
            },
            {
                "level": 3,
                "name": "Empire Feast",
                "description": "Network of cover restaurants across the city."
            }
        ]
    },
    "club": {
        "name": "Velvet Shadows Club",
        "description": "An elite club for conducting exclusive 'family business'.",
        "emoji": "🥃",
        "levels": [
            {
                "level": 0,
                "name": "Private Room",
                "description": "Closed room for discrete meetings."
            },
            {
                "level": 1,
                "name": "Exclusive Lounge",
                "description": "VIP zone for important guests."
            },
            {
                "level": 2,
                "name": "Shadow Society",
                "description": "Secret society for the most influential."
            },
            {
                "level": 3,
                "name": "Velvet Empire",
                "description": "Network of influential clubs across the city."
            }
        ]
    },
    "charity": {
        "name": "Angel's Mercy Foundation",
        "description": "A charity foundation providing 'assistance' to those in need.",
        "emoji": "👼",
        "levels": [
            {
                "level": 0,
                "name": "Helping Hand",
                "description": "Local charity providing community assistance."
            },
            {
                "level": 1,
                "name": "Guardian Angel",
                "description": "Major donations and community influence."
            },
            {
                "level": 2,
                "name": "Divine Intervention",
                "description": "International foundation with global reach."
            },
            {
                "level": 3,
                "name": "Mercy Empire",
                "description": "Global 'assistance' network spanning continents."
            }
        ]
    }
}

class NFTImageGenerator:
    def __init__(self, api_key: str, base_output_dir: str = "./app/frontend/public/nft-images", api_version: str = "responses", remove_bg: bool = True, bg_method: str = "rembg"):
        self.api_key = api_key
        self.base_output_dir = Path(base_output_dir)
        self.api_version = api_version  # "responses" (gpt-image-1) or "images" (dall-e-3)
        self.remove_bg = remove_bg
        self.bg_method = bg_method  # "rembg", "bria", or "none"
        self.bg_remover = None
        self.rembg_session = None
        
        # Инициализируем выбранный метод удаления фона
        if self.remove_bg:
            if self.bg_method == "rembg" and REMBG_AVAILABLE:
                try:
                    print("🔄 Загружаем rembg модель...")
                    # Создаем сессию с лучшей моделью для качества
                    self.rembg_session = new_session('isnet-general-use')  # Высокое качество для общих объектов
                    print("✅ rembg загружен успешно (модель: isnet-general-use)")
                except Exception as e:
                    print(f"⚠️  Не удалось загрузить rembg: {e}")
                    print("💡 Попробуем BRIA RMBG...")
                    self._init_bria()
            elif self.bg_method == "bria" or not REMBG_AVAILABLE:
                if not REMBG_AVAILABLE:
                    print("⚠️ rembg недоступен, используем BRIA RMBG")
                self._init_bria()
            else:
                print("💡 Удаление фона отключено")
                self.remove_bg = False
        
        # Базовый промпт для генерации
        self.base_prompt = """Create a detailed 3D isometric business building representing {business_name} - {level_name}.
{description}

CRITICAL ISOLATION REQUIREMENTS:
- Building placed on a small, defined ground plate or paved area (street section) 
- Ground plate should be minimal and contained within the asset boundaries
- NO shadows, lighting, or effects extending beyond the ground plate boundaries
- NO external ambient lighting or effects outside the contained area
- All lighting and shadows must be contained within the building and its immediate ground area
- Clean, self-contained game asset suitable for automatic background removal
- The ground plate adds realism but must not extend beyond asset boundaries

CRITICAL: Transparent background is essential - the image must have NO background, completely transparent PNG format.
NO TEXT OR SIGNAGE - clean building without any visible text, letters, or signs.

Style requirements:
- 3D isometric perspective (viewed from top-side angle, like a video game asset)
- Highly detailed and professional 3D rendering
- Game asset style with cartoon-like quality and rich details
- Rich textures and realistic lighting contained within the asset
- Dark, sophisticated vintage aesthetic with elegant colors (deep browns, golds, dark greens)
- Single building/establishment focus, no people or characters
- Premium game asset quality suitable for blockchain gaming
- Professional AAA game asset quality with clean edges
- Retro 1920s-1950s business architecture style with Art Deco elements
- High contrast, sharp details, and premium materials (wood, brass, marble, glass)
- Small contained ground plate/paved area that adds street realism

The building should clearly represent: {specific_description}

IMPORTANT: The final image must be a completely self-contained building object with minimal ground plate, perfect for game asset use with automatic background removal."""
    
    def _init_bria(self):
        """Инициализация BRIA RMBG как fallback"""
        try:
            print("🔄 Загружаем BRIA RMBG модель...")
            self.bg_remover = pipeline("image-segmentation", 
                                     model="briaai/RMBG-1.4", 
                                     trust_remote_code=True,
                                     device=0 if torch.cuda.is_available() else -1)
            self.bg_method = "bria"
            print("✅ BRIA RMBG загружена успешно")
        except Exception as e:
            print(f"⚠️  Не удалось загрузить BRIA RMBG: {e}")
            print("💡 Продолжаем без удаления фона")
            self.remove_bg = False

    def create_prompt(self, business_type: str, level: int) -> str:
        """Создает промпт для генерации изображения"""
        business = BUSINESSES[business_type]
        level_data = business["levels"][level]
        
        # Специфические детали для каждого типа бизнеса
        specific_details = {
            "tobacco": {
                0: "A small street tobacco kiosk, modest single-story stand with basic cigarette displays and simple wooden counter",
                1: "A mid-size traditional tobacco shop with premium cigar displays, mahogany wood details, and classic storefront design",
                2: "An intimate luxury cigar lounge, 2-3 story elegant building with sophisticated interior design and premium materials",
                3: "A massive tobacco empire headquarters - towering multi-story complex with grand architecture, multiple wings, rooftop elements, and imposing presence that dominates the skyline"
            },
            "funeral": {
                0: "A small funeral home, modest single-story building with simple chapel and basic service area",
                1: "A mid-size traditional funeral parlor with premium wooden details and elegant mourning rooms",
                2: "A luxury funeral facility, 2-3 story sophisticated building with VIP chambers and refined architecture",
                3: "A massive funeral empire complex - towering multi-story headquarters with multiple wings, grand architecture, and imposing memorial presence"
            },
            "car": {
                0: "A small street garage, modest single-bay workshop with basic tools and simple car lift",
                1: "A mid-size auto workshop with multiple service bays, advanced tuning equipment, and modern tools",
                2: "A sophisticated garage facility, 2-3 story building with premium modification bays and upscale showroom area",
                3: "A massive automotive empire complex - towering multi-story headquarters with numerous service bays, high-tech equipment, and imposing industrial presence"
            },
            "restaurant": {
                0: "A small home kitchen, modest single-story building with traditional cooking equipment and cozy family atmosphere",
                1: "A mid-size neighborhood trattoria with outdoor seating, bustling dining area, and authentic Italian decor",
                2: "An upscale Italian restaurant, 2-3 story elegant building with private dining rooms and sophisticated ambiance",
                3: "A massive restaurant empire complex - towering multi-story headquarters with multiple dining areas, luxury fixtures, and grand culinary architecture"
            },
            "club": {
                0: "A small private meeting room, modest single-story space with elegant furniture and classic decor",
                1: "A mid-size exclusive lounge with premium bar, sophisticated lighting, and luxurious member areas",
                2: "An elegant society hall, 2-3 story sophisticated building with refined ambiance and vintage architecture",
                3: "A massive club empire complex - towering multi-story Victorian headquarters with multiple levels, opulent decor, and prestigious commanding presence"
            },
            "charity": {
                0: "A small charity office, modest single-story building with donation boxes and basic community service area",
                1: "A mid-size foundation building with multiple donation centers, outreach facilities, and modern volunteer areas",
                2: "An international charity headquarters, 2-3 story professional building with communication centers and elegant architecture",
                3: "A massive charity empire complex - towering multi-story headquarters with multiple wings, prestigious architecture, and commanding philanthropic presence"
            }
        }
        
        specific_description = specific_details[business_type][level]
        
        return self.base_prompt.format(
            business_name=business["name"],
            level_name=level_data["name"],
            description=level_data["description"],
            specific_description=specific_description
        )

    def remove_background(self, image_path: str) -> bool:
        """Удаляет фон с помощью выбранного метода (rembg или BRIA RMBG)"""
        if not self.remove_bg:
            return True
            
        try:
            print(f"🔄 Удаляем фон ({self.bg_method}): {image_path}")
            
            # Загружаем изображение
            original_image = Image.open(image_path)
            
            if self.bg_method == "rembg" and self.rembg_session:
                # Используем rembg - простой и надежный
                result_image = rembg_remove(original_image, session=self.rembg_session)
                
                # rembg возвращает готовое изображение с прозрачным фоном
                result_image.save(image_path, 'PNG')
                print(f"✅ Фон удален (rembg): {image_path}")
                return True
                
            elif self.bg_method == "bria" and self.bg_remover:
                # Используем BRIA RMBG как fallback
                return self._remove_background_bria(original_image, image_path)
            
            else:
                print(f"⚠️  Метод удаления фона {self.bg_method} недоступен")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка удаления фона {image_path}: {e}")
            return False
    
    def _remove_background_bria(self, original_image: Image.Image, image_path: str) -> bool:
        """Удаляет фон с помощью BRIA RMBG (fallback метод)"""
        try:
            # Используем BRIA RMBG для удаления фона
            result = self.bg_remover(original_image)
            
            # result это list с одним элементом содержащим 'mask' и 'label'
            if isinstance(result, list) and len(result) > 0:
                # Создаем маску для переднего плана
                mask = result[0].get('mask')
                if mask:
                    # Применяем маску к оригинальному изображению
                    # Конвертируем в RGBA если нужно
                    if original_image.mode != 'RGBA':
                        original_image = original_image.convert('RGBA')
                    
                    # Применяем маску
                    mask_resized = mask.resize(original_image.size)
                    
                    # Создаем финальное изображение с прозрачным фоном
                    final_image = Image.new('RGBA', original_image.size, (0, 0, 0, 0))
                    final_image.paste(original_image, mask=mask_resized)
                    
                    # Сохраняем с прозрачным фоном
                    final_image.save(image_path, 'PNG')
                    print(f"✅ Фон удален (BRIA): {image_path}")
                    return True
            
            print(f"⚠️  Не удалось обработать маску BRIA для {image_path}")
            return False
            
        except Exception as e:
            print(f"❌ Ошибка BRIA удаления фона {image_path}: {e}")
            return False

    async def generate_image_responses(self, prompt: str, filename: str) -> bool:
        """Генерирует изображение через Responses API с gpt-image-1 (лучшее качество)"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4.1-mini",
            "input": prompt,
            "tools": [{"type": "image_generation"}]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Извлекаем base64 изображение из ответа
                        image_data = None
                        for output in result.get("output", []):
                            if output.get("type") == "image_generation_call":
                                image_data = output.get("result")
                                break
                        
                        if image_data:
                            # Декодируем base64 и сохраняем
                            import base64
                            with open(filename, "wb") as f:
                                f.write(base64.b64decode(image_data))
                            
                            print(f"✅ Сохранено (Responses API): {filename}")
                            
                            # Удаляем фон если включено
                            if self.remove_bg:
                                self.remove_background(filename)
                                
                            return True
                        else:
                            print(f"❌ Не найдены данные изображения в ответе")
                            return False
                    else:
                        error_data = await response.json()
                        print(f"❌ Ошибка Responses API: {response.status} - {error_data}")
                        return False
                        
        except Exception as e:
            print(f"❌ Исключение при генерации через Responses API {filename}: {e}")
            return False

    async def generate_image_dalle(self, prompt: str, filename: str) -> bool:
        """Генерирует изображение через Images API с DALL-E 3"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "hd",
            "style": "vivid",
            "response_format": "url"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/images/generations",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        image_url = result["data"][0]["url"]
                        
                        # Скачиваем изображение
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                image_data = await img_response.read()
                                
                                # Сохраняем файл
                                with open(filename, "wb") as f:
                                    f.write(image_data)
                                
                                print(f"✅ Сохранено (DALL-E 3): {filename}")
                                
                                # Удаляем фон если включено
                                if self.remove_bg:
                                    self.remove_background(filename)
                                    
                                return True
                            else:
                                print(f"❌ Ошибка скачивания изображения: {img_response.status}")
                                return False
                    else:
                        error_data = await response.json()
                        print(f"❌ Ошибка Images API: {response.status} - {error_data}")
                        return False
                        
        except Exception as e:
            print(f"❌ Исключение при генерации через Images API {filename}: {e}")
            return False

    async def generate_image(self, prompt: str, filename: str) -> bool:
        """Генерирует изображение через выбранный API"""
        if self.api_version == "responses":
            return await self.generate_image_responses(prompt, filename)
        else:
            return await self.generate_image_dalle(prompt, filename)

    async def generate_test_images(self, business_type: str = "tobacco", max_levels: int = 2):
        """Генерирует тестовые изображения для отладки промптов"""
        print(f"🧪 Генерируем тестовые изображения для {business_type} (уровни 0-{max_levels-1})")
        
        business = BUSINESSES[business_type]
        output_dir = self.base_output_dir / business_type
        output_dir.mkdir(exist_ok=True)
        
        for level in range(max_levels):
            level_data = business["levels"][level]
            filename = output_dir / f"level_{level}_{level_data['name'].lower().replace(' ', '_').replace('&', 'and')}.png"
            
            prompt = self.create_prompt(business_type, level)
            print(f"\n📝 Промпт для {business_type} уровень {level}:")
            print(f"   {level_data['name']}: {level_data['description']}")
            print(f"   Файл: {filename}")
            
            success = await self.generate_image(prompt, filename)
            if success:
                print(f"✅ Успешно: {filename}")
            else:
                print(f"❌ Неудача: {filename}")
            
            # Пауза между запросами
            await asyncio.sleep(2)

    async def generate_all_images(self):
        """Генерирует все 24 изображения"""
        print("🚀 Начинаем генерацию всех NFT изображений...")
        
        total_images = 0
        successful_images = 0
        
        for business_type, business in BUSINESSES.items():
            print(f"\n🏢 Генерируем {business['name']} ({business_type})")
            
            output_dir = self.base_output_dir / business_type
            output_dir.mkdir(exist_ok=True)
            
            for level in range(4):  # 0, 1, 2, 3
                level_data = business["levels"][level]
                filename = output_dir / f"level_{level}_{level_data['name'].lower().replace(' ', '_').replace('&', 'and')}.png"
                
                prompt = self.create_prompt(business_type, level)
                print(f"   Генерируем уровень {level}: {level_data['name']}")
                
                total_images += 1
                success = await self.generate_image(prompt, filename)
                
                if success:
                    successful_images += 1
                
                # Пауза между запросами (OpenAI rate limiting)
                await asyncio.sleep(3)
        
        print(f"\n🎯 Завершено! Успешно: {successful_images}/{total_images}")

    def show_prompts(self, business_type: str = None):
        """Показывает промпты для проверки без генерации"""
        if business_type:
            businesses_to_show = {business_type: BUSINESSES[business_type]}
        else:
            businesses_to_show = BUSINESSES
            
        for btype, business in businesses_to_show.items():
            print(f"\n🏢 {business['name']} ({btype})")
            print("=" * 50)
            
            for level in range(4):
                level_data = business["levels"][level]
                prompt = self.create_prompt(btype, level)
                
                print(f"\n📝 Уровень {level}: {level_data['name']}")
                print(f"   Описание: {level_data['description']}")
                print(f"   Промпт:\n{prompt[:200]}...")

async def main():
    parser = argparse.ArgumentParser(description="Генератор NFT изображений для Solana Mafia")
    parser.add_argument("--api-key", required=True, help="OpenAI API ключ")
    parser.add_argument("--mode", choices=["test", "all", "prompts"], default="test", 
                       help="Режим: test (тестовые), all (все), prompts (показать промпты)")
    parser.add_argument("--business", choices=list(BUSINESSES.keys()), default="tobacco",
                       help="Тип бизнеса для тестирования")
    parser.add_argument("--levels", type=int, default=2, help="Количество уровней для тестирования")
    parser.add_argument("--api", choices=["responses", "images"], default="responses",
                       help="API версия: responses (gpt-image-1, лучшее качество) или images (dall-e-3)")
    parser.add_argument("--remove-bg", action="store_true", default=True,
                       help="Автоматически удалять фон (по умолчанию включено)")
    parser.add_argument("--no-remove-bg", action="store_true", 
                       help="Отключить автоматическое удаление фона")
    parser.add_argument("--bg-method", choices=["rembg", "bria"], default="rembg",
                       help="Метод удаления фона: rembg (рекомендуется) или bria (fallback)")
    
    args = parser.parse_args()
    
    # Определяем нужно ли удалять фон
    remove_bg = args.remove_bg and not args.no_remove_bg
    
    generator = NFTImageGenerator(args.api_key, api_version=args.api, remove_bg=remove_bg, bg_method=args.bg_method)
    
    if args.mode == "prompts":
        generator.show_prompts(args.business if args.business else None)
    elif args.mode == "test":
        await generator.generate_test_images(args.business, args.levels)
    elif args.mode == "all":
        await generator.generate_all_images()

if __name__ == "__main__":
    asyncio.run(main())