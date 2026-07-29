import type { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '@/theme/tokens';

interface RecordCardProps {
  title: string;
  meta: string;
  body: string;
  badge?: ReactNode;
}

export function RecordCard({ title, meta, body, badge }: RecordCardProps) {
  return (
    <Pressable style={({ pressed }) => [styles.card, pressed && styles.pressed]}>
      <View style={styles.heading}>
        <Text style={styles.title}>{title}</Text>
        {badge}
      </View>
      <Text style={styles.meta}>{meta}</Text>
      <Text style={styles.body}>{body}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderColor: colors.sand300,
    borderRadius: radii.md,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.md,
  },
  pressed: {
    opacity: 0.72,
  },
  heading: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing.sm,
    justifyContent: 'space-between',
  },
  title: {
    color: colors.ink900,
    flex: 1,
    fontSize: typography.heading,
    fontWeight: '700',
  },
  meta: {
    color: colors.forest500,
    fontSize: typography.caption,
    fontWeight: '700',
  },
  body: {
    color: colors.ink600,
    fontSize: typography.body,
    lineHeight: 22,
  },
});
