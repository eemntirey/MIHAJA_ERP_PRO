// web/frontend/src/i18n/__tests__/translations.test.js
// Garde-fous du dictionnaire i18n : parité FR/MG, couverture de la navigation
// (source unique navConfig) et absence de valeurs vides.
// NB : les clés contiennent des points ('nav./dashboard') — les dictionnaires
// sont plats, on indexe donc directement avec les clés exactes.

import {
  translations,
  LANGUAGES,
  SUPPORTED_LANGUAGES,
  DEFAULT_LANGUAGE,
  FR_CODE,
  MG_CODE,
} from '../translations';
import { NAV_ITEMS, NAV_GROUPS } from '@shared/navConfig';

describe('i18n translations', () => {
  it('expose exactement les langues supportées FR et MG', () => {
    expect(SUPPORTED_LANGUAGES).toEqual(expect.arrayContaining([FR_CODE, MG_CODE]));
    expect(SUPPORTED_LANGUAGES).toHaveLength(2);
    expect(DEFAULT_LANGUAGE).toBe(FR_CODE);
    expect(LANGUAGES).toHaveLength(SUPPORTED_LANGUAGES.length);
    LANGUAGES.forEach((lang) => {
      expect(lang.code).toBeTruthy();
      expect(lang.label).toBeTruthy();
      expect(lang.short).toBeTruthy();
    });
  });

  it('couvre exactement les mêmes clés dans chaque langue (fr <=> mg)', () => {
    const frKeys = Object.keys(translations.fr).sort();
    SUPPORTED_LANGUAGES.forEach((code) => {
      expect(Object.keys(translations[code]).sort()).toEqual(frKeys);
    });
  });

  it("n'a aucune valeur vide", () => {
    SUPPORTED_LANGUAGES.forEach((code) => {
      Object.entries(translations[code]).forEach(([key, value]) => {
        expect(typeof value).toBe('string');
        expect(value.trim().length).toBeGreaterThan(0);
      });
    });
  });

  it('traduit chaque item de navigation (par chemin) dans chaque langue', () => {
    SUPPORTED_LANGUAGES.forEach((code) => {
      NAV_ITEMS.forEach((item) => {
        expect(typeof translations[code][`nav.${item.path}`]).toBe('string');
      });
    });
  });

  it('traduit chaque groupe de navigation dans chaque langue', () => {
    SUPPORTED_LANGUAGES.forEach((code) => {
      NAV_GROUPS.forEach((group) => {
        expect(typeof translations[code][`navGroup.${group}`]).toBe('string');
      });
    });
  });
});