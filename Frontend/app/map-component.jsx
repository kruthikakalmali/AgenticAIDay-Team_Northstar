import axios from "axios";
import * as Location from "expo-location";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Dimensions,
  Image,
  Linking,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import MapView, { Callout, Marker, PROVIDER_GOOGLE } from "react-native-maps";

const { width, height } = Dimensions.get("window");
const LATITUDE_DELTA = 0.05;
const ASPECT_RATIO = width / height;
const LONGITUDE_DELTA = LATITUDE_DELTA * ASPECT_RATIO;

// Dark theme colors
const COLORS = {
  background: "#222531",
  surface: "#2E303E",
  accent: "#FF6B6B",
  success: "#4CAF50",
  error: "#F44336",
  text: "#FFFFFF",
  buttonBg: "#3A3C4F",
};

// Event‑type icons
const ICONS = {
  music: require("../assets/images/music.png"),
  tech: require("../assets/images/tech.png"),
  shopping: require("../assets/images/shopping.png"),
  comedy: require("../assets/images/comedy.png"),
  movie: require("../assets/images/movie.png"),
  sports: require("../assets/images/sports.png"),
  fitness: require("../assets/images/fitness.png"),
  food: require("../assets/images/food.png"),
  party: require("../assets/images/party.png")
};
const AVAILABLE_ICONS = Object.values(ICONS);
const DEFAULT_ICON = require("../assets/images/default.png");

export default function BangaloreMap() {
  const [initialRegion, setInitialRegion] = useState(null);
  const [annotations, setAnnotations] = useState([]);
  const [allTypes, setAllTypes] = useState([]);
  const [selectedTypes, setSelectedTypes] = useState([]);
  const timeoutRef = useRef(null);
  const mapReadyRef = useRef(false);

  const API_ENDPOINT =
    "https://incident-api-66fji4lxba-uc.a.run.app/events-nearby";

  useEffect(() => {
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission denied", "Location access is required.");
        return;
      }
      const {
        coords: { latitude, longitude },
      } = await Location.getCurrentPositionAsync({});

      setInitialRegion({
        latitude,
        longitude,
        latitudeDelta: LATITUDE_DELTA,
        longitudeDelta: LONGITUDE_DELTA,
      });
      await fetchAndAppendData(latitude, longitude);
    })();
    return () => clearTimeout(timeoutRef.current);
  }, []);

  const fetchAndAppendData = async (lat, lon) => {
    try {
      const URL = `${API_ENDPOINT}?latitude=${lat}&longitude=${lon}`;
      const resp = await axios.get(URL);
      const data = Array.isArray(resp.data) ? resp.data : [];

      const flat = data.flatMap((grp) => {
        const evts = Array.isArray(grp.events) ? grp.events : [];
        return evts.map((e) => ({
          latitude: e.lat,
          longitude: e.lng,
          content: e.title,
          location: e.location,
          datetime: e.datetime,
          link: e.link,
          category: grp?.event_type || grp.type,
        }));
      });

      setAnnotations((prev) => {
        const seen = new Set(prev.map((a) => `${a.latitude},${a.longitude}`));
        const fresh = flat.filter((a) => !seen.has(`${a.latitude},${a.longitude}`));
        return [...prev, ...fresh];
      });

      setAllTypes((prev) => {
        const s = new Set(prev);
        flat.forEach((a) => s.add(a.category));
        return Array.from(s);
      });

      setSelectedTypes((prev) =>
        prev.length ? prev : Array.from(new Set(flat.map((a) => a.category)))
      );
    } catch (e) {
      console.error("API fetch error:", e.message);
    }
  };

  const filtered = useMemo(
    () => annotations.filter((a) => selectedTypes.includes(a.category)),
    [annotations, selectedTypes]
  );

  const onRegionChangeComplete = (r) => {
    if (!mapReadyRef.current) return;
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => {
      fetchAndAppendData(r.latitude, r.longitude);
    }, 1000);
  };

  const toggleType = (type) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  if (!initialRegion) return null;
  return (
    <View style={styles.container}>
      <MapView
        provider={PROVIDER_GOOGLE}
        style={styles.map}
        initialRegion={initialRegion}
        showsTraffic
        onMapReady={() => (mapReadyRef.current = true)}
        onRegionChangeComplete={onRegionChangeComplete}
        customMapStyle={dawnMapStyle}
      >
        {filtered.map((a, i) => {
          const icon = ICONS[a.category] || AVAILABLE_ICONS[0] || DEFAULT_ICON;
          return (
            <Marker
              key={`${a.latitude}-${a.longitude}-${i}`}
              coordinate={{ latitude: a.latitude, longitude: a.longitude }}
              image={icon}
            >
              <Callout tooltip>
                <View style={styles.calloutContainer}>
                  <Text style={styles.calloutTitle}>{a.content}</Text>
                  <Text style={styles.calloutLocation}>{a.location}</Text>
                  <TouchableOpacity
                    onPress={() => Linking.openURL(a.link)}
                    style={styles.calloutButton}
                    activeOpacity={0.8}
                  >
                    <Text style={styles.calloutLink}>View Details</Text>
                  </TouchableOpacity>
                </View>
              </Callout>
            </Marker>
          );
        })}
      </MapView>

      {/* vertical round filter buttons */}
      <View style={styles.filterVerticalContainer}>
        {allTypes.map((type) => {
          const icon = ICONS[type] || DEFAULT_ICON;
          const selected = selectedTypes.includes(type);
          return (
            <TouchableOpacity
              key={type}
              onPress={() => toggleType(type)}
              style={[
                styles.filterRoundButton,
                selected && styles.filterRoundButtonSelected,
              ]}
              activeOpacity={0.8}
            >
              <Image
                source={icon}
                style={[
                  styles.filterRoundIcon,
                  selected && { tintColor: COLORS.text },
                ]}
              />
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  map: { flex: 1 },

  markerIcon: {
    width: 30,
    height: 30,
    resizeMode: "contain",
  },

  calloutContainer: {
    width: 200,
    padding: 8,
    borderRadius: 8,
    backgroundColor: "#fff",
    elevation: 4,
  },
  calloutTitle: {
    fontSize: 16,
    fontWeight: "bold",
    marginBottom: 4,
    color: "#333",
  },
  calloutLocation: {
    fontSize: 14,
    marginBottom: 8,
    color: "#555",
  },
  calloutButton: {
    alignSelf: "flex-start",
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 4,
    backgroundColor: COLORS.accent,
  },
  calloutLink: {
    fontSize: 14,
    color: "#fff",
    fontWeight: "600",
  },

  // vertical container on left
  filterVerticalContainer: {
    position: "absolute",
    top: 100,
    left: 10,
    width: 50,
    alignItems: "center",
    backgroundColor: "transparent",
  },
  filterRoundButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: COLORS.buttonBg,
    marginVertical: 6,
    justifyContent: "center",
    alignItems: "center",
  },
  filterRoundButtonSelected: {
    backgroundColor: COLORS.accent,
  },
  filterRoundIcon: {
    width: 24,
    height: 24,
    tintColor: COLORS.text,
    resizeMode: "contain",
  },
});

const dawnMapStyle = [
  { elementType: "geometry", stylers: [{ color: "#ebe3cd" }] },
  { elementType: "labels", stylers: [{ visibility: "off" }] },
  { elementType: "labels.icon", stylers: [{ visibility: "off" }] },
  { elementType: "labels.text.fill", stylers: [{ visibility: "off" }] },
  { elementType: "labels.text.stroke", stylers: [{ visibility: "off" }] },
  {
    featureType: "administrative",
    elementType: "geometry.stroke",
    stylers: [{ color: "#c9b2a6" }],
  },
  {
    featureType: "poi",
    elementType: "geometry",
    stylers: [{ color: "#dfd2ae" }],
  },
  { featureType: "poi.business", stylers: [{ visibility: "off" }] },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#f5f1e6" }],
  },
  {
    featureType: "road.arterial",
    elementType: "geometry",
    stylers: [{ color: "#fdfcf8" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry",
    stylers: [{ color: "#f8c967" }],
  },
  {
    featureType: "road.highway",
    elementType: "geometry.stroke",
    stylers: [{ color: "#e9bc62" }],
  },
  { featureType: "road.local", stylers: [{ visibility: "on" }] },
  {
    featureType: "transit.line",
    elementType: "geometry",
    stylers: [{ color: "#dfd2ae" }],
  },
  {
    featureType: "water",
    elementType: "geometry.fill",
    stylers: [{ color: "#b9d3c2" }],
  },
];