// src/config/env.js
// Configuration d'environnement. Les variables EXPO_PUBLIC_* sont inlinées
// dans le bundle au démarrage (fichier mobile/.env, voir .env.example).

const RAW_API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://10.0.2.2:5000/api/v1';

// URL de l'API backend Flask, sans slash final.
export const API_BASE_URL = RAW_API_URL.replace(/\/+$/, '');

export const APP_NAME = 'ERP PRO';
export const APP_VERSION = '1.0.0';
