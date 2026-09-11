// src/components/Badge.js
// Badge de statut — mappings des statuts backend (ventes, livraisons, stocks).

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, fontSizes } from '../theme';

const STATUS_STYLES = {
  // Ventes
  devis: { label: 'Devis', bg: colors.infoBg, fg: colors.info },
  en_attente: { label: 'En attente', bg: colors.warningBg, fg: colors.warning },
  payee: { label: 'Payée', bg: colors.successBg, fg: colors.success },
  annulee: { label: 'Annulée', bg: colors.dangerBg, fg: colors.danger },
  // Livraisons
  chargee: { label: 'Chargée', bg: colors.infoBg, fg: colors.info },
  en_route: { label: 'En route', bg: `${colors.accent}1A`, fg: colors.accent },
  livree: { label: 'Livrée', bg: colors.successBg, fg: colors.success },
  retournee: { label: 'Retournée', bg: colors.neutralBg, fg: colors.neutral },
  echec: { label: 'Échec', bg: colors.dangerBg, fg: colors.danger },
  // Stocks
  rupture: { label: 'Rupture', bg: colors.dangerBg, fg: colors.danger },
  stock_bas: { label: 'Stock bas', bg: colors.warningBg, fg: colors.warning },
  en_stock: { label: 'En stock', bg: colors.successBg, fg: colors.success },
};

export function Badge({ status, customLabel, bg, fg }) {
  const s = STATUS_STYLES[status] || {
    label: customLabel || status || '—',
    bg: colors.neutralBg,
    fg: colors.neutral,
  };
  return (
    <View style={[styles.badge, { backgroundColor: bg || s.bg }]}>
      <Text style={[styles.badgeText, { color: fg || s.fg }]}>
        {customLabel || s.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
  },
  badgeText: {
    fontSize: fontSizes.xs,
    fontWeight: '600',
  },
});
