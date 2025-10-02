// app/(auth)/test.tsx
import { useEffect, useState } from "react";
import { Redirect } from "expo-router";

export default function AuthIndex() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setReady(true), 3000);
    return () => clearTimeout(timer);
  }, []);

  if (!ready) return null; // или спиннер
  return <Redirect href="/auth/login" />;
}
