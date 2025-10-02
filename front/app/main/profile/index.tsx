import {useEffect, useState} from "react";
import {
  View,
  Text,
  ActivityIndicator,
  StyleSheet,
  FlatList,
  Pressable,
  SafeAreaView,
} from "react-native";
import {Link} from "expo-router";
import {getObjects} from "@/api/actions";
import {useUserStore, useObjectsStore} from "@/store";

type Obj = { object_id: number; name: string; status: string };

export default function ProfileObjectsScreen() {
  const [data, setData] = useState<Obj[] | null>(null);
  const [loading, setLoading] = useState(true);
  const user_id = useUserStore((s) => s.user.user_id);
  const setObjects = useObjectsStore((s) => s.setObjects);
  const setActiveObject = useObjectsStore((s) => s.setActiveObject);

  useEffect(() => {
    (async () => {
      try {
        const list = await getObjects({limit: 100, offset: 0, user_id});
        if (Array.isArray(list)) {
          setData(list);
          setObjects(list);
        } else {
          throw Error("Not a list");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [user_id]);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator/>
        <Text style={styles.muted}>Загрузка…</Text>
      </View>
    );
  }

  if (!data || data.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.empty}>Нет объектов</Text>
        <Text style={styles.muted}>Попробуйте обновить позже</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Небольшой заголовок — без визуального шума */}
      <Text style={styles.header}>Ваши объекты</Text>

      <FlatList
        data={data}
        keyExtractor={(item) => String(item.object_id)}
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={() => <View style={styles.separator}/>}
        renderItem={({item}) => (
          <Link
            href={{
              pathname: "/main/profile/[objectId]",
              params: {objectId: item.object_id},
            }}
            onPress={() => setActiveObject(item)}

            asChild
          >
            <Pressable
              style={({pressed}) => [
                styles.item,
                pressed && styles.itemPressed,
              ]}
              android_ripple={{color: "#0000000f"}}
              accessibilityRole="button"
              accessibilityLabel={item.name}
            >
              <View style={styles.itemTextWrap}>
                <Text style={styles.itemTitle} numberOfLines={1}>
                  {item.name}
                </Text>
                {!!item.status && (
                  <Text style={styles.itemSubtitle} numberOfLines={1}>
                    {item.status}
                  </Text>
                )}
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
  container: {
    flex: 1,
    backgroundColor: "#F9FAFB", // нейтральный фон
    paddingBlock: 40,
    overflow: 'scroll',
  },
  header: {
    fontSize: 18,
    fontWeight: "600",
    color: "#111827",
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  listContent: {
    padding: 16,
    paddingTop: 8,
  },
  separator: {
    height: 12,
  },
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
    // тень минимальная, чтобы не шумела (iOS)
    shadowColor: "#000",
    shadowOpacity: 0.03,
    shadowRadius: 6,
    shadowOffset: {width: 0, height: 2},
    // Android “тень”
    elevation: 1,
  },
  itemPressed: {
    opacity: 0.95,
  },
  itemTextWrap: {
    flex: 1,
    paddingRight: 8,
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#111827",
    marginBottom: 2,
  },
  itemSubtitle: {
    fontSize: 12,
    color: "#6B7280",
  },
  chevron: {
    fontSize: 20,
    color: "#9CA3AF",
    paddingLeft: 4,
  },
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
  muted: {
    fontSize: 12,
    color: "#6B7280",
    textAlign: "center",
  },
});
