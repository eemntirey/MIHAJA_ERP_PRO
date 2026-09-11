// src/screens/auth/ChangePasswordScreen.js
// Changement OBLIGATOIRE de mot de passe (première connexion avec un
// mot de passe temporaire). POST /auth/first-login-change.
// L'écran ne peut pas être contourné : RootNavigator n'affiche les onglets
// qu'une fois must_change_password = false.

import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { useAuth } from '../../context/AuthContext';
import { authService } from '../../services/services';
import { getErrorMessage } from '../../services/api';
import { Field, TextInput_ } from '../../components/Form';
import { PrimaryButton } from '../../components/Buttons';
import { ErrorBanner } from '../../components/States';
import { Screen, ScreenHeader } from '../../components/Screen';
import { PrimaryButton as Button } from '../../components/Buttons';
import { colors, spacing, radius, fontSizes } from '../../theme';

export default function ChangePasswordScreen() {
  const { user, updateUser, setMustChangePassword } = useAuth();
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async () => {
    setError(null);

    if (!password || password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.');
      return;
    }
    if (!/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password)) {
      setError('Ajoutez au moins une majuscule, une minuscule et un chiffre.');
      return;
    }
    if (password !== confirm) {
      setError('Les mots de passe ne correspondent pas.');
      return;
    }

    setLoading(true);
    try {
      await authService.firstChangePassword(password);
      Alert.alert('Succès', 'Mot de passe défini avec succès.');
      setMustChangePassword(false);
      if (user) {
        await updateUser({ ...user, must_change_password: false });
      }
    } catch (e) {
      setError(
        getErrorMessage(e, 'Erreur lors du changement de mot de passe.')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Screen edges={['top', 'left', 'right', 'bottom']}>
      <ScreenHeader title="Nouveau mot de passe" />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.notice}>
            <Ionicons name="lock-closed" size={19} color={colors.info} />
            <Text style={styles.noticeText}>
              {user?.email || 'Votre compte'} utilise un mot de passe temporaire.
              Vous devez en définir un nouveau pour accéder à l'application.
            </Text>
          </View>

          <ErrorBanner message={error} />

          <Field label="Nouveau mot de passe">
            <TextInput_
              value={password}
              onChangeText={setPassword}
              placeholder="8+ caractères, majuscule, minuscule, chiffre"
              secureTextEntry
              autoCapitalize="none"
              textContentType="newPassword"
            />
          </Field>

          <Field label="Confirmation">
            <TextInput_
              value={confirm}
              onChangeText={setConfirm}
              placeholder="Ressaisissez le mot de passe"
              secureTextEntry
              autoCapitalize="none"
              textContentType="newPassword"
            />
          </Field>

          <Button
            title="Définir le mot de passe"
            icon="checkmark-circle-outline"
            onPress={onSubmit}
            loading={loading}
            style={styles.submit}
          />
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: spacing.lg,
  },
  notice: {
    flexDirection: 'row',
    backgroundColor: colors.infoBg,
    borderRadius: radius.sm,
    padding: spacing.md,
    marginBottom: spacing.lg,
  },
  noticeText: {
    flex: 1,
    marginLeft: spacing.sm,
    fontSize: fontSizes.sm,
    color: colors.info,
  },
  submit: {
    marginTop: spacing.sm,
  },
});
