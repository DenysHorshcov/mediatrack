import { type FormEvent, useState } from "react";
import { Mail } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AuthLayout } from "@/components/AuthLayout";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { PasswordInput } from "@/components/PasswordInput";
import { ApiError } from "@/lib/api";
import { type LoginFields, validateLoginForm } from "@/lib/validation";
import { useAuth } from "@/stores/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<LoginFields>({});
  const [submitting, setSubmitting] = useState(false);

  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation() as { state?: { from?: string } };
  const redirectTo = location.state?.from ?? "/";

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validateLoginForm({ email, password });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await auth.login({ email: email.trim(), password });
      navigate(redirectTo, { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({ ...(error.fieldErrors ?? {}), form: error.message });
      } else {
        setErrors({ form: "Не вдалося увійти. Спробуйте ще раз." });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Вхід" subtitle="Увійдіть, щоб продовжити стежити за своєю бібліотекою.">
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <Input
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          leftIcon={<Mail size={18} />}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
          disabled={submitting}
        />
        <PasswordInput
          label="Пароль"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
          disabled={submitting}
        />

        {errors.form && (
          <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
            {errors.form}
          </p>
        )}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Входимо…" : "Увійти"}
        </Button>
      </form>

      <p className="text-sm text-muted">
        Ще немає акаунта?{" "}
        <Link to="/register" className="font-medium text-accent hover:text-accent-dark">
          Зареєструватися
        </Link>
      </p>
    </AuthLayout>
  );
}
