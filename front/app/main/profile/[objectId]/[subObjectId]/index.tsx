// app/main/profile/[objectId]/[subObjectId]/index.tsx
import { SafeAreaView, View, Text, StyleSheet, Pressable } from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useObjectsStore } from "@/store";

export default function SubObjectActionsScreen() {
  const router = useRouter();
  const { objectId, subObjectId } = useLocalSearchParams<{
    objectId: string;
    subObjectId: string;
  }>();

  const sub = useObjectsStore((s) => s.activeSubObject);
  const title = sub?.name ?? "Субобъект";

  const goHistory = () =>
    router.push({
      pathname: "/main/profile/[objectId]/[subObjectId]/history",
      params: { objectId, subObjectId },
    });

  const goCheck = () =>
    router.push({
      pathname: "/main/profile/[objectId]/[subObjectId]/check",
      params: { objectId, subObjectId },
    });

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.header}>{title}</Text>

      <View style={styles.card}>
        <Text style={styles.caption}>Выберите действие</Text>

        <Pressable style={({pressed}) => [styles.actionBtn, pressed && styles.pressed]} onPress={goCheck}>
          <Text style={styles.actionText}>Начать проверку</Text>
        </Pressable>

        <Pressable style={({pressed}) => [styles.actionBtn, pressed && styles.pressed]} onPress={goHistory}>
          <Text style={styles.actionText}>История</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB", paddingVertical: 40 },
  header: {
    fontSize: 18, fontWeight: "600", color: "#111827",
    paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12,
  },
  card: {
    marginHorizontal: 16, backgroundColor: "#fff", borderRadius: 12,
    borderWidth: 1, borderColor: "#E5E7EB", padding: 16,
    shadowColor: "#000", shadowOpacity: 0.03, shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 }, elevation: 1,
  },
  caption: { fontSize: 14, color: "#6B7280", marginBottom: 12 },
  actionBtn: {
    backgroundColor: "#111827", borderRadius: 10, paddingVertical: 12, paddingHorizontal: 14,
    alignItems: "center", justifyContent: "center", marginBottom: 8,
  },
  pressed: { opacity: 0.9 },
  actionText: { color: "#fff", fontWeight: "700", fontSize: 14 },
});
