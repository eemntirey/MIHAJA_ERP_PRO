// src/navigation/RootNavigator.js
// Navigation racine — 4 modules uniquement (Consultation, Vente, Inventaire, Livraison)

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';

import { useAuth } from '../context/AuthContext';
import { colors, spacing, fontSizes } from '../theme';
import HomeScreen from '../screens/HomeScreen';
import VenteScreen from '../screens/VenteScreen';
import InventaireScreen from '../screens/InventaireScreen';
import LivraisonScreen from '../screens/LivraisonScreen';
import LoginScreen from '../screens/LoginScreen';

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const TABS = [
  { name: 'Accueil', component: HomeScreen, icon: 'home', label: 'Consultation' },
  { name: 'Vente', component: VenteScreen, icon: 'cart', label: 'Vente' },
  { name: 'Inventaire', component: InventaireScreen, icon: 'cube', label: 'Inventaire' },
  { name: 'Livraison', component: LivraisonScreen, icon: 'bicycle', label: 'Livraison' },
];

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 64,
          paddingBottom: 8,
          paddingTop: 8,
          elevation: 8,
          shadowColor: colors.text,
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.06,
          shadowRadius: 6,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '600',
          marginTop: 2,
        },
        tabBarIcon: ({ color, size, focused }) => {
          const tab = TABS.find((t) => t.name === route.name);
          const icon = tab?.icon || 'ellipse';
          return (
            <Ionicons name={focused ? icon : `${icon}-outline`} size={24} color={color} style={{ marginBottom: -4 }} />
          );
        },
      })}
    >
      {TABS.map((tab) => (
        <Tab.Screen
          key={tab.name}
          name={tab.name}
          component={tab.component}
          options={{ tabBarLabel: tab.label }}
        />
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
  const { booting, isAuthenticated } = useAuth();

  if (booting) {
    return <BootSplash />;
  }

  return (
    <NavigationContainer>
      <Stack.Navigator screenOptions={{ headerShown: false, animation: 'fade' }}>
        {!isAuthenticated ? (
          <Stack.Screen name="Login" component={LoginScreen} />
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
    width: 80,
    height: 80,
    borderRadius: 24,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 24,
    elevation: 8,
  },
  bootLogoText: {
    color: colors.textInverse,
    fontSize: 32,
    fontWeight: '800',
    letterSpacing: -1,
  },
  bootTitle: {
    fontSize: fontSizes.xl,
    fontWeight: '800',
    color: colors.text,
    letterSpacing: -0.5,
  },
});
