import React from 'react';
import {View, Text, TextInput, TouchableOpacity, StyleSheet} from 'react-native';
import {useRouter} from "expo-router";
import {useForm, Controller} from "react-hook-form";
import {login} from "@/api/actions";
import {LoginRequest} from "@/dto/auth.dto";
import {useUserStore} from "@/store/";

export default function LoginScreen() {
  const router = useRouter();
  const {
    control,
    handleSubmit,
    formState: {errors, isSubmitting},
  } = useForm<LoginRequest>({
    defaultValues: {
      name: '',
      password: '',
    },
  });

  const setUser = useUserStore((state) => state.setUser);
  const user = useUserStore((state) => state.user);
  const onSubmit = async (data: LoginRequest) => {

    try {
      const result = await login(data);
      setUser(result);
      router.replace("/main/profile");
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Вход</Text>

      <Controller
        control={control}
        name="name"
        rules={{
          required: 'Введите имя',
        }}
        render={({field: {onChange, onBlur, value}}) => (
          <>
            <TextInput
              style={[styles.input, errors.name && styles.inputError]}
              placeholder="Имя"
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              autoCapitalize="words"
              editable={!isSubmitting}
            />
            {errors.name && (
              <Text style={styles.errorText}>{errors.name.message}</Text>
            )}
          </>
        )}
      />

      <Controller
        control={control}
        name="password"
        rules={{
          required: 'Введите пароль',
        }}
        render={({field: {onChange, onBlur, value}}) => (
          <>
            <TextInput
              style={[styles.input, errors.password && styles.inputError]}
              placeholder="Пароль"
              value={value}
              onChangeText={onChange}
              onBlur={onBlur}
              secureTextEntry
              editable={!isSubmitting}
            />
            {errors.password && (
              <Text style={styles.errorText}>{errors.password.message}</Text>
            )}
          </>
        )}
      />

      <TouchableOpacity
        style={[styles.button, isSubmitting && styles.buttonDisabled]}
        onPress={handleSubmit(onSubmit)}
        disabled={isSubmitting}
      >
        <Text style={styles.buttonText}>
          {isSubmitting ? 'Загрузка...' : 'Войти'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#f5f5f5',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 24,
  },
  input: {
    width: '100%',
    height: 48,
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    paddingHorizontal: 16,
    marginBottom: 8,
    backgroundColor: '#fff',
  },
  inputError: {
    borderColor: '#ff3b30',
  },
  errorText: {
    width: '100%',
    color: '#ff3b30',
    fontSize: 12,
    marginBottom: 12,
    paddingLeft: 4,
  },
  button: {
    width: '100%',
    height: 48,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});