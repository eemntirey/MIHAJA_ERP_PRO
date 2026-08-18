import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from app.security.tenant import get_current_tenant_id

logger = logging.getLogger(__name__)


class ExternalAIService:
    """Abstraction pour appeler des fournisseurs IA externes."""

    def __init__(self):
        self.provider = os.getenv('AI_PROVIDER', 'local').lower()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.anthropic_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')
        self.timeout = int(os.getenv('AI_REQUEST_TIMEOUT', '30'))

    def is_configured(self) -> bool:
        if self.provider == 'openai':
            return bool(self.openai_api_key)
        if self.provider == 'anthropic':
            return bool(self.anthropic_api_key)
        return False

    def chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        if not self.is_configured():
            return {
                'provider': 'local',
                'content': None,
                'error': 'Aucun fournisseur IA externe configuré'
            }

        try:
            if self.provider == 'openai':
                return self._call_openai(messages, system_prompt)
            if self.provider == 'anthropic':
                return self._call_anthropic(messages, system_prompt)
        except Exception as e:
            logger.error(f"Erreur appel IA externe ({self.provider}): {str(e)}")
            return {
                'provider': self.provider,
                'content': None,
                'error': str(e)
            }

        return {
            'provider': 'local',
            'content': None,
            'error': 'Fournisseur IA non supporté'
        }

    def _call_openai(self, messages: List[Dict[str, str]], system_prompt: Optional[str]) -> Dict[str, Any]:
        payload_messages = []
        if system_prompt:
            payload_messages.append({'role': 'system', 'content': system_prompt})
        payload_messages.extend(messages)

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f"Bearer {self.openai_api_key}",
                'Content-Type': 'application/json'
            },
            json={
                'model': self.openai_model,
                'messages': payload_messages,
                'temperature': 0.2,
                'max_tokens': 1200
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        content = data['choices'][0]['message']['content']
        return {
            'provider': 'openai',
            'content': content,
            'model': self.openai_model,
            'usage': data.get('usage')
        }

    def _call_anthropic(self, messages: List[Dict[str, str]], system_prompt: Optional[str]) -> Dict[str, Any]:
        payload_messages = []
        for m in messages:
            role = 'user' if m['role'] == 'user' else 'assistant'
            payload_messages.append({'role': role, 'content': m['content']})

        body = {
            'model': self.anthropic_model,
            'messages': payload_messages,
            'max_tokens': 1200,
            'temperature': 0.2
        }
        if system_prompt:
            body['system'] = system_prompt

        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': self.anthropic_api_key,
                'anthropic-version': '2023-06-01',
                'Content-Type': 'application/json'
            },
            json=body,
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        content_blocks = data.get('content', [])
        content = content_blocks[0].get('text', '') if content_blocks else ''
        return {
            'provider': 'anthropic',
            'content': content,
            'model': self.anthropic_model,
            'usage': data.get('usage')
        }


class WebSearchService:
    """Recherche web basique pour enrichir les réponses IA."""

    def __init__(self):
        self.enabled = os.getenv('AI_WEB_SEARCH_ENABLED', 'false').lower() == 'true'
        self.serpapi_key = os.getenv('SERPAPI_KEY')
        self.timeout = int(os.getenv('AI_WEB_SEARCH_TIMEOUT', '15'))

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if not self.enabled:
            return []

        results = []
        try:
            if self.serpapi_key:
                results = self._search_serpapi(query, max_results)
            else:
                results = self._search_duckduckgo(query, max_results)
        except Exception as e:
            logger.error(f"Erreur recherche web: {str(e)}")

        return results[:max_results]

    def _search_serpapi(self, query: str, max_results: int) -> List[Dict[str, str]]:
        response = requests.get(
            'https://serpapi.com/search.json',
            params={
                'q': query,
                'api_key': self.serpapi_key,
                'num': max_results,
                'hl': 'fr',
                'gl': 'fr'
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get('organic_results', [])[:max_results]:
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', '')
            })
        return results

    def _search_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, str]]:
        response = requests.get(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': 1,
                'skip_disambig': 1
            },
            timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        results = []

        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'FirstURL' in topic:
                results.append({
                    'title': topic.get('Text', '').split(' - ')[0],
                    'url': topic.get('FirstURL', ''),
                    'snippet': topic.get('Text', '')
                })
        return results

    def fetch_page(self, url: str) -> Optional[str]:
        try:
            response = requests.get(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; ERP-IA-Bot/1.0)'
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = soup.get_text(separator='\n')
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines[:120])
        except Exception as e:
            logger.error(f"Erreur fetch page {url}: {str(e)}")
            return None


class AIContextManager:
    """Gestion du contexte conversationnel."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history

    def build_messages(self, conversation: List[Dict[str, Any]], current_prompt: str) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        for msg in conversation[-self.max_history:]:
            role = 'user' if msg.get('role') == 'user' else 'assistant'
            content = msg.get('content', '')
            if content:
                messages.append({'role': role, 'content': content})

        if current_prompt:
            messages.append({'role': 'user', 'content': current_prompt})
        return messages

    def build_system_prompt(self, tenant_name: Optional[str] = None) -> str:
        tenant_label = tenant_name or 'votre entreprise'
        return (
            "Vous êtes l'assistant IA d'un ERP commercial. "
            f"Vous répondez en français, de manière concise et professionnelle. "
            f"Vous vous appuyez sur les données métier du tenant '{tenant_label}', "
            "sur les outils internes du ERP (stocks, ventes, clients, factures, prévisions) "
            "et, si disponible, sur des ressources externes vérifiées. "
            "Si une information incertaine vient d'une source externe, citez-la clairement. "
            "Si une donnée interne est indisponible, dites-le explicitement."
        )


external_ai = ExternalAIService()
web_search = WebSearchService()
context_manager = AIContextManager()
