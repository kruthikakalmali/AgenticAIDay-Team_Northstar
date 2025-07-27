import { Ionicons } from '@expo/vector-icons';
import { Stack, usePathname, useRouter } from 'expo-router';
import React, { memo, useEffect, useRef } from 'react';
import { Animated, Pressable, SafeAreaView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

// Theme constants
const COLORS = {
  background: '#222531',
  surface: '#2E303E',
  accent: '#FF6B6B',
  text: '#FFFFFF',
};

// Tabs configuration
const TAB_ITEMS = [
  { route: '/map-component', icon: 'map-outline', iconActive: 'map', label: 'Map Dashboard' },
  { route: '/', icon: 'list-outline', iconActive: 'list', label: 'Feed' },
  { route: '/report', icon: 'document-text-outline', iconActive: 'document-text', label: 'Report Incident' },
];

// Animated header title component
function AnimatedTitle({ title }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(-10)).current;

  useEffect(() => {
    opacity.setValue(0);
    translateY.setValue(-10);
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 300, useNativeDriver: true }),
      Animated.timing(translateY, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start();
  }, [title]);

  return (
    <Animated.Text style={[styles.headerTitle, { opacity, transform: [{ translateY }] }]}>  
      {title}
    </Animated.Text>
  );
}

// Footer icons as tabs with press feedback
function IconTab({ route, icon, iconActive, onPress, active }) {
  const color = active ? COLORS.accent : COLORS.text;
  const name = active ? iconActive : icon;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.tabButton,
        pressed && styles.tabButtonPressed
      ]}
      android_ripple={{ color: COLORS.accent, radius: 24 }}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
    >
      <Ionicons name={name} size={28} color={color} />
    </Pressable>
  );
}

function RootLayout() {
  const router = useRouter();
  const pathname = usePathname();
  const insets = useSafeAreaInsets();

  return (
    <SafeAreaView style={[styles.container, { paddingBottom: insets.bottom }]}>      
      <Stack
        screenOptions={({ route }) => {
          const path = route.name === 'index' ? '/' : `/${route.name}`;
          const tab = TAB_ITEMS.find(item => item.route === path);
          const title = tab?.label || '';

          return {
            headerStyle: styles.header,
            headerShadowVisible: false,
            headerTintColor: COLORS.text,
            headerTitleAlign: 'center',
            headerTitle: () => <AnimatedTitle title={title} />,  
            headerBackVisible: true,
            headerBackTitleVisible: false,
            headerBackImage: ({ tintColor }) => <Ionicons name="chevron-back" size={24} color={tintColor} />,          
            contentStyle: { backgroundColor: COLORS.surface },
          };
        }}
      />

      <View style={styles.tabBar}>
        {TAB_ITEMS.map(({ route, icon, iconActive }) => (
          <IconTab
            key={route}
            route={route}
            icon={icon}
            iconActive={iconActive}
            active={pathname === route}
            onPress={() => router.replace(route)}
          />
        ))}
      </View>
    </SafeAreaView>
  );
}

export default memo(RootLayout);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    backgroundColor: COLORS.background,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '600',
    letterSpacing: 0.5,
    color: COLORS.text,
  },
  tabBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingVertical: 12,
    backgroundColor: COLORS.surface,
    borderTopWidth: 1,
    borderTopColor: COLORS.background,
  },
  tabButton: {
    flex: 1,
    alignItems: 'center',
  },
  tabButtonPressed: {
    opacity: 0.6,
  },
});
