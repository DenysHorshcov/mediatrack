import { type FormEvent, useState } from "react";
import { Image, Pencil, User } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { ApiError } from "@/lib/api";
import { type ProfileFields, validateProfileForm } from "@/lib/validation";
import { useAuth } from "@/stores/auth";

const LIST_STUBS: Array<{ status: string; label: string; description: string }> = [
  { status: "in_progress", label: "Дивлюсь / граю", description: "Що зараз в процесі" },
  { status: "planned", label: "У планах", description: "Чекає своєї черги" },
  { status: "completed", label: "Завершено", description: "Пройдено до кінця" },
  { status: "on_hold", label: "На паузі", description: "Поставлено на холд" },
  { status: "dropped", label: "Закинуто", description: "Не бачу сенсу продовжувати" },
];

function Avatar({ src, username }: { src: string | null; username: string }) {
  const [failed, setFailed] = useState(false);
  const showImage = src && !failed;
  return showImage ? (
    <img
      src={src}
      alt={username}
      onError={() => setFailed(true)}
      className="h-20 w-20 rounded-full border border-line object-cover"
    />
  ) : (
    <div className="flex h-20 w-20 items-center justify-center rounded-full border border-line bg-poster text-muted">
      <User size={36} strokeWidth={1.8} />
    </div>
  );
}

export default function ProfilePage() {
  const auth = useAuth();
  const user = auth.status === "authenticated" ? auth.user : null;

  const [editing, setEditing] = useState(false);
  const [username, setUsername] = useState(user?.username ?? "");
  const [avatarUrl, setAvatarUrl] = useState(user?.avatar_url ?? "");
  const [errors, setErrors] = useState<ProfileFields>({});
  const [submitting, setSubmitting] = useState(false);

  if (!user) return null;

  function startEditing() {
    setUsername(user!.username);
    setAvatarUrl(user!.avatar_url ?? "");
    setErrors({});
    setEditing(true);
  }

  function cancelEditing() {
    setErrors({});
    setEditing(false);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const nextErrors = validateProfileForm({ username, avatar_url: avatarUrl });
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    try {
      await auth.updateProfile({
        username: username.trim(),
        avatar_url: avatarUrl.trim() || null,
      });
      setEditing(false);
    } catch (error) {
      if (error instanceof ApiError) {
        setErrors({ ...(error.fieldErrors ?? {}), form: error.message });
      } else {
        setErrors({ form: "Не вдалося зберегти профіль" });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-10 px-8 py-12">
      <section className="rounded-field border border-line bg-panel p-6">
        {editing ? (
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="flex items-center gap-5">
              <Avatar src={avatarUrl.trim() || null} username={username || user.username} />
              <div className="flex-1 space-y-1">
                <h1 className="text-xl font-semibold text-text">Редагування профілю</h1>
                <p className="text-sm text-muted">{user.email}</p>
              </div>
            </div>

            <Input
              label="Нікнейм"
              name="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              leftIcon={<User size={18} />}
              error={errors.username}
              disabled={submitting}
            />
            <Input
              label="Посилання на аватар"
              name="avatar_url"
              type="url"
              placeholder="https://example.com/photo.png"
              value={avatarUrl}
              onChange={(e) => setAvatarUrl(e.target.value)}
              leftIcon={<Image size={18} />}
              error={errors.avatar_url}
              disabled={submitting}
            />

            {errors.form && (
              <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
                {errors.form}
              </p>
            )}

            <div className="flex gap-3">
              <Button type="submit" disabled={submitting}>
                {submitting ? "Зберігаємо…" : "Зберегти"}
              </Button>
              <Button type="button" variant="ghost" onClick={cancelEditing} disabled={submitting}>
                Скасувати
              </Button>
            </div>
          </form>
        ) : (
          <div className="flex items-center gap-5">
            <Avatar src={user.avatar_url} username={user.username} />
            <div className="flex-1">
              <h1 className="text-2xl font-semibold text-text">{user.username}</h1>
              <p className="text-sm text-muted">{user.email}</p>
            </div>
            <Button variant="ghost" onClick={startEditing}>
              <span className="inline-flex items-center gap-2">
                <Pencil size={16} />
                Редагувати
              </span>
            </Button>
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-text">Мої списки</h2>
          <p className="text-sm text-muted">Повні списки зʼявляться в наступних спринтах.</p>
        </div>
        <ul className="grid gap-3 sm:grid-cols-2">
          {LIST_STUBS.map((item) => (
            <li key={item.status}>
              <Link
                to={`/lists/${item.status}`}
                className="block rounded-field border border-line bg-bg px-4 py-3 transition hover:border-accent hover:bg-row"
              >
                <p className="font-medium text-text">{item.label}</p>
                <p className="text-sm text-muted">{item.description}</p>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
