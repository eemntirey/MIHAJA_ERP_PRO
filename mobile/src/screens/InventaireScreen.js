// src/screens/InventaireScreen.js
// Inventaire : liste des produits avec statut de stock, recherche locale.
// GET /stocks → {stocks: [produits avec statut stock]}.

import React, { useCallback, useMemo, useState } from 'react';
import { FlatList, StyleSheet, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';

import { stockService } from '../services/services';
import { getErrorMessage, extractList } from '../services/api';
import { Screen, ScreenHeader, Separator } from '../components/Screen';
import { SearchBar } from '../components/Form';
import { ProductRow } from '../components/Lists';
import { EmptyState, ErrorBanner, LoadingScreen } from '../components/States';

export default function InventaireScreen() {
  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await stockService.getAll();
      setStocks(extractList(data, ['stocks']));
    } catch (e) {
      setError(getErrorMessage(e, 'Impossible de charger le stock.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return stocks;
    return stocks.filter((p) =>
      ['nom', 'reference', 'categorie'].some((key) =>
        String(p[key] || '').toLowerCase().includes(term)
      )
    );
  }, [stocks, search]);

  return (
    <Screen>
      <ScreenHeader
        title="Inventaire"
        subtitle={`${stocks.length} produit(s) en stock`}
      />
      <SearchBar
        value={search}
        onChangeText={setSearch}
        placeholder="Rechercher un produit, une référence..."
      />
      <ErrorBanner message={error} onRetry={load} />
      {loading ? (
        <LoadingScreen label="Chargement du stock..." />
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => String(item.id)}
          keyboardShouldPersistTaps="handled"
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <EmptyState
              icon="cube-outline"
              title="Aucun produit"
              subtitle={search ? 'Aucun résultat pour cette recherche.' : 'Le stock est vide.'}
            />
          }
          renderItem={({ item }) => (
            <View>
              <ProductRow p={item} />
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
});
