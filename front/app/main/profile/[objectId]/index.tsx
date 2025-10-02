import { useEffect, useState } from "react";
import {
  View,
  Text,
  ActivityIndicator,
  StyleSheet,
  FlatList,
  Pressable,
  SafeAreaView,
} from "react-native";
import { Link } from "expo-router";
import { getSubObjects } from "@/api/actions";
import { useObjectsStore, type ISubObject } from "@/store";

export default function SubObjectsScreen() {
  const activeObject = useObjectsStore((s) => s.activeObject);
  const object_id = activeObject?.object_id;

  const setSubObjects = useObjectsStore((s) => s.setSubObjects);
  const setActiveSubObject = useObjectsStore((s) => s.setActiveSubObject);

  const [data, setData] = useState<ISubObject[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (object_id == null) return;
    (async () => {
      try {
        const {subobjects} = await getSubObjects({ limit: 100, offset: 0, object_id });


        setData(subobjects);
        setSubObjects(subobjects);
      } finally {
        setLoading(false);
      }
    })();
  }, [object_id, setSubObjects]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
        <Text style={styles.muted}>Загрузка…</Text>
      </View>
    );
  }

  if (!data || data.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.empty}>Нет субобъектов</Text>
        <Text style={styles.muted}>Выберите другой объект или попробуйте позже</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.header}>{activeObject?.name ?? "Субобъекты"}</Text>

      <FlatList
        data={data}
        keyExtractor={(item) => String(item.subobject_id)}
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        renderItem={({ item }) => (
          <Link
            href={{
              pathname: "/main/profile/[objectId]/[subObjectId]",
              params: {
                objectId: String(item.object_id),
                subObjectId: String(item.subobject_id),
              },
            }}
            onPress={() => setActiveSubObject(item)}
            asChild
          >
            <Pressable
              style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
              android_ripple={{ color: "#0000000f" }}
              accessibilityRole="button"
              accessibilityLabel={item.name}
            >
              <View style={styles.itemTextWrap}>
                <Text style={styles.itemTitle} numberOfLines={1}>
                  {item.name}
                </Text>
                {/* Если нужен подзаголовок/статус — выбери нужное поле */}
                {/* <Text style={styles.itemSubtitle} numberOfLines={1}>
                  {item.status_inspector}
                </Text> */}
              </View>
              <Text style={styles.chevron}>›</Text>
            </Pressable>
          </Link>
        )}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB", paddingVertical: 40 },
  header: {
    fontSize: 18,
    fontWeight: "600",
    color: "#111827",
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  listContent: { padding: 16, paddingTop: 8 },
  separator: { height: 12 },
  item: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#E5E7EB",
    paddingHorizontal: 14,
    paddingVertical: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    shadowColor: "#000",
    shadowOpacity: 0.03,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 1,
  },
  itemPressed: { opacity: 0.95 },
  itemTextWrap: { flex: 1, paddingRight: 8 },
  itemTitle: { fontSize: 16, fontWeight: "600", color: "#111827", marginBottom: 2 },
  itemSubtitle: { fontSize: 12, color: "#6B7280" },
  chevron: { fontSize: 20, color: "#9CA3AF", paddingLeft: 4 },
  centered: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    backgroundColor: "#F9FAFB",
  },
  empty: {
    fontSize: 16,
    fontWeight: "600",
    color: "#111827",
    marginBottom: 4,
    textAlign: "center",
  },
  muted: { fontSize: 12, color: "#6B7280", textAlign: "center" },
});
