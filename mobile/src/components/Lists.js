// mobile/src/components/Lists.js
// Listes réutilisables de l'accueil : top produits et alertes stock.

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Card } from './Card';
import { Badge } from './Badge';
import { EmptyState } from './States';
import { Screen, Separator } from './Screen';
import { colors, spacing, fontSizes } from '../theme';
import { formatMoney, formatNumber } from '../utils/format';

export const stockStatus = (p) =>
  Number(p?.quantite_stock) <= 0
    ? 'rupture'
    : p?.est_alerte_stock
      ? 'stock_bas'
      : 'en_stock';

export function TopProductsCard({ items }) {
  return (
    <Card style={{ paddingVertical: 4 }}>
      {items.length === 0 ? (
        <EmptyState icon="podium-outline" title="Aucune vente ce mois" />
      ) : items.map((p, index) => (
        <View key={String(p.produit_id ?? index)}>
          {index > 0 ? <Separator /> : null}
          <View style={styles.listRow}>
            <View style={styles.rank}>
              <Text style={styles.rankText}>{index + 1}</Text>
            </View>
            <View style={{ flex: 1, marginRight: spacing.md }}>
              <Text style={styles.name} numberOfLines={1}>
                {p.nom || `Produit #${p.produit_id}`}
              </Text>
              <Text style={styles.meta}>
                {formatNumber(p.total_quantite)} unité(s) vendue(s)
              </Text>
            </View>
            <Text style={styles.ca}>
              {formatMoney(p.total_ca ?? p.total_ttc)}
            </Text>
          </View>
        </View>
      ))}
    </Card>
  );
}

export function AlertsCard({ items }) {
  return (
    <Card style={{ paddingVertical: 4 }}>
      {items.length === 0 ? (
        <EmptyState icon="checkmark-circle-outline" title="Aucune alerte" />
      ) : items.map((p, index) => (
        <View key={String(p.id ?? index)}>
          {index > 0 ? <Separator /> : null}
          <View style={styles.listRow}>
            <View style={{ flex: 1, marginRight: spacing.md }}>
              <Text style={styles.name} numberOfLines={1}>{p.nom}</Text>
              <Text style={styles.meta}>
                Stock {formatNumber(p.quantite_stock)} / seuil{' '}
                {formatNumber(p.seuil_alerte)}
              </Text>
            </View>
            <Badge status={stockStatus(p)} />
          </View>
        </View>
      ))}
    </Card>
  );
}

export function ProductRow({ p }) {
  return (
    <View style={styles.listRow}>
      <View style={{ flex: 1, marginRight: spacing.md }}>
        <Text style={styles.name} numberOfLines={1}>{p.nom}</Text>
        <Text style={styles.meta} numberOfLines={1}>
          {[p.reference, p.categorie].filter(Boolean).join(' • ') || '—'}
        </Text>
      </View>
      <View style={{ alignItems: 'flex-end' }}>
        <Text style={styles.ca}>
          {formatMoney(p.prix_vente_ttc ?? p.prix_vente_ht)}
        </Text>
        <Badge status={stockStatus(p)} />
      </View>
    </View>
  );
}

export function SectionTitle({ children }) {
  return (
    <Screen>
      <Text style={styles.sectionTitle}>{children}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  listRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  rank: {
    width: 26,
    height: 26,
    borderRadius: 999,
    backgroundColor: colors.primarySoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
  },
  rankText: { fontSize: fontSizes.xs, fontWeight: '800', color: colors.primary },
  name: { fontSize: fontSizes.sm, fontWeight: '600', color: colors.text },
  meta: { fontSize: fontSizes.xs, color: colors.textMuted, marginTop: 2 },
  ca: { fontSize: fontSizes.xs, fontWeight: '700', color: colors.text },
  sectionTitle: {
    fontSize: fontSizes.xs,
    fontWeight: '700',
    color: colors.textMuted,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
});
