// src/screens/VenteScreen.js
// Ventes : liste des ventes (consultation) — création via le web/desktop.
// GET /ventes → {ventes: [...]} (avec client_nom, type_vente, mode_paiement...).

import React, { useCallback, useState } from 'react';
import { FlatList, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';

import { saleService } from '../services/services';
import { getErrorMessage, extractList } from '../services/api';
import { Screen, ScreenHeader, Separator } from '../components/Screen';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorBanner, LoadingScreen } from '../components/States';
import { formatDate, formatMoney } from '../utils/format';
import { colors, spacing, fontSizes } from '../theme';

const MODE_PAIEMENT_LABELS = {
  especes: 'Espèces',
  virement: 'Virement',
  cheque: 'Chèque',
  mvola: 'MVola',
  orange_money: 'Orange Money',
  airtel_money: 'Airtel Money',
};

const getModePaiementLabel = (mode) =>
  MODE_PAIEMENT_LABELS[mode] || mode || '—';

export default function VenteScreen() {
  const [ventes, setVentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await saleService.getAll();
      setVentes(extractList(data, ['ventes']));
    } catch (e) {
      setError(getErrorMessage(e, 'Impossible de charger les ventes.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {`${item.reference || `Vente #${item.id}`} — ${item.client_nom || 'Client passager'}`}
        </Text>
        <View style={styles.badgeRow}>
          <Badge status={item.type_vente === 'gros' ? 'gros' : 'detail'} />
          <Badge status={item.statut} />
        </View>
      </View>
      <Text style={styles.meta} numberOfLines={1}>
        {formatDate(item.date)}
      </Text>
      <View style={styles.cardFooter}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="cash-outline" size={13} color={colors.textMuted} />
          <Text style={styles.meta} numberOfLines={1}>
            {getModePaiementLabel(item.mode_paiement)}
          </Text>
        </View>
        <Text style={styles.total}>{formatMoney(item.total_ttc)}</Text>
      </View>
    </View>
  );

  return (
    <Screen>
      <ScreenHeader title="Vente" subtitle={`${ventes.length} vente(s)`} />
      <ErrorBanner message={error} onRetry={load} />
      {loading ? (
        <LoadingScreen label="Chargement des ventes..." />
      ) : (
        <FlatList
          data={ventes}
          keyExtractor={(item) => String(item.id)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <EmptyState
              icon="cart-outline"
              title="Aucune vente"
              subtitle="Les ventes créées depuis le web ou le desktop apparaîtront ici."
            />
          }
          renderItem={({ item }) => (
            <View>
              {renderItem({ item })}
              <Separator />
            </View>
          )}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  list: {
    paddingBottom: 32,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.md,
    marginHorizontal: spacing.lg,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardTitle: {
    flex: 1,
    marginRight: spacing.sm,
    fontSize: fontSizes.sm,
    fontWeight: '700',
    color: colors.text,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  meta: {
    fontSize: fontSizes.xs,
    color: colors.textMuted,
    marginTop: 4,
  },
  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: spacing.sm,
  },
  total: {
    fontSize: fontSizes.sm,
    fontWeight: '800',
    color: colors.text,
  },
});