// src/screens/LivraisonScreen.js
// Livraisons : liste + statut + passage au statut suivant.
// GET /livraisons, POST /livraisons/{id}/avancer.

import React, { useCallback, useState } from 'react';
import { Alert, FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';

import { livraisonService } from '../services/services';
import { getErrorMessage, extractList } from '../services/api';
import { Screen, ScreenHeader, Separator } from '../components/Screen';
import { Badge } from '../components/Badge';
import { EmptyState, ErrorBanner, LoadingScreen } from '../components/States';
import { formatDate, formatMoney } from '../utils/format';
import { colors, spacing, fontSizes } from '../theme';

export default function LivraisonScreen() {
  const [livraisons, setLivraisons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await livraisonService.getAll();
      setLivraisons(extractList(data, ['livraisons']));
    } catch (e) {
      setError(getErrorMessage(e, 'Impossible de charger les livraisons.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const avancer = (livraison) => {
    setBusyId(livraison.id);
    livraisonService
      .avancer(livraison.id)
      .then(load)
      .catch((e) => {
        Alert.alert('Livraison', getErrorMessage(e, 'Action impossible.'));
      })
      .finally(() => setBusyId(null));
  };

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.cardTitle} numberOfLines={1}>
          {`Livraison #${item.id}`}
          {item.nom_destinataire ? ` — ${item.nom_destinataire}` : ''}
        </Text>
        <Badge status={item.statut} />
      </View>
      <Text style={styles.meta} numberOfLines={1}>
        {item.adresse_livraison || item.ville_livraison || 'Adresse non renseignée'}
      </Text>
      <View style={styles.cardFooter}>
        <Text style={styles.meta}>
          {item.date_livraison_prevue ? formatDate(item.date_livraison_prevue) : 'Date non planifiée'}
        </Text>
        <Pressable
          onPress={() => avancer(item)}
          disabled={busyId === item.id || item.statut === 'livree'}
          style={({ pressed }) => [
            styles.avancer,
            (busyId === item.id || item.statut === 'livree' || pressed) && { opacity: 0.6 },
          ]}
        >
          <Ionicons name="play" size={14} color={colors.textInverse} style={{ marginRight: 6 }} />
          <Text style={styles.avancerText}>
            {item.statut === 'livree' ? 'Livrée' : 'Avancer'}
          </Text>
        </Pressable>
      </View>
    </View>
  );

  return (
    <Screen>
      <ScreenHeader
        title="Livraison"
        subtitle={`${livraisons.length} livraison(s)`}
      />
      <ErrorBanner message={error} onRetry={load} />
      {loading ? (
        <LoadingScreen label="Chargement des livraisons..." />
      ) : (
        <FlatList
          data={livraisons}
          keyExtractor={(item) => String(item.id)}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <EmptyState
              icon="bicycle-outline"
              title="Aucune livraison"
              subtitle="Les livraisons créées depuis le web apparaîtront ici."
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
  avancer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary,
    borderRadius: 999,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
  },
  avancerText: {
    color: colors.textInverse,
    fontSize: fontSizes.sm,
    fontWeight: '700',
  },
});
