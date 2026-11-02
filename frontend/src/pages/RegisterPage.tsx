import { type FormEvent, useState } from "react";
import { Mail, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { PasswordInput } from "@/components/PasswordInput";
import { ApiError } from "@/lib/api";
import {
  type RegisterFields,
  validateRegisterForm,
} from "@/lib/validation";
import { useAuth } from "@/stores/auth";

type FormValues = {
  email: string;
  username: string;
  password: string;
  passwordConfirm: string;
};

export default function RegisterPage() {
  const [values, setValues] = useState<FormValues>({
    email: "",
    username: "",
    password: "",
    passwordConfirm: "",
  });
  const [errors, setErrors] = useState<RegisterFields>({});
  const [submitting, setSubmitting] = useState(false);

  const auth = useAuth();
  const navigate = useNavigate();

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validateRegisterForm(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await auth.register({
        email: values.email.trim(),
        username: values.username.trim(),
        password: values.password,
      });
      navigate("/", { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({ ...(error.fieldErrors ?? {}), form: error.message });
      } else {
        setErrors({ form: "Не вдалося створити акаунт. Спробуйте ще раз." });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      title="Реєстрація"
      subtitle="Створіть акаунт, щоб вести облік фільмів, серіалів та ігор."
    >
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          leftIcon={<Mail size={18} />}
          value={values.email}
          onChange={(e) => update("email", e.target.value)}
          error={errors.email}
          disabled={submitting}
        />
        <Input
          label="Нікнейм"
          name="username"
          autoComplete="username"
          leftIcon={<User size={18} />}
          value={values.username}
          onChange={(e) => update("username", e.target.value)}
          error={errors.username}
          disabled={submitting}
        />
        <PasswordInput
          label="Пароль"
          name="password"
          autoComplete="new-password"
          value={values.password}
          onChange={(e) => update("password", e.target.value)}
          error={errors.password}
          disabled={submitting}
        />
        <PasswordInput
          label="Повторіть пароль"
          name="passwordConfirm"
          autoComplete="new-password"
          value={values.passwordConfirm}
          onChange={(e) => update("passwordConfirm", e.target.value)}
          error={errors.passwordConfirm}
          disabled={submitting}
        />

        {errors.form && (
          <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
            {errors.form}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Створюємо…" : "Створити акаунт"}
        </Button>
      </form>

      <p className="text-sm text-muted">
        Вже маєте акаунт?{" "}
        <Link to="/login" className="font-medium text-accent hover:text-accent-dark">
          Увійти
        </Link>
      </p>
    </AuthLayout>
  );
}
