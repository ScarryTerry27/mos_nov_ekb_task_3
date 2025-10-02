import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  Pressable,
  ActivityIndicator,
  Modal,
  TextInput,
  Linking,
  ScrollView,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import * as Location from "expo-location";
import { useObjectsStore } from "@/store";
import { uploadVideo, putCheck, putIncident } from "@/api/actions";

interface Incident {
  incident_id: string | number;
  incident_status: boolean;
  incident_info: string;
}

interface Check {
  check_id: string | number;
  info: string;
  status_check: boolean;
}

export default function CheckScreen() {
  const activeSubObject = useObjectsStore((s) => s.activeSubObject);
  const subobject_id = useObjectsStore((state) => state.activeSubObject?.subobject_id);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [check, setCheck] = useState<Check | null>(null);
  const [reportUrl, setReportUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const askMediaPermissions = async () => {
    const lib = await ImagePicker.requestMediaLibraryPermissionsAsync();
    return lib.status === "granted";
  };

  const askCameraPermissions = async () => {
    const cam = await ImagePicker.requestCameraPermissionsAsync();
    return cam.status === "granted";
  };

  const askLocation = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== "granted") return undefined;
      const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      return { lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy ?? undefined };
    } catch {
      return undefined;
    }
  };

  const reverseGeocode = async (lat: number, lon: number) => {
    try {
      const res = await Location.reverseGeocodeAsync({ latitude: lat, longitude: lon });
      const p = res[0];
      const parts = [p?.country, p?.region, p?.city || p?.subregion, p?.street, p?.name].filter(Boolean).join(", ");
      return parts || undefined;
    } catch {
      return undefined;
    }
  };

  const buildVideoFormData = (p: {
    uri: string;
    fileName?: string | null;
    type?: string | null;
    address?: string;
    lat?: number;
    lon?: number;
    subobject_id: number | string;
  }) => {
    const fd = new FormData();
    fd.append("subobject_id", String(1));
    if (p.lat != null) fd.append("location_lat", String(-90));
    if (p.lon != null) fd.append("location_lon", String(-180));
    if (p.address) fd.append("address", p.address);

    const name = (p.fileName && p.fileName.replace(/\s+/g, "_")) || `video_${Date.now()}.mp4`;

    fd.append("video", {
      uri: p.uri,
      name,
      type: p.type || "video/mp4",
    } as any);

    return fd;
  };

  const handleAutoUpload = async (uri: string, fileName: any, type: any) => {
    if (!subobject_id) {
      setError("Не удалось определить ID субобъекта");
      return;
    }

    setUploading(true);
    setError(null);
    setPickerOpen(false);

    try {
      const location = await askLocation();
      const address = location ? await reverseGeocode(location.lat, location.lon) : undefined;

      const formData = buildVideoFormData({
        uri,
        fileName,
        type,
        address,
        lat: location?.lat,
        lon: location?.lon,
        subobject_id,
      });
      const { check, incidents, report_url } = await uploadVideo(formData);

      setCheck(check);
      setIncidents(incidents);
      setReportUrl(report_url._url);
    } catch (err: any) {
      console.error("Full upload error:", {
        message: err?.message,
        response: JSON.stringify(err?.response?.data, null, 2),
        status: err?.response?.status,
        headers: err?.response?.headers,
      });
      setError(err?.response?.data?.message || err?.message || "Ошибка загрузки видео");
    } finally {
      setUploading(false);
    }
  };

  const pickFromLibrary = async () => {
    const hasPermission = await askMediaPermissions();
    if (!hasPermission) {
      setError("Нет доступа к галерее");
      setPickerOpen(false);
      return;
    }

    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Videos,
        allowsEditing: false,
        quality: 1,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        await handleAutoUpload(asset.uri, asset.fileName, asset.mimeType);
      }
    } catch (err) {
      console.error("Library picker error:", err);
      setError("Ошибка при выборе видео из галереи");
      setPickerOpen(false);
    }
  };

  const recordVideo = async () => {
    const hasPermission = await askCameraPermissions();
    if (!hasPermission) {
      setError("Нет доступа к камере");
      setPickerOpen(false);
      return;
    }

    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Videos,
        allowsEditing: false,
        quality: 1,
        videoMaxDuration: 60,
      });

      if (!result.canceled && result.assets[0]) {
        const asset = result.assets[0];
        await handleAutoUpload(asset.uri, asset.fileName, asset.mimeType);
      }
    } catch (err) {
      console.error("Camera error:", err);
      setError("Ошибка при записи видео");
      setPickerOpen(false);
    }
  };

  const handleCheckInfoChange = (text: string) => {
    if (check) {
      setCheck({ ...check, info: text });
    }
  };

  const handleCheckStatusChange = (value: boolean) => {
    if (check) {
      setCheck({ ...check, status_check: value });
    }
  };

  const handleIncidentInfoChange = (index: number, text: string) => {
    const updatedIncidents = [...incidents];
    updatedIncidents[index] = { ...updatedIncidents[index], incident_info: text };
    setIncidents(updatedIncidents);
  };

  const handleIncidentStatusChange = (index: number, value: boolean) => {
    const updatedIncidents = [...incidents];
    updatedIncidents[index] = { ...updatedIncidents[index], incident_status: value };
    setIncidents(updatedIncidents);
  };

  const handleUpdateCheck = async () => {
    if (!check || !check.check_id) {
      setError("Проверка или ID проверки отсутствует");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      await putCheck({
        check_id: check.check_id,
        info: check.info,
        status_check: check.status_check,
      });
      setError("Проверка успешно обновлена");
    } catch (err: any) {
      console.error("Check update error:", err);
      setError(err?.response?.data?.message || err?.message || "Ошибка при обновлении проверки");
    } finally {
      setUploading(false);
    }
  };

  const handleUpdateIncidents = async () => {
    if (incidents.length === 0) {
      setError("Нет инцидентов для обновления");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      for (const incident of incidents) {
        if (!incident.incident_id) {
          throw new Error(`Инцидент ${incident.incident_info} не имеет ID`);
        }
        await putIncident({
          incident_id: incident.incident_id,
          incident_status: incident.incident_status,
          incident_info: incident.incident_info,
        });
      }
      setError("Инциденты успешно обновлены");
    } catch (err: any) {
      console.error("Incidents update error:", err);
      setError(err?.response?.data?.message || err?.message || "Ошибка при обновлении инцидентов");
    } finally {
      setUploading(false);
    }
  };

  const handleDownloadReport = async () => {
    if (reportUrl) {
      try {
        await Linking.openURL(reportUrl);
      } catch (err) {
        console.error("Error opening report URL:", err);
        setError("Ошибка при открытии отчета");
      }
    } else {
      setError("Отчет недоступен");
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.header}>{activeSubObject?.name ?? "Проверка субобъекта"}</Text>

        <View style={styles.card}>
          <Text style={styles.caption}>Загрузите видео-доказательство выполнения работ.</Text>

          <Pressable
            style={({ pressed }) => [styles.btn, pressed && styles.btnPressed]}
            onPress={() => setPickerOpen(true)}
            disabled={uploading}
          >
            <Text style={styles.btnText}>{uploading ? "Загрузка…" : "Добавить медиа"}</Text>
          </Pressable>

          {uploading && (
            <View style={styles.inline}>
              <ActivityIndicator />
              <Text style={styles.muted}>Отправляем видео на сервер…</Text>
            </View>
          )}

          {check && (
            <View style={styles.resultBox}>
              <Text style={styles.resultTitle}>Информация о проверке</Text>
              <TextInput
                style={styles.input}
                value={check.info}
                onChangeText={handleCheckInfoChange}
                placeholder="Введите информацию о проверке"
                placeholderTextColor="#9CA3AF"
                multiline
              />
              <View style={styles.toggleContainer}>
                <Text style={styles.toggleLabel}>Статус проверки:</Text>
                <View style={styles.toggleButtons}>
                  <Pressable
                    style={({ pressed }) => [
                      styles.toggleBtn,
                      check.status_check && styles.toggleBtnActive,
                      pressed && styles.btnPressed,
                    ]}
                    onPress={() => handleCheckStatusChange(true)}
                  >
                    <Text style={[styles.toggleBtnText, check.status_check && styles.toggleBtnTextActive]}>
                      Активен
                    </Text>
                  </Pressable>
                  <Pressable
                    style={({ pressed }) => [
                      styles.toggleBtn,
                      !check.status_check && styles.toggleBtnActive,
                      pressed && styles.btnPressed,
                    ]}
                    onPress={() => handleCheckStatusChange(false)}
                  >
                    <Text style={[styles.toggleBtnText, !check.status_check && styles.toggleBtnTextActive]}>
                      Неактивен
                    </Text>
                  </Pressable>
                </View>
              </View>
              <Pressable
                style={({ pressed }) => [styles.btn, pressed && styles.btnPressed, styles.downloadBtn]}
                onPress={handleUpdateCheck}
                disabled={uploading}
              >
                <Text style={styles.btnText}>Обновить проверку</Text>
              </Pressable>
            </View>
          )}

          {incidents.length > 0 && (
            <View style={styles.resultBox}>
              <Text style={styles.resultTitle}>Инциденты</Text>
              {incidents.map((incident, index) => (
                <View key={index} style={styles.incidentItem}>
                  <Text style={styles.resultRow}>Инцидент {index + 1}</Text>
                  <TextInput
                    style={styles.input}
                    value={incident.incident_info}
                    onChangeText={(text) => handleIncidentInfoChange(index, text)}
                    placeholder="Введите описание инцидента"
                    placeholderTextColor="#9CA3AF"
                    multiline
                  />
                  <View style={styles.toggleContainer}>
                    <Text style={styles.toggleLabel}>Статус инцидента:</Text>
                    <View style={styles.toggleButtons}>
                      <Pressable
                        style={({ pressed }) => [
                          styles.toggleBtn,
                          incident.incident_status && styles.toggleBtnActive,
                          pressed && styles.btnPressed,
                        ]}
                        onPress={() => handleIncidentStatusChange(index, true)}
                      >
                        <Text
                          style={[styles.toggleBtnText, incident.incident_status && styles.toggleBtnTextActive]}
                        >
                          Активен
                        </Text>
                      </Pressable>
                      <Pressable
                        style={({ pressed }) => [
                          styles.toggleBtn,
                          !incident.incident_status && styles.toggleBtnActive,
                          pressed && styles.btnPressed,
                        ]}
                        onPress={() => handleIncidentStatusChange(index, false)}
                      >
                        <Text
                          style={[styles.toggleBtnText, !incident.incident_status && styles.toggleBtnTextActive]}
                        >
                          Неактивен
                        </Text>
                      </Pressable>
                    </View>
                  </View>
                </View>
              ))}
              <Pressable
                style={({ pressed }) => [styles.btn, pressed && styles.btnPressed, styles.downloadBtn]}
                onPress={handleUpdateIncidents}
                disabled={uploading}
              >
                <Text style={styles.btnText}>Обновить инциденты</Text>
              </Pressable>
            </View>
          )}

          {reportUrl && (
            <Pressable
              style={({ pressed }) => [styles.btn, pressed && styles.btnPressed, styles.downloadBtn]}
              onPress={handleDownloadReport}
            >
              <Text style={styles.btnText}>Скачать отчет</Text>
            </Pressable>
          )}

          {error && <Text style={styles.error}>{error}</Text>}
        </View>
      </ScrollView>

      <Modal transparent visible={pickerOpen} animationType="fade" onRequestClose={() => setPickerOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setPickerOpen(false)} />
        <View style={styles.sheet}>
          <Text style={styles.sheetTitle}>Добавить медиа</Text>

          <Pressable
            style={({ pressed }) => [styles.sheetBtn, pressed && styles.sheetBtnPressed]}
            onPress={pickFromLibrary}
          >
            <Text style={styles.sheetBtnText}>Выбрать из галереи</Text>
          </Pressable>

          <Pressable
            style={({ pressed }) => [styles.sheetBtn, pressed && styles.sheetBtnPressed]}
            onPress={recordVideo}
          >
            <Text style={styles.sheetBtnText}>Снять видео</Text>
          </Pressable>

          <Pressable
            style={({ pressed }) => [styles.sheetCancel, pressed && styles.sheetBtnPressed]}
            onPress={() => setPickerOpen(false)}
          >
            <Text style={styles.sheetCancelText}>Отмена</Text>
          </Pressable>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB", paddingVertical: 40 },
  scrollContent: { paddingBottom: 20 },
  header: { fontSize: 18, fontWeight: "600", color: "#111827", paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12 },
  card: {
    marginHorizontal: 16,
    backgroundColor: "#fff",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    padding: 16,
    shadowColor: "#000",
    shadowOpacity: 0.03,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  caption: { fontSize: 14, color: "#6B7280", marginBottom: 12 },
  btn: {
    backgroundColor: "#111827",
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  btnPressed: { opacity: 0.9 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  inline: { flexDirection: "row", gap: 8, alignItems: "center", marginTop: 12 },
  muted: { fontSize: 12, color: "#6B7280" },
  resultBox: { marginTop: 12, borderTopWidth: 1, borderTopColor: "#F3F4F6", paddingTop: 12, gap: 8 },
  resultTitle: { fontSize: 16, fontWeight: "600", color: "#111827" },
  resultRow: { fontSize: 14, color: "#374151", marginBottom: 4 },
  error: { marginTop: 10, color: "#ef4444", fontSize: 12, fontWeight: "600" },
  backdrop: { flex: 1, backgroundColor: "#00000055" },
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "#fff",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 16,
    gap: 8,
    borderTopWidth: 1,
    borderColor: "#E5E7EB",
  },
  sheetTitle: { fontSize: 16, fontWeight: "700", color: "#111827", marginBottom: 4 },
  sheetBtn: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#E5E7EB",
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 12,
  },
  sheetBtnPressed: { opacity: 0.95 },
  sheetBtnText: { color: "#111827", fontWeight: "600" },
  sheetCancel: { marginTop: 4, alignItems: "center", paddingVertical: 12 },
  sheetCancelText: { color: "#6B7280", fontWeight: "600" },
  input: {
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: "#111827",
    backgroundColor: "#F9FAFB",
    minHeight: 80,
    textAlignVertical: "top",
  },
  incidentItem: { marginTop: 12, gap: 8 },
  downloadBtn: { marginTop: 12 },
  toggleContainer: { marginTop: 8 },
  toggleLabel: { fontSize: 14, color: "#374151", marginBottom: 8 },
  toggleButtons: { flexDirection: "row", gap: 8 },
  toggleBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#D1D5DB",
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 12,
    alignItems: "center",
    backgroundColor: "#F9FAFB",
  },
  toggleBtnActive: {
    backgroundColor: "#111827",
    borderColor: "#111827",
  },
  toggleBtnText: {
    fontSize: 14,
    color: "#111827",
    fontWeight: "600",
  },
  toggleBtnTextActive: {
    color: "#fff",
  },
});