"""
================================================================================
VOICE RESTAURANT ASSISTANT - CONFIGURATION LOADER
================================================================================
Carga y gestion de archivos de configuracion (JSON/YAML)
Con soporte para obtener datos del menu-service API
================================================================================
"""

import json
import yaml
import logging
import httpx
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Remove trailing /api/v1 if present (to avoid duplication)
_raw_menu_url = os.getenv("MENU_SERVICE_URL", "http://menu-service:5011")
MENU_SERVICE_URL = _raw_menu_url.rstrip("/").removesuffix("/api/v1")


class ConfigLoader:
    def __init__(self, config_dir=None):
        if config_dir is None:
            current_file = Path(__file__)
            config_dir = current_file.parent.parent.parent / "config"
        self.config_dir = Path(config_dir)
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {self.config_dir}")
        logger.info(f"ConfigLoader inicializado: {self.config_dir}")
        self._menu_knowledge = None
        self._menu_from_api = None
        self._sales_rules = None
        self._assistant_prompts = None
        self._last_reload = None
        self._last_api_fetch = None

    def load_menu_from_api(self, force_reload=False):
        if (self._menu_from_api is not None and not force_reload and
            self._last_api_fetch and (datetime.now() - self._last_api_fetch).seconds < 60):
            return self._menu_from_api
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{MENU_SERVICE_URL}/api/v1/agent/menu")
                response.raise_for_status()
                self._menu_from_api = response.json()
                self._last_api_fetch = datetime.now()
                logger.info(f"Menu loaded from API")
                return self._menu_from_api
        except Exception as e:
            logger.warning(f"Failed to load menu from API: {e}")
            return None

    def get_recommendations_from_api(self, **filters):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{MENU_SERVICE_URL}/api/v1/agent/recommendations", params=filters)
                response.raise_for_status()
                return response.json().get("recommendations", [])
        except:
            return []

    def search_products_from_api(self, **filters):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{MENU_SERVICE_URL}/api/v1/agent/search", params=filters)
                response.raise_for_status()
                return response.json().get("products", [])
        except:
            return []

    def get_upsell_suggestions_from_api(self, product_id):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{MENU_SERVICE_URL}/api/v1/agent/upsell/{product_id}")
                response.raise_for_status()
                return response.json()
        except:
            return {"suggestions": []}

    def load_menu_knowledge(self, force_reload=False):
        api_menu = self.load_menu_from_api(force_reload)
        if api_menu:
            return self._convert_api_menu_to_knowledge(api_menu)
        if self._menu_knowledge is None or force_reload:
            menu_file = self.config_dir / "menu_knowledge.json"
            if not menu_file.exists():
                return self._get_default_menu_knowledge()
            try:
                with open(menu_file, "r", encoding="utf-8") as f:
                    self._menu_knowledge = json.load(f)
            except:
                return self._get_default_menu_knowledge()
        return self._menu_knowledge

    def _convert_api_menu_to_knowledge(self, api_menu):
        categories = []
        for cat in api_menu.get("categories", []):
            products = []
            for prod in cat.get("products", []):
                ingredients = prod.get("ingredients", "") or ""
                products.append({
                    "id": str(prod.get("id")),
                    "name": prod.get("name"),
                    "description": prod.get("description"),
                    "price": prod.get("price"),
                    "available": prod.get("is_available", True),
                    "popular": prod.get("popularity", 3) >= 4,
                    "ingredients": ingredients.split(", ") if ingredients else [],
                    "spice_level": self._get_spice_label(prod.get("spice_level", 0)),
                    "spice_level_num": prod.get("spice_level", 0),
                    "tags": self._get_product_tags(prod),
                    "preparation_time": prod.get("preparation_time", 15),
                    "popularity": prod.get("popularity", 3),
                    "profitability": prod.get("profitability", "media"),
                    "menu_classification": prod.get("menu_classification"),
                    "video_url": prod.get("video_url")
                })
            categories.append({"id": str(cat.get("id")), "name": cat.get("name"), "description": cat.get("description"), "products": products})
        return {
            "menu": {"version": "2.0.0", "restaurant_name": "Mi Restaurante", "categories": categories, "combos": [], "promotions": []},
            "metadata": {"currency": "MXN", "source": "api"},
            "recommendations": api_menu.get("recommendations", {}),
            "unavailable": api_menu.get("unavailable", [])
        }

    def _get_spice_label(self, level):
        return {0: "suave", 1: "poco picante", 2: "medio", 3: "picante"}.get(level, "suave")

    def _get_product_tags(self, product):
        tags = []
        if product.get("menu_classification") == "estrella":
            tags.extend(["estrella", "recomendado", "mas vendido"])
        elif product.get("menu_classification") == "caballo":
            tags.append("popular")
        if product.get("popularity", 3) >= 4:
            tags.append("favorito")
        if product.get("profitability") == "alta":
            tags.append("gran valor")
        return tags

    def load_sales_rules(self, force_reload=False):
        if self._sales_rules is None or force_reload:
            sales_file = self.config_dir / "sales_rules.yaml"
            if not sales_file.exists():
                return self._get_default_sales_rules()
            try:
                with open(sales_file, "r", encoding="utf-8") as f:
                    self._sales_rules = yaml.safe_load(f)
            except:
                return self._get_default_sales_rules()
        return self._sales_rules

    def load_assistant_prompts(self, force_reload=False):
        if self._assistant_prompts is None or force_reload:
            prompts_file = self.config_dir / "assistant_prompts.yaml"
            if not prompts_file.exists():
                return self._get_default_prompts()
            try:
                with open(prompts_file, "r", encoding="utf-8") as f:
                    self._assistant_prompts = yaml.safe_load(f)
            except:
                return self._get_default_prompts()
        return self._assistant_prompts

    def reload_all(self):
        self._menu_from_api = None
        self.load_menu_knowledge(force_reload=True)
        self.load_sales_rules(force_reload=True)
        self.load_assistant_prompts(force_reload=True)
        self._last_reload = datetime.now()

    def get_menu_categories(self):
        return self.load_menu_knowledge().get("menu", {}).get("categories", [])

    def get_all_products(self):
        categories = self.get_menu_categories()
        all_products = []
        for category in categories:
            for product in category.get("products", []):
                product_copy = product.copy()
                product_copy["category_name"] = category.get("name")
                product_copy["category_id"] = category.get("id")
                all_products.append(product_copy)
        return all_products

    def get_product_by_id(self, product_id):
        for product in self.get_all_products():
            if str(product.get("id")) == str(product_id):
                return product
        return None

    def get_popular_products(self):
        return [p for p in self.get_all_products() if p.get("popularity", 3) >= 4 or p.get("popular", False)]

    def get_star_products(self):
        return [p for p in self.get_all_products() if p.get("menu_classification") == "estrella"]

    def get_products_by_classification(self, classification):
        return [p for p in self.get_all_products() if p.get("menu_classification") == classification]

    def get_products_without_spice(self):
        return [p for p in self.get_all_products() if p.get("spice_level_num", 0) == 0]

    def get_active_promotions(self):
        promotions = self.load_menu_knowledge().get("menu", {}).get("promotions", [])
        return [p for p in promotions if p.get("active", False)]

    def get_combos(self):
        return self.load_menu_knowledge().get("menu", {}).get("combos", [])

    def get_unavailable_products(self):
        return self.load_menu_knowledge().get("unavailable", [])

    def get_recommendations(self):
        return self.load_menu_knowledge().get("recommendations", {})

    def get_sales_rule(self, category):
        return self.load_sales_rules().get("sales_rules_by_category", {}).get(category)

    def get_master_prompt(self, **kwargs):
        prompts = self.load_assistant_prompts()
        master_template = prompts.get("system_prompts", {}).get("master_prompt", "")
        menu_summary = self._get_compact_menu_summary()
        defaults = {
            "restaurant_name": self.get_restaurant_name(),
            "menu_knowledge": menu_summary,
            "sales_rules": "Prioriza platillos estrella. Sugiere complementos.",
            "active_promotions": ""
        }
        try:
            return master_template.format(**{**defaults, **kwargs})
        except KeyError:
            return master_template

    def _get_compact_menu_summary(self):
        recs = self.get_recommendations()
        estrellas = recs.get('estrellas', [])[:5]
        unavailable = self.get_unavailable_products()
        lines = []
        if estrellas:
            lines.append(f"ESTRELLAS: {', '.join([p['name'] for p in estrellas])}")
        if unavailable:
            lines.append(f"AGOTADOS: {', '.join([p['name'] for p in unavailable])}")
        for cat in self.get_menu_categories()[:5]:
            prods = [p['name'] for p in cat.get('products', [])[:3]]
            lines.append(f"{cat['name']}: {', '.join(prods)}")
        return " | ".join(lines)

    def get_prompt_template(self, prompt_name):
        return self.load_assistant_prompts().get("system_prompts", {}).get(prompt_name, "")

    def get_response_template(self, template_name):
        return self.load_assistant_prompts().get("response_templates", {}).get(template_name, {}).get("template", "")

    def get_restaurant_name(self):
        return self.load_menu_knowledge().get("menu", {}).get("restaurant_name", "Mi Restaurante")

    def get_restaurant_metadata(self):
        return self.load_menu_knowledge().get("metadata", {})

    def _get_default_menu_knowledge(self):
        return {"menu": {"version": "1.0.0", "restaurant_name": "Mi Restaurante", "categories": [], "combos": [], "promotions": []}, "metadata": {"currency": "MXN"}}

    def _get_default_sales_rules(self):
        return {"general_interaction_rules": {"tone": "profesional y amable"}, "sales_rules_by_category": {}}

    def _get_default_prompts(self):
        return {"system_prompts": {"master_prompt": "Eres un asistente de voz profesional para restaurante."}, "response_templates": {}}


_config_loader = None


def get_config_loader():
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


config_loader = get_config_loader()
