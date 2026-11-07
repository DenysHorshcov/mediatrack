import { useEffect, useState } from "react";
import { CheckCircle2, Film, Gamepad2, Star, Tv } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Stats } from "@/types/stats";

const TYPE_ROWS: Array<{
  key: keyof Stats["by_type"];
  label: string;
  icon: typeof Film;
}> = [
  { key: "movie", label: "Фільми", icon: Film },
  { key: "series", label: "Серіали", icon: Tv },
  { key: "game", label: "Ігри", icon: Gamepad2 },
];

const STATUS_ROWS: Array<{
  key: keyof Stats["by_status"];
  label: string;
}> = [
  { key: "in_progress", label: "В процесі" },
  { key: "planned", label: "У планах" },
  { key: "completed", label: "Завершено" },
  { key: "on_hold", label: "На паузі" },
  { key: "dropped", label: "Закинуто" },
];

export function StatsBlock() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err.message : "Не вдалося завантажити статистику");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <section className="rounded-field border border-line bg-panel p-6">
        <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
          {error}
        </p>
      </section>
    );
  }

  if (stats === null) {
    return (
      <section className="rounded-field border border-line bg-panel p-6">
        <div className="h-24 animate-pulse rounded-field bg-poster" />
      </section>
    );
  }

  const maxTypeCount = Math.max(1, ...TYPE_ROWS.map((row) => stats.by_type[row.key]));

  return (
    <section className="space-y-5 rounded-field border border-line bg-panel p-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">Статистика</h2>
          <p className="text-sm text-muted">
            {stats.total > 0
              ? "Що у вашому обліку по типах і статусах."
              : "Поки порожньо — додайте перший тайтл з пошуку."}
          </p>
        </div>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryCard label="Усього тайтлів" value={stats.total} />
        <SummaryCard
          label="Середня оцінка"
          value={stats.average_rating === null ? "—" : stats.average_rating.toFixed(1)}
          icon={<Star size={14} />}
        />
        <SummaryCard
          label="Завершено цього року"
          value={stats.completed_this_year}
          icon={<CheckCircle2 size={14} />}
        />
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-medium text-text">За типом</h3>
        <ul className="space-y-2">
          {TYPE_ROWS.map(({ key, label, icon: Icon }) => {
            const value = stats.by_type[key];
            const percent = Math.round((value / maxTypeCount) * 100);
            return (
              <li key={key} className="flex items-center gap-3 text-sm text-text">
                <span className="inline-flex w-24 items-center gap-1.5 text-muted">
                  <Icon size={14} />
                  {label}
                </span>
                <span
                  className="relative h-3 flex-1 overflow-hidden rounded-full bg-row"
                  aria-hidden
                >
                  <span
                    className="block h-full rounded-full bg-accent transition-[width]"
                    style={{ width: value === 0 ? "0%" : `${Math.max(percent, 6)}%` }}
                  />
                </span>
                <span className="w-8 text-right tabular-nums text-muted">{value}</span>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium text-text">За статусом</h3>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {STATUS_ROWS.map(({ key, label }) => (
            <li
              key={key}
              className="rounded-field border border-line bg-bg px-3 py-2 text-center"
            >
              <p className="text-lg font-semibold text-text">{stats.by_status[key]}</p>
              <p className="text-xs text-muted">{label}</p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function SummaryCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
}) {
  return (
    <div className="rounded-field border border-line bg-bg px-4 py-3">
      <p className="inline-flex items-center gap-1.5 text-xs text-muted">
        {icon}
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-text">{value}</p>
    </div>
  );
}
