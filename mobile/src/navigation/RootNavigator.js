// src/navigation/RootNavigator.js
// Navigation racine :
// - booting      → écran de démarrage (restauration de session)
// - déconnecté   → Login (ou Changement de mot de passe obligatoire)
// - connecté     → onglets : Accueil, Vente, Inventaire, Livraison, Réglages

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import { useAuth } from '../context/AuthContext';
import { colors, spacing, fontSizes } from '../theme';
import LoginScreen from '../screens/auth/LoginScreen';
import ChangePasswordScreen from '../screens/auth/ChangePasswordScreen';
import HomeScreen from '../screens/HomeScreen';
import VenteScreen from '../screens/VenteScreen';
import InventaireScreen from '../screens/InventaireScreen';
import LivraisonScreen from '../screens/LivraisonScreen';
import SettingsScreen from '../screens/SettingsScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const TABS = [
  { name: 'Accueil', component: HomeScreen, icon: 'home' },
  { name: 'Vente', component: VenteScreen, icon: 'cart' },
  { name: 'Inventaire', component: InventaireScreen, icon: 'cube' },
  { name: 'Livraison', component: LivraisonScreen, icon: 'bicycle' },
  { name: 'Réglages', component: SettingsScreen, icon: 'settings' },
];

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: { backgroundColor: colors.surface, paddingBottom: 4 },
        tabBarIcon: ({ color, size, focused }) => {
          const tab = TABS.find((t) => t.name === route.name);
          const icon = tab?.icon || 'ellipse';
          return (
            <Ionicons name={focused ? icon : `${icon}-outline`} size={size} color={color} />
          );
        },
      })}
    >
      {TABS.map((tab) => (
        <Tab.Screen key={tab.name} name={tab.name} component={tab.component} />
      ))}
    </Tab.Navigator>
  );
}

function BootSplash() {
  return (
    <View style={styles.boot}>
      <View style={styles.bootLogo}>
        <Text style={styles.bootLogoText}>EP</Text>
      </View>
      <Text style={styles.bootTitle}>ERP PRO</Text>
    </View>
  );
}

export default function RootNavigator() {
  const { booting, isAuthenticated, mustChangePassword } = useAuth();

  if (booting) {
    return <BootSplash />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        {!isAuthenticated ? (
          mustChangePassword ? (
            <Stack.Screen name="ChangePassword" component={ChangePasswordScreen} />
          ) : (
            <Stack.Screen name="Login" component={LoginScreen} />
          )
        ) : (
          <Stack.Screen name="Main" component={MainTabs} />
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  bootLogo: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  bootLogoText: {
    color: '#FFFFFF',
    fontSize: fontSizes.xxl,
    fontWeight: '800',
  },
  bootTitle: {
    fontSize: fontSizes.lg,
    fontWeight: '700',
    color: colors.text,
  },
});
