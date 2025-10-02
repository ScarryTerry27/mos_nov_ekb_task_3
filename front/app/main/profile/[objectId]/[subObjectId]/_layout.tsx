// app/main/profile/[objectId]/[subObjectId]/_layout.tsx
import { Stack } from "expo-router";

export default function SubObjectStackLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index"   options={{ title: "Субобъект" }} />
      <Stack.Screen name="check"   options={{ title: "Проверка" }} />
      <Stack.Screen name="history" options={{ title: "История" }} />
    </Stack>
  );
}
