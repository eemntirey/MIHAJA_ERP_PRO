// src/components/Buttons.js
// Boutons de l'application (variantes primary / secondary / success / danger).

import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { colors, spacing, radius, fontSizes } from '../theme';

export function PrimaryButton({
  title,
  onPress,
  disabled,
  loading,
  variant = 'primary',
  icon,
  style,
}) {
  const palette = {
    primary: { bg: colors.primary, fg: colors.textInverse },
    secondary: { bg: colors.surfaceActive, fg: colors.text },
    danger: { bg: colors.danger, fg: colors.textInverse },
    success: { bg: colors.success, fg: colors.textInverse },
  }[variant];

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: palette.bg, opacity: disabled ? 0.5 : pressed ? 0.85 : 1 },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={palette.fg} size="small" />
      ) : (
        <View style={styles.row}>
          {icon ? (
            <Ionicons name={icon} size={17} color={palette.fg} style={{ marginRight: spacing.sm }} />
          ) : null}
          <Text style={[styles.text, { color: palette.fg }]}>{title}</Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 46,
    borderRadius: radius.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  text: {
    fontSize: fontSizes.md,
    fontWeight: '700',
  },
});
