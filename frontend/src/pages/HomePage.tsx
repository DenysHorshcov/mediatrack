import { useAuth } from "@/stores/auth";

export default function HomePage() {
  const auth = useAuth();
  const user = auth.status === "authenticated" ? auth.user : null;

  return (
    <div className="mx-auto max-w-3xl px-8 py-12">
      <h1 className="text-3xl font-semibold text-text">
        Вітаємо{user ? `, ${user.username}` : ""}!
      </h1>
      <p className="mt-2 text-muted">
        Пошук, профіль і списки з'являться в наступних спринтах.
      </p>
    </div>
  );
}
