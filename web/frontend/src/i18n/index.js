// web/frontend/src/i18n/index.js
// Point d'entrée de l'i18n léger (FR / MG).
export { translations } from './translations';

export {
  DEFAULT_LANGUAGE,
  FR_CODE,
  LANGUAGES,
  MG_CODE,
  SUPPORTED_LANGUAGES,
} from './translations';

export { LanguageContext, LanguageProvider, useTranslation } from './LanguageContext';