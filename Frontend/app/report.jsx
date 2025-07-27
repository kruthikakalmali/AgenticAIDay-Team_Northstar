import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  Animated,
  Image,
  Modal,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { INCIDENT_API_URL_HOST } from "./constants";

const COLORS = {
  background: "#222531",
  surface: "#2E303E",
  accent: "#FF6B6B",
  success: "#4CAF50",
  error: "#F44336",
  text: "#FFFFFF",
  buttonBg: "#3A3C4F",
};

const CATEGORIES = ["pothole", "accident", "roadblock", "water logging", "other"];

const API_ENDPOINT = `${INCIDENT_API_URL_HOST}/report-incident`;

export default function Report() {
  const insets = useSafeAreaInsets();
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [imageUri, setImageUri] = useState(null);
  const [pickerVisible, setPickerVisible] = useState(false);
  const [fullImageVisible, setFullImageVisible] = useState(false);
  const [loading, setLoading] = useState(false);

  const toastAnim = useRef(new Animated.Value(0)).current;
  const [toastMsg, setToastMsg] = useState("");
  const [toastColor, setToastColor] = useState(COLORS.success);

  const showToast = (message, color) => {
    setToastMsg(message);
    setToastColor(color);
    Animated.sequence([
      Animated.timing(toastAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: false,
      }),
      Animated.delay(2000),
      Animated.timing(toastAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: false,
      }),
    ]).start();
  };

  const pickImage = async (mode) => {
    let result;
    if (mode === "camera") {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== "granted") {
        showToast("Camera permission is required.", COLORS.error);
        return;
      }
      result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
      });
    } else {
      const { status } =
        await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (status !== "granted") {
        showToast("Gallery permission is required.", COLORS.error);
        return;
      }
      result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
      });
    }

    if (!result.canceled && result.assets?.length) {
      setImageUri(result.assets[0].uri);
    }
  };

  const handleSubmit = async () => {
    if (!description.trim()) {
      showToast("Description cannot be empty.", COLORS.error);
      return;
    }

    setLoading(true);

    // Request location
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== "granted") {
      showToast("Location permission is needed.", COLORS.error);
      setLoading(false);
      return;
    }
    const loc = await Location.getCurrentPositionAsync({});

    // Build payload
    const form = new FormData();
    form.append("description", description);
    form.append("event_type", category);
    form.append(
      "location",
      JSON.stringify({
        latitude: loc.coords.latitude,
        longitude: loc.coords.longitude,
      })
    );
    form.append("timestamp", Date.now().toString());

    if (imageUri) {
      const filename = imageUri.split("/").pop();
      form.append("images", {
        uri: imageUri,
        name: filename,
        type: "image/jpeg",
      });
    }

    try {
      const res = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "multipart/form-data",
        },
        body: form,
      });

      if (res.ok) {
        showToast("Report submitted successfully!", COLORS.success);
        setDescription("");
        setCategory(CATEGORIES[0]);
        setImageUri(null);
        setFullImageVisible(false);
      } else {
        showToast("Submission failed. Try again.", COLORS.error);
      }
    } catch (e) {
      showToast("Network error. Please retry.", COLORS.error);
    } finally {
      setLoading(false);
    }
  };

  const toastStyle = {
    backgroundColor: toastColor,
    opacity: toastAnim,
    transform: [
      {
        translateY: toastAnim.interpolate({
          inputRange: [0, 1],
          outputRange: [-50, 0],
        }),
      },
    ],
  };

  return (
    <SafeAreaView style={styles.safe}>
      <Animated.View style={[styles.toast, toastStyle]}>
        <Text style={styles.toastText}>{toastMsg}</Text>
      </Animated.View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.container}
      >
        {/* Description */}
        <View style={styles.labelRow}>
          <Text style={styles.label}>Description</Text>
          <Text style={styles.charCount}>{description.length}/200</Text>
        </View>
        <TextInput
          style={styles.input}
          placeholder="Describe the incident..."
          placeholderTextColor="#888"
          multiline
          maxLength={200}
          value={description}
          onChangeText={setDescription}
        />

        <Text style={[styles.label, styles.labelSection]}>Event Type</Text>
        <View style={styles.pickerContainer}>
          <TouchableOpacity
            style={styles.pickerTouch}
            onPress={() => setPickerVisible(!pickerVisible)}
            activeOpacity={0.7}
          >
            <Text style={styles.pickerText}>{category}</Text>
            <Ionicons name="chevron-down" size={20} color={COLORS.text} />
          </TouchableOpacity>
          {pickerVisible && (
            <View style={styles.pickerDropdown}>
              {CATEGORIES.map((item) => (
                <TouchableOpacity
                  key={item}
                  style={styles.dropdownItem}
                  onPress={() => {
                    setCategory(item);
                    setPickerVisible(false);
                  }}
                  activeOpacity={0.7}
                >
                  <Text style={styles.dropdownItemText}>{item}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* Photo picker */}
        <Text style={[styles.label, styles.labelSection]}>Photo</Text>
        <View style={styles.photoRow}>
          <TouchableOpacity
            style={[styles.photoButton, styles.photoOption]}
            onPress={() => pickImage("camera")}
            activeOpacity={0.7}
          >
            <Ionicons name="camera" size={20} color={COLORS.text} />
            <Text style={styles.photoButtonText}>Take Photo</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.photoButton, styles.photoOption]}
            onPress={() => pickImage("gallery")}
            activeOpacity={0.7}
          >
            <Ionicons name="image-outline" size={20} color={COLORS.text} />
            <Text style={styles.photoButtonText}>Choose Gallery</Text>
          </TouchableOpacity>
        </View>

        {imageUri && (
          <>
            <TouchableOpacity
              activeOpacity={0.9}
              onPress={() => setFullImageVisible(true)}
            >
              <View style={styles.previewContainer}>
                <Image
                  source={{ uri: imageUri }}
                  style={styles.previewImage}
                  resizeMode="cover"
                />
                <View style={styles.watermarkOverlay}>
                  <Text style={styles.watermarkText}>PREVIEW</Text>
                </View>
              </View>
            </TouchableOpacity>
            <Modal
              visible={fullImageVisible}
              transparent
              animationType="fade"
              onRequestClose={() => setFullImageVisible(false)}
            >
              <TouchableOpacity
                style={styles.fullScreenOverlay}
                activeOpacity={1}
                onPress={() => setFullImageVisible(false)}
              >
                <Image
                  source={{ uri: imageUri }}
                  style={styles.fullScreenImage}
                  resizeMode="contain"
                />
              </TouchableOpacity>
            </Modal>
          </>
        )}
      </ScrollView>

      <View style={[styles.submitContainer, { bottom: insets.bottom + 10 }]}>
        <TouchableOpacity
          style={[styles.submitButton, loading && { opacity: 0.7 }]}
          onPress={handleSubmit}
          activeOpacity={0.8}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator
              size="small"
              color={COLORS.background}
              style={{ marginRight: 8 }}
            />
          ) : (
            <Ionicons
              name="send"
              size={20}
              color={COLORS.background}
              style={styles.icon}
            />
          )}
          <Text style={styles.submitText}>
            {loading ? "Submitting..." : "Submit"}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.surface },
  toast: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    padding: 12,
    zIndex: 2000,
  },
  toastText: { color: COLORS.text, textAlign: "center", fontWeight: "600" },
  scroll: { flex: 1 },
  container: { padding: 20, paddingTop: 60, paddingBottom: 20 },
  labelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    color: COLORS.text,
    fontSize: 16,
    fontWeight: "500",
    marginBottom: 8,
  },
  charCount: { color: COLORS.text, fontSize: 14, fontWeight: "400" },
  input: {
    backgroundColor: COLORS.buttonBg,
    color: COLORS.text,
    borderRadius: 12,
    padding: Platform.OS === "ios" ? 18 : 14,
    fontSize: 16,
    marginBottom: 24,
    minHeight: 80,
    textAlignVertical: "top",
  },
  labelSection: { marginTop: 10, marginBottom: 8 },
  pickerContainer: { position: "relative", marginBottom: 24 },
  pickerTouch: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: COLORS.buttonBg,
    padding: Platform.OS === "ios" ? 18 : 14,
    borderRadius: 12,
  },
  pickerText: { color: COLORS.text, fontSize: 16 },
  pickerDropdown: {
    position: "absolute",
    top: Platform.OS === "ios" ? 60 : 60,
    width: "100%",
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    maxHeight: 200,
    zIndex: 1000,
  },
  dropdownItem: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.buttonBg,
  },
  dropdownItemText: { color: COLORS.text, fontSize: 16 },
  photoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 24,
  },
  photoOption: { flex: 1, flexDirection: "row", alignItems: "center" },
  photoButton: {
    backgroundColor: COLORS.accent,
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginHorizontal: 5,
    alignItems: "center",
    justifyContent: "center",
  },
  photoButtonText: {
    color: COLORS.background,
    fontWeight: "600",
    marginLeft: 8,
    fontSize: 15,
  },
  icon: { opacity: 0.9 },
  previewContainer: {
    width: "100%",
    height: 100,
    borderRadius: 12,
    overflow: "hidden",
    marginBottom: 16,
    position: "relative",
    backgroundColor: COLORS.buttonBg,
  },
  previewImage: { width: "100%", height: "100%" },
  watermarkOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: "center",
    alignItems: "center",
  },
  watermarkText: {
    color: "rgba(255,255,255,0.5)",
    fontSize: 16,
    fontWeight: "bold",
    textTransform: "uppercase",
  },
  fullScreenOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.9)",
    justifyContent: "center",
    alignItems: "center",
  },
  fullScreenImage: { width: "100%", height: "100%" },
  submitContainer: {
    position: "absolute",
    left: 0,
    right: 0,
    alignItems: "center",
  },
  submitButton: {
    flexDirection: "row",
    backgroundColor: COLORS.accent,
    paddingVertical: 16,
    paddingHorizontal: 30,
    borderRadius: 12,
    alignItems: "center",
  },
  submitText: {
    color: COLORS.background,
    fontSize: 16,
    fontWeight: "600",
    marginLeft: 10,
  },
});
