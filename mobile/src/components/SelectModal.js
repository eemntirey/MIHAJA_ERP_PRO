// src/components/SelectModal.js
// Modale plein écran de sélection générique (client, produit, statut...)
// avec recherche locale.

import React, { useEffect, useState } from 'react';
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { SearchBar } from './Form';
import { EmptyState } from './States';
import { colors, spacing, fontSizes } from '../theme';

export function SelectModal({
  visible,
  title,
  items,
  onClose,
  onSelect,
  searchKeys = ['nom'],
  renderItem,
  keyExtractor = (item) => String(item.id),
}) {
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (visible) setSearch('');
  }, [visible]);

  const filtered = items.filter((item) =>
    searchKeys.some((key) =>
      String(item[key] || '').toLowerCase().includes(search.toLowerCase())
    )
  );

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <Text style={styles.title}>{title}</Text>
          <Pressable onPress={onClose}>
            <Ionicons name="close" size={22} color={colors.text} />
          </Pressable>
        </View>
        <SearchBar
          value={search}
          onChangeText={setSearch}
          placeholder="Rechercher..."
        />
        <FlatList
          data={filtered}
          keyExtractor={keyExtractor}
          keyboardShouldPersistTaps="handled"
          ListEmptyComponent={
            <EmptyState icon="search-outline" title="Aucun résultat" />
          }
          renderItem={({ item }) => (
            <Pressable
              style={({ pressed }) => [
                styles.modalItem,
                pressed && { backgroundColor: colors.background },
              ]}
              onPress={() => onSelect(item)}
            >
              {renderItem ? (
                renderItem(item)
              ) : (
                <Text style={styles.modalItemText}>
                  {item.nom || item.label || String(item)}
                </Text>
              )}
            </Pressable>
          )}
        />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  modalContainer: {
    flex: 1,
    backgroundColor: colors.background,
    paddingTop: 12,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
  title: {
    fontSize: fontSizes.xl,
    fontWeight: '700',
    color: colors.text,
  },
  modalItem: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  modalItemText: {
    fontSize: fontSizes.md,
    color: colors.text,
  },
});
