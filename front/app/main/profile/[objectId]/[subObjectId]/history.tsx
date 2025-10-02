// app/main/profile/[objectId]/[subObjectId]/history.tsx
import { useEffect, useState } from "react";
import { View, Text, ActivityIndicator } from "react-native";
import { useLocalSearchParams } from "expo-router";

type HistoryItem = { id: string; status: string; createdAt: string };

export default function HistoryScreen() {
  const { objectId, subObjectId } = useLocalSearchParams<{ objectId: string; subObjectId: string }>();
  const [data, setData] = useState<HistoryItem[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        // TODO: подставь реальный запрос истории
        // const list = await getHistory({ objectId, subObjectId });
        setData([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [objectId, subObjectId]);

  if (loading) return <ActivityIndicator />;
  if (!data?.length) return <Text>История пустая</Text>;

  return (
    <View>
      {data.map((h) => (
        <View key={h.id}>
          <Text>{h.status}</Text>
          <Text>{h.createdAt}</Text>
        </View>
      ))}
    </View>
  );
}
