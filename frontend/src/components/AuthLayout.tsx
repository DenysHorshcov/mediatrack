import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";

type Props = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function AuthLayout({ title, subtitle, children }: Props) {
  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2">
      <aside className="hidden md:flex flex-col justify-between bg-accent-dark text-white p-12">
        <div className="flex items-center gap-2 text-xl font-semibold">
          <Logo tone="light" size={22} />
          MediaTrack
        </div>

        <div className="max-w-md space-y-4">
          <h2 className="text-3xl font-semibold leading-tight">
            Один профіль для фільмів, серіалів та ігор
          </h2>
          <p className="text-white/80 leading-relaxed">
            Шукайте тайтли, зберігайте статуси, оцінюйте й ведіть прогрес серій.
            Весь ваш медіатрек — в одному місці і українською.
          </p>
        </div>

        <div />
      </aside>

      <main className="flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md space-y-6">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold text-text">{title}</h1>
            <p className="text-muted">{subtitle}</p>
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
