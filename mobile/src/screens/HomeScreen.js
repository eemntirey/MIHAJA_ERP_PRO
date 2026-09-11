// src/screens/HomeScreen.js
// Consultation : statistiques du mois, top produits, alertes stock.
// GET /dashboard, /dashboard/top-products, /dashboard/alerts.

import React, { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

import { dashboardService } from '../services/services';
import { getErrorMessage, extractList } from '../services/api';
import { Screen, ScreenHeader } from '../components/Screen';
import { StatCard } from '../components/Card';
import { TopProductsCard, AlertsCard } from '../components/Lists';
import { ErrorBanner, LoadingScreen } from '../components/States';
import { formatMoney } from '../utils/format';
import { colors } from '../theme';

export default function HomeScreen() {
  const [stats, setStats] = useState(null);
  const [topProducts, setTopProducts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [statsRes, topRes, alertsRes] = await Promise.all([
        dashboardService.getStats(),
        dashboardService.getTopProducts(),
        dashboardService.getAlerts(),
      ]);
      setStats(statsRes.data?.stats || null);
      setTopProducts(extractList(topRes.data, ['top_products']));
      setAlerts(extractList(alertsRes.data, ['alertes_stock']));
    } catch (e) {
      setError(getErrorMessage(e, 'Impossible de charger les données.'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Recharge à chaque affichage de l'onglet (données toujours fraîches).
  useFocusEffect(useCallback(() => { load(); }, [load]));

  if (loading) {
    return (
      <Screen>
        <ScreenHeader title="Accueil" subtitle="Consultation" />
        <LoadingScreen label="Chargement des statistiques..." />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title="Accueil" subtitle="Consultation" />
      <ErrorBanner message={error} onRetry={() => load()} />
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />
        }
      >
        <View style={styles.statRow}>
          <StatCard
            icon="trending-up"
            label="CA du mois"
            value={formatMoney(stats?.ca_mois)}
            tone="primary"
          />
          <StatCard
            icon="cart"
            label="Ventes aujourd'hui"
            value={formatNumber(stats?.ventes_aujourdhui)}
            tone="info"
          />
        </View>
        <View style={styles.statRow}>
          <StatCard
            icon="wallet"
            label="Bénéfice du mois"
            value={formatMoney(stats?.benefice_mois)}
            tone="success"
          />
          <StatCard
            icon="alert-circle"
            label="Alertes stock"
            value={formatNumber(stats?.alertes_stock)}
            tone={Number(stats?.alertes_stock) > 0 ? 'danger' : 'success'}
          />
        </View>

        <AlertsCard items={alerts} />

        <TopProductsCard items={topProducts} />
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: colors.md ? 16 : 16,
    paddingBottom: 32,
  },
  statRow: {
    flexDirection: 'row',
    marginBottom: 12,
  },
});
