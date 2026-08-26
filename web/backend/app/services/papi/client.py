
import json
import logging
from typing import Dict, Any, Optional

import requests

from app.services.papi.errors import (
    PapiError,
    PapiAuthError,
    PapiValidationError,
    PapiUnavailableError,
)

logger = logging.getLogger(__name__)


class PapiClient:
    """HTTP client for Papi payment gateway API."""

    def __init__(self, api_url: str, api_key: str, environment: str = 'sandbox'):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.environment = environment

    def _headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'Token': self.api_key,
        }

    def create_payment_link(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a payment link via Papi API.

        Args:
            payload: Payment creation payload matching Papi spec.

        Returns:
            The 'data' object from Papi response containing paymentLink,
            notificationToken, paymentReference, etc.

        Raises:
            PapiAuthError: If API key is invalid (401/403).
            PapiValidationError: If payload is invalid (400).
            PapiUnavailableError: If API is unreachable.
            PapiError: For other errors.
        """
        url = self.api_url
        logger.info(
            'Creating Papi payment link for reference=%s amount=%s',
            payload.get('reference'),
            payload.get('amount'),
        )

        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
        except requests.ConnectionError as exc:
            logger.error('Papi API connection error: %s', exc)
            raise PapiUnavailableError('Papi API est indisponible') from exc
        except requests.Timeout as exc:
            logger.error('Papi API timeout: %s', exc)
            raise PapiUnavailableError('Papi API a mis trop de temps à répondre') from exc
        except requests.RequestException as exc:
            logger.error('Papi API request error: %s', exc)
            raise PapiUnavailableError('Erreur de communication avec Papi') from exc

        if response.status_code in (401, 403):
            logger.error('Papi authentication failed: %s', response.text)
            raise PapiAuthError('Clé API Papi invalide')

        if response.status_code == 400:
            try:
                error_data = response.json()
                message = error_data.get('error', {}).get('message', 'Requête invalide')
            except Exception:
                message = response.text or 'Requête invalide'
            logger.error('Papi validation error: %s', message)
            raise PapiValidationError(message)

        if response.status_code != 200:
            logger.error('Papi unexpected status %s: %s', response.status_code, response.text)
            raise PapiError(f"Papi a retourné le statut {response.status_code}")

        try:
            result = response.json()
        except ValueError as exc:
            logger.error('Papi invalid JSON response: %s', exc)
            raise PapiError('Réponse invalide de Papi') from exc

        data = result.get('data')
        if not data:
            logger.error('Papi response missing data: %s', result)
            raise PapiError('Réponse de Papi incomplète')

        logger.info(
            'Papi payment link created: paymentReference=%s paymentLink=%s',
            data.get('paymentReference'),
            data.get('paymentLink'),
        )
        return data
