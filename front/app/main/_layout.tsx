// app/(main)/_layout.tsx
import {Stack, Tabs} from "expo-router";

export default function MainLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" options={{ title: "Главная" }} />
    </Stack>
  );
}
