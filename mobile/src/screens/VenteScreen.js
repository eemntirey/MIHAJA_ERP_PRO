// src/screens/VenteScreen.js
// Ventes : liste des ventes et actions rapides.

import React from 'react';
import { StyleSheet, View, Text } from 'react-native';
import { Screen, ScreenHeader } from '../components/Screen';
import { colors } from '../theme';

export default function VenteScreen() {
  return (
    <Screen>
      <ScreenHeader title="Vente" subtitle="Point de vente" />
      <View style={styles.content}>
        <Text style={styles.text}>Écran Vente (point de vente) - en cours de développement.</Text>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 16,
  },
  text: {
    color: colors.text,
    fontSize: 14,
  },
});
