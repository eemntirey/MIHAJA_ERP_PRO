// src/screens/auth/LoginScreen.js
// Écran de connexion : identifiant (email ou username) + mot de passe.
// Authentification JWT via POST /auth/login (même backend que web/desktop).

import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useAuth } from '../../context/AuthContext';
import { getErrorMessage } from '../../services/api';
import { Field, TextInput_ } from '../../components/Form';
import { PrimaryButton } from '../../components/Buttons';
import { ErrorBanner } from '../../components/States';
import { Screen } from '../../components/Screen';
import { colors, spacing, radius, fontSizes } from '../../theme';
import { APP_NAME, APP_VERSION } from '../../config/env';

export default function LoginScreen() {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    if (!identifier.trim() || !password) {
      setError('Veuillez saisir votre identifiant et votre mot de passe.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await login(identifier.trim(), password);
    } catch (e) {
      setError(
        getErrorMessage(
          e,
          'Erreur de connexion. Vérifiez vos identifiants et votre connexion.'
        )
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen edges={['top', 'left', 'right', 'bottom']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.logoBlock}>
            <View style={styles.logo}>
              <Ionicons name="business" size={30} color="#FFFFFF" />
            </View>
            <Text style={styles.appName}>{APP_NAME}</Text>
            <Text style={styles.appSubtitle}>Gestion commerciale — mobile</Text>
          </View>

          <View style={styles.card}>
            <ErrorBanner message={error} />

            <Field label="Email ou nom d'utilisateur">
              <TextInput_
                value={identifier}
                onChangeText={setIdentifier}
                placeholder="ex. distrifood@erp.com"
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                textContentType="username"
              />
            </Field>

            <Field label="Mot de passe">
              <View style={styles.passwordRow}>
                <TextInput_
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Votre mot de passe"
                  secureTextEntry={!showPassword}
                  textContentType="password"
                  style={styles.passwordInput}
                />
                <Pressable
                  onPress={() => setShowPassword((v) => !v)}
                  style={styles.passwordToggle}
                >
                  <Ionicons
                    name={showPassword ? 'eye-off' : 'eye'}
                    size={19}
                    color={colors.textMuted}
                  />
                </Pressable>
              </View>
            </Field>

            <PrimaryButton
              title="Se connecter"
              icon="log-in-outline"
              onPress={onSubmit}
              loading={loading}
              style={styles.submit}
            />
          </View>

          <Pressable
            onPress={() =>
              Alert.alert(
                APP_NAME,
                'Seuls les comptes ERP existants peuvent se connecter. Créez vos comptes depuis le web ou le desktop.'
              )
            }
          >
            <Text style={styles.footer}>Version {APP_VERSION}</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: spacing.xl,
  },
  logoBlock: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  logo: {
    width: 64,
    height: 64,
    borderRadius: radius.lg,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.md,
  },
  appName: {
    fontSize: fontSizes.xxl,
    fontWeight: '800',
    color: colors.text,
  },
  appSubtitle: {
    fontSize: fontSizes.sm,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: spacing.lg,
    shadowColor: '#0F172A',
    shadowOpacity: 0.06,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  passwordRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.inputBg,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.sm,
  },
  passwordInput: {
    flex: 1,
    borderWidth: 0,
    backgroundColor: 'transparent',
    minHeight: 46,
  },
  passwordToggle: {
    paddingHorizontal: spacing.md,
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  submit: {
    marginTop: spacing.sm,
  },
  footer: {
    textAlign: 'center',
    marginTop: spacing.lg,
    fontSize: fontSizes.xs,
    color: colors.textMuted,
  },
});
