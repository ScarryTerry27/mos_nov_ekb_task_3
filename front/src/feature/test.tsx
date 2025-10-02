import {Button, StyleSheet, View, Image, Platform, Alert, ActionSheetIOS, Text, TouchableOpacity} from "react-native";
import {useState} from "react";
import * as ImagePicker from "expo-image-picker";
import {Video} from "expo-av";

export default function Test() {
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [image, setImage] = useState<string | null>(null);
  const [video, setVideo] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [videoResult, setVideoResult] = useState<any>(null);

  const selectImage = async (source: "camera" | "library") => {
    try {
      setLoading(true);

      if (source === "library") {
        const libPerm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!libPerm.granted) {
          Alert.alert("Нет доступа к галерее", "Разрешите доступ в настройках.");
          return;
        }
        const result = await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Images,
          quality: 0.8,
          allowsEditing: true,
        });
        if (!result.canceled) {
          const imageUri = result.assets[0].uri;
          setImage(imageUri);
          setVideo(null);
          setVideoResult(null);
          await uploadImage(imageUri, result.assets[0]);
        }
        return;
      }

      const camPerm = await ImagePicker.requestCameraPermissionsAsync();
      if (!camPerm.granted) {
        Alert.alert("Нет доступа к камере", "Разрешите доступ в настройках.");
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        quality: 0.8,
        allowsEditing: true,
      });
      if (!result.canceled) {
        const imageUri = result.assets[0].uri;
        setImage(imageUri);
        setVideo(null);
        setVideoResult(null);
        await uploadImage(imageUri, result.assets[0]);
      }
    } catch (error) {
      console.error("Ошибка выбора изображения:", error);
      Alert.alert("Ошибка", "Не удалось выбрать изображение");
    } finally {
      setLoading(false);
    }
  };

  const selectVideo = async (source: "camera" | "library") => {
    try {
      setLoading(true);

      if (source === "library") {
        const libPerm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!libPerm.granted) {
          Alert.alert("Нет доступа к галерее", "Разрешите доступ в настройках.");
          return;
        }
        const result = await ImagePicker.launchImageLibraryAsync({
          mediaTypes: ImagePicker.MediaTypeOptions.Videos,
          quality: 0.8,
          allowsEditing: false,
        });
        if (!result.canceled) {
          const videoUri = result.assets[0].uri;
          const duration = result.assets[0].duration || 0;
          console.log(`Выбрано видео из галереи: ${videoUri}, длительность: ${Math.round(duration / 1000)}сек`);
          setVideo(videoUri);
          setImage(null);
          setResult(null);
          await uploadVideo(videoUri, result.assets[0]);
        }
        return;
      }

      const camPerm = await ImagePicker.requestCameraPermissionsAsync();
      if (!camPerm.granted) {
        Alert.alert("Нет доступа к камере", "Разрешите доступ в настройках.");
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Videos,
        allowsEditing: false,
        quality: 0.8,
        videoMaxDuration: 60,
        videoQuality: ImagePicker.UIImagePickerControllerQualityType.Medium,
      });

      if (!result.canceled) {
        const videoUri = result.assets[0].uri;
        const duration = result.assets[0].duration || 0;

        console.log(`Записано видео: ${videoUri}, длительность: ${Math.round(duration / 1000)}сек`);

        setVideo(videoUri);
        setImage(null);
        setResult(null);
        await uploadVideo(videoUri, result.assets[0]);
      }
    } catch (error) {
      console.error("Ошибка работы с видео:", error);
      Alert.alert("Ошибка", "Не удалось работать с видео");
    } finally {
      setLoading(false);
    }
  };

  const uploadImage = async (imageUri: string, asset: ImagePicker.ImagePickerAsset) => {
    try {
      setUploading(true);
      console.log(`Отправляю файл '${imageUri}' на http://194.87.236.27/upload-image...`);

      const extFromUri = imageUri.split(".").pop()?.toLowerCase() || "jpg";
      const name = (asset as any).fileName || `photo.${extFromUri}`;
      const type = asset.mimeType || `image/${extFromUri === "jpg" ? "jpeg" : extFromUri}`;

      if (!imageUri || !imageUri.startsWith("file://")) {
        throw new Error("Недействительный URI изображения");
      }

      const formData = new FormData();
      formData.append("file", {
        uri: imageUri,
        name,
        type,
      } as any);
      //
      Alert.alert("Успех", "МУЖИКИ, ЗАРАБОТАЛО!");
    } catch (error: any) {
      console.error("Ошибка загрузки:", error);
      let errorMessage = "Не удалось загрузить изображение";
      if (error.code === "ERR_NETWORK") {
        errorMessage = "Ошибка: Не удалось подключиться к серверу. Проверьте IP и порт.";
      } else if (error.code === "ECONNABORTED") {
        errorMessage = "Ошибка: Таймаут. Сервер не ответил за 300 секунд.";
      } else if (error.response) {
        errorMessage = error.response.data?.message || `Ошибка сервера: ${error.response.status}`;
      } else {
        errorMessage = `Неизвестная ошибка: ${error.message}`;
      }
      Alert.alert("Ошибка загрузки", errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const uploadVideo = async (videoUri: string, asset: ImagePicker.ImagePickerAsset) => {
    try {
      setUploading(true);
      const duration = asset.duration ? Math.round(asset.duration / 1000) : 'неизвестно';
      console.log(`Отправляю видео '${videoUri}' на http://194.87.236.27/upload-video... (${duration}сек)`);

      const extFromUri = videoUri.split(".").pop()?.toLowerCase() || "mp4";
      const name = (asset as any).fileName || `video_${Date.now()}.${extFromUri}`;
      const type = asset.mimeType || `video/${extFromUri}`;

      if (!videoUri || !videoUri.startsWith("file://")) {
        throw new Error("Недействительный URI видео");
      }

      console.log(`Файл видео: ${name}, тип: ${type}, размер: ${asset.fileSize ? Math.round(asset.fileSize / 1024 / 1024) : 'неизвестно'}МБ`);

      const formData = new FormData();
      formData.append("file", {
        uri: videoUri,
        name,
        type,
      } as any);

      const response = await apiRequest("post", "/upload-video", formData, {
        headers: {"Content-Type": "multipart/form-data"},
        timeout: 600000,
      });

      setVideoResult(response);
      console.log("Video upload response:", response);
      Alert.alert("Успех", `Видео загружено на сервер! Длительность: ${duration}сек`);

    } catch (error: any) {
      console.error("Ошибка загрузки видео:", error);
      let errorMessage = "Не удалось загрузить видео";
      if (error.code === "ERR_NETWORK") {
        errorMessage = "Ошибка: Не удалось подключиться к серверу. Проверьте IP и порт.";
      } else if (error.code === "ECONNABORTED") {
        errorMessage = "Ошибка: Таймаут. Сервер не ответил.";
      } else if (error.response) {
        errorMessage = error.response.data?.message || `Ошибка сервера: ${error.response.status}`;
      } else {
        errorMessage = `Неизвестная ошибка: ${error.message}`;
      }
      Alert.alert("Ошибка загрузки видео", errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const openChooser = () => {
    if (Platform.OS === "ios") {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options: ["Отмена", "Сделать фото", "Выбрать фото из галереи", "Записать видео", "Выбрать видео из галереи"],
          cancelButtonIndex: 0,
        },
        (buttonIndex) => {
          if (buttonIndex === 1) selectImage("camera");
          if (buttonIndex === 2) selectImage("library");
          if (buttonIndex === 3) selectVideo("camera");
          if (buttonIndex === 4) selectVideo("library");
        }
      );
    } else {
      Alert.alert("Добавить медиа", "Выберите источник", [
        {text: "Сделать фото", onPress: () => selectImage("camera")},
        {text: "Выбрать фото из галереи", onPress: () => selectImage("library")},
        {text: "Записать видео", onPress: () => selectVideo("camera")},
        {text: "Выбрать видео из галереи", onPress: () => selectVideo("library")},
        {text: "Отмена", style: "cancel"},
      ]);
    }
  };

  const handleDelete = () => {
    setImage(null);
    setVideo(null);
    setResult(null);
    setVideoResult(null);
  };

  const handleClick = async () => {
    setLoading(true);
    console.log("Отправляю result на БЕК...");
    try {
      const dataToSend = result || videoResult;
      console.log("Данные для отправки:", dataToSend);
      Alert.alert("Успех", "Бек принял на грудь!");
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <TouchableOpacity
          style={[styles.button, (loading || uploading) && styles.buttonDisabled]}
          onPress={openChooser}
          disabled={loading || uploading}
        >
          <Text style={styles.buttonText}>
            {loading ? "Загрузка..." : "Добавить медиа"}
          </Text>
        </TouchableOpacity>

        {(image || video) && (
          <>
            {image && (
              <View style={styles.mediaContainer}>
                <Image source={{uri: image}} style={styles.media}/>
                <Text style={styles.mediaLabel}>Фото</Text>
              </View>
            )}

            {video && (
              <View style={styles.mediaContainer}>
                <Video
                  source={{uri: video}}
                  style={styles.media}
                  useNativeControls
                />
                <Text style={styles.mediaLabel}>
                  Видео{videoResult?.duration && ` (${videoResult.duration}с)`}
                </Text>
              </View>
            )}

            <TouchableOpacity
              style={[styles.deleteButton, uploading && styles.buttonDisabled]}
              onPress={handleDelete}
              disabled={uploading}
            >
              <Text style={styles.deleteButtonText}>Удалить</Text>
            </TouchableOpacity>
          </>
        )}

        {(result || videoResult) && (
          <TouchableOpacity
            style={[styles.sendButton, (!(result || videoResult) || loading || uploading) && styles.buttonDisabled]}
            onPress={handleClick}
            disabled={!(result || videoResult) || loading || uploading}
          >
            <Text style={styles.sendButtonText}>Отправить на бек</Text>
          </TouchableOpacity>
        )}

        {uploading && (
          <Text style={styles.uploadingText}>
            {video ? "Отправка видео..." : "Отправка изображения..."}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    gap: 16,
  },
  button: {
    backgroundColor: '#007AFF',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    minWidth: 180,
  },
  deleteButton: {
    backgroundColor: '#FF3B30',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    minWidth: 120,
  },
  sendButton: {
    backgroundColor: '#34C759',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 8,
    minWidth: 180,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '500',
    textAlign: 'center',
  },
  deleteButtonText: {
    color: 'white',
    fontSize: 15,
    fontWeight: '500',
    textAlign: 'center',
  },
  sendButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '500',
    textAlign: 'center',
  },
  mediaContainer: {
    alignItems: 'center',
    gap: 8,
  },
  media: {
    width: 240,
    height: 240,
    borderRadius: 8,
  },
  mediaLabel: {
    fontSize: 16,
    color: '#666',
  },
  uploadingText: {
    fontSize: 16,
    color: '#007AFF',
  },
});