import { MaterialIcons } from "@expo/vector-icons";
import * as Location from "expo-location";
import React, { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Dimensions,
  FlatList,
  LayoutAnimation,
  Linking,
  Platform,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  UIManager,
  View,
} from "react-native";
import {
  GestureHandlerRootView,
  PanGestureHandler,
  State,
} from "react-native-gesture-handler";

// Theme constants
const COLORS = {
  background: "#1A1B22",
  surface: "#2E303E",
  accent: "#FF6B6B",
  success: "#4CAF50",
  error: "#F44336",
  softRed: "#FF8A8A",
  text: "#FFFFFF",
  hint: "#888888",
};

const EVENT_COLORS = {
  info: "#2196F3",
  warning: "#FFC107",
  error: "#F44336",
  success: "#4CAF50",
};

const API_BASE = "https://fastapi-event-api-66fji4lxba-uc.a.run.app";

// Enable LayoutAnimation on Android
if (Platform.OS === "android") {
  UIManager.setLayoutAnimationEnabledExperimental?.(true);
}

const SCREEN_WIDTH = Dimensions.get("window").width;
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.25;

const FeedItem = ({ item, onDelete }) => {
  const [expanded, setExpanded] = useState(false);
  const translateX = useRef(new Animated.Value(0)).current;

  const backgroundColor = translateX.interpolate({
    inputRange: [0, SWIPE_THRESHOLD],
    outputRange: [COLORS.surface, COLORS.softRed],
    extrapolate: "clamp",
  });

  const accentColor = EVENT_COLORS[item.event_type] || COLORS.accent;

  // Only track rightward drags
  const onGestureEvent = ({ nativeEvent }) => {
    const { translationX } = nativeEvent;
    if (translationX > 0) {
      translateX.setValue(translationX);
    }
  };

  const onHandlerStateChange = ({ nativeEvent }) => {
    if (nativeEvent.oldState === State.ACTIVE) {
      const { translationX } = nativeEvent;
      if (translationX > SWIPE_THRESHOLD) {
        Animated.timing(translateX, {
          toValue: SCREEN_WIDTH,
          duration: 200,
          useNativeDriver: false,
        }).start(() => {
          LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
          onDelete(item.id);
          translateX.setValue(0);
        });
      } else {
        Animated.spring(translateX, {
          toValue: 0,
          useNativeDriver: false,
        }).start();
      }
    }
  };

  const toggleExpand = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded(v => !v);
  };

  return (
    <PanGestureHandler
      onGestureEvent={onGestureEvent}
      onHandlerStateChange={onHandlerStateChange}
    >
      <Animated.View
        style={[
          styles.card,
          { backgroundColor, borderLeftColor: accentColor, transform: [{ translateX }] },
        ]}
      >
        <TouchableOpacity onPress={toggleExpand} activeOpacity={0.8} style={styles.header}>
          <Text style={styles.title}>{item.title}</Text>
          <MaterialIcons
            name={expanded ? "keyboard-arrow-up" : "keyboard-arrow-down"}
            size={24}
            color={COLORS.hint}
          />
        </TouchableOpacity>

        {expanded && (
          <View style={styles.detail}>
            <Text style={styles.summary}>{item.summary}</Text>
            <TouchableOpacity style={styles.sourceButton} onPress={() => Linking.openURL(item.link)}>
              <Text style={styles.sourceButtonText}>View Original Source</Text>
            </TouchableOpacity>
          </View>
        )}
      </Animated.View>
    </PanGestureHandler>
  );
};

export default function Feed() {
  const [data, setData] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      console.error("Location permission not granted");
      setLoading(false);
      return;
    }
    try {
      const loc = await Location.getCurrentPositionAsync({});
      const { latitude, longitude } = loc.coords;
      const res = await fetch(
        `${API_BASE}/lookup_incidents?lat=${latitude}&lng=${longitude}`
      );
      const items = await res.json();
      setData([...items.jurisdiction_incidents, ...items.city_incidents]);
    } catch (e) {
      console.error("Fetch failed", e);
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchData();
    setRefreshing(false);
  };

  const handleDelete = async id => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setData(prev => prev.filter(i => i.id !== id));
    try {
      await fetch(`${API_BASE}/feed/${id}`, { method: "DELETE" });
    } catch (e) {
      console.error("Delete failed", e);
    }
  };

  if (loading) {
    return (
      <GestureHandlerRootView style={{ flex: 1 }}>
        <SafeAreaView style={styles.safe}>
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color={COLORS.accent} />
          </View>
        </SafeAreaView>
      </GestureHandlerRootView>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaView style={styles.safe}>
        <FlatList
          data={data}
          keyExtractor={(item, index) =>
            item.id && item.source ? `${item.id}-${item.source}` : index.toString()
          }
          renderItem={({ item }) => <FeedItem item={item} onDelete={handleDelete} />}
          ItemSeparatorComponent={() => <View style={styles.separator} />}
          contentContainerStyle={
            data.length === 0 ? styles.emptyContainer : styles.list
          }
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.text} />
          }
          ListEmptyComponent={() => (
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>No feeds available!</Text>
              <Text style={styles.emptyText}>Pull down to refresh.</Text>
            </View>
          )}
          ListHeaderComponent={
            data.length > 0 ? <Text style={styles.hint}>Pull down to refresh</Text> : null
          }
        />
      </SafeAreaView>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  list: {
    padding: 16,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 16,
  },
  separator: {
    height: 12,
  },
  loaderContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  card: {
    borderRadius: 12,
    borderLeftWidth: 4,
    backgroundColor: COLORS.surface,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
    padding: 16,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: "600",
    flex: 1,
    marginRight: 8,
  },
  detail: {
    marginTop: 12,
  },
  summary: {
    color: COLORS.text,
    fontSize: 16,
    lineHeight: 22,
  },
  sourceButton: {
    backgroundColor: COLORS.accent,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    marginTop: 12,
    alignSelf: "flex-start",
  },
  sourceButtonText: {
    color: COLORS.text,
    fontWeight: "600",
  },
  emptyText: {
    color: COLORS.text,
    fontSize: 18,
  },
  hint: {
    textAlign: "center",
    color: COLORS.hint,
    fontSize: 14,
    marginBottom: 8,
  },
});
