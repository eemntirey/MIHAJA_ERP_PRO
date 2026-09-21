// src/config/env.js
// Configuration d'environnement. Les variables EXPO_PUBLIC_* sont inlinées
// dans le bundle au démarrage (fichier mobile/.env, voir .env.example).
//
// L'URL du backend est résolue par plateforme (voir ./resolveApiUrl.js) : le
// même mobile/.env sert ainsi l'émulateur Android, le navigateur (Expo web sur
// le port 8081) et l'appareil physique (IP LAN / tunnel).

import { Platform } from 'react-native';
import Constants from 'expo-constants';

import {
  DEFAULT_API_PORT,
  hostFromHostUri,
  isLocalApiUrl,
  resolveApiBaseUrl,
  resolveApiPort,
  resolveFallbackApiBaseUrl,
} from './resolveApiUrl';

const RAW_API_URL = process.env.EXPO_PUBLIC_API_URL || '';
const API_PORT = resolveApiPort(process.env.EXPO_PUBLIC_API_PORT, DEFAULT_API_PORT);

// URL utilisée telle quelle (sans réécriture par plateforme) : utile pour
// `adb reverse` (appareil USB → http://localhost:5000/api/v1) ou un cas exotique.
const STRICT = /^(1|true|yes|on)$/i.test((process.env.EXPO_PUBLIC_API_URL_STRICT || '').trim());

// Hôte de la page courante sur le web (localhost:8081, 192.168.x.y:8081, tunnel).
const WEB_HOSTNAME =
  typeof window !== 'undefined' && window.location ? window.location.hostname : '';

// Hôte du serveur de dev Expo (celui qui a servi le bundle) : en Expo Go sur un
// appareil physique c'est l'IP LAN du PC, ex. '192.168.89.120:8081'.
const DEV_SERVER_HOST = hostFromHostUri(
  (Constants.expoConfig && Constants.expoConfig.hostUri) ||
    (Constants.expoGoConfig && Constants.expoGoConfig.debuggerHost) ||
    (Constants.manifest2 &&
      Constants.manifest2.extra &&
      Constants.manifest2.extra.expoGo &&
      Constants.manifest2.extra.expoGo.debuggerHost) ||
    ''
);

// URL de l'API backend Flask, sans slash final.
export const API_BASE_URL =
  STRICT && RAW_API_URL
    ? RAW_API_URL.trim().replace(/\/+$/, '')
    : resolveApiBaseUrl(RAW_API_URL, Platform.OS, WEB_HOSTNAME, API_PORT);

// URL de secours : déduite de l'hôte du serveur de dev (IP LAN déjà joignable
// par le téléphone). Utilisée automatiquement si API_BASE_URL ne répond pas —
// c'est le cas d'un appareil physique alors que .env cible 10.0.2.2 (émulateur).
export const API_FALLBACK_URL =
  STRICT || Platform.OS === 'web'
    ? ''
    : resolveFallbackApiBaseUrl(API_BASE_URL, DEV_SERVER_HOST, API_PORT);

// Diagnostic : URL dérivée de la plateforme (dev local) ou explicite (LAN/prod).
export const API_URL_IS_DERIVED = !RAW_API_URL || isLocalApiUrl(RAW_API_URL);
export const API_PLATFORM = Platform.OS;
export const API_DEV_SERVER_HOST = DEV_SERVER_HOST;

export const APP_NAME = 'ERP PRO';
export const APP_VERSION = '1.0.0';
