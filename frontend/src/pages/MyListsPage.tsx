import { useEffect, useState } from "react";
import { Inbox, Search } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { LibraryCard } from "@/components/LibraryCard";
import { api, ApiError } from "@/lib/api";
import {
  LIBRARY_STATUSES,
  statusIcon,
  tabLabel,
} from "@/lib/library";
import type { LibraryStatus, LibraryTitle } from "@/types/library";
import type { SearchItemType } from "@/types/search";

const TYPE_TABS: Array<{ value: SearchItemType | "all"; label: string }> = [
  { value: "all", label: "Усе" },
  { value: "movie", label: "Фільми" },
  { value: "series", label: "Серіали" },
  { value: "game", label: "Ігри" },
];

function readStatus(raw: string | null): LibraryStatus {
  return (LIBRARY_STATUSES as readonly string[]).includes(raw ?? "")
    ? (raw as LibraryStatus)
    : "in_progress";
}

function readType(raw: string | null): SearchItemType | "all" {
  if (raw === "movie" || raw === "series" || raw === "game") return raw;
  return "all";
}

export default function MyListsPage() {
  const [params, setParams] = useSearchParams();
  const status = readStatus(params.get("status"));
  const type = readType(params.get("type"));

  const [items, setItems] = useState<LibraryTitle[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .listLibrary({ status, type: type === "all" ? undefined : type })
      .then((response) => {
        if (!cancelled) setItems(response.items);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не вдалося завантажити");
        setItems(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [status, type]);

  function setStatusTab(next: LibraryStatus) {
    const nextParams = new URLSearchParams(params);
    nextParams.set("status", next);
    setParams(nextParams, { replace: true });
  }

  function setTypeTab(next: SearchItemType | "all") {
    const nextParams = new URLSearchParams(params);
    if (next === "all") nextParams.delete("type");
    else nextParams.set("type", next);
    setParams(nextParams, { replace: true });
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-8 py-10">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-text">Мої списки</h1>
        <p className="text-sm text-muted">
          Все, що ви позначили статусом на сторінках тайтлів.
        </p>
      </div>

      <StatusTabs value={status} onChange={setStatusTab} />

      <TypeTabs value={type} onChange={setTypeTab} />

      {loading && items === null && <ListSkeleton />}
      {error && (
        <p role="alert" className="rounded-field bg-error-bg px-4 py-3 text-sm text-error">
          {error}
        </p>
      )}
      {items !== null && items.length === 0 && !loading && <EmptyState />}
      {items !== null && items.length > 0 && (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
          {items.map((item) => (
            <li key={item.id}>
              <LibraryCard item={item} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function StatusTabs({
  value,
  onChange,
}: {
  value: LibraryStatus;
  onChange: (next: LibraryStatus) => void;
}) {
  return (
    <div
      role="tablist"
      aria-label="Статус"
      className="inline-flex flex-wrap gap-1 rounded-field border border-line bg-panel p-1"
    >
      {LIBRARY_STATUSES.map((status) => {
        const Icon = statusIcon(status);
        const isActive = status === value;
        return (
          <button
            key={status}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(status)}
            className={[
              "inline-flex h-9 items-center gap-2 rounded-field px-3 text-sm font-medium transition",
              isActive
                ? "bg-accent-soft text-accent-dark"
                : "text-muted hover:bg-row hover:text-accent-dark",
            ].join(" ")}
          >
            <Icon size={14} />
            {tabLabel(status)}
          </button>
        );
      })}
    </div>
  );
}

function TypeTabs({
  value,
  onChange,
}: {
  value: SearchItemType | "all";
  onChange: (next: SearchItemType | "all") => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {TYPE_TABS.map((tab) => {
        const isActive = tab.value === value;
        return (
          <button
            key={tab.value}
            type="button"
            onClick={() => onChange(tab.value)}
            className={[
              "h-8 rounded-full border px-3 text-xs font-medium transition",
              isActive
                ? "border-accent bg-accent-soft text-accent-dark"
                : "border-line bg-bg text-muted hover:border-accent hover:text-accent-dark",
            ].join(" ")}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

function ListSkeleton() {
  return (
    <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
      {Array.from({ length: 10 }, (_, index) => (
        <li
          key={index}
          className="aspect-[2/3] animate-pulse rounded-field bg-poster"
        />
      ))}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-field border border-dashed border-line bg-panel px-6 py-12 text-center">
      <span className="text-muted">
        <Inbox size={32} strokeWidth={1.6} />
      </span>
      <p className="text-base font-medium text-text">Поки нічого немає</p>
      <p className="max-w-md text-sm text-muted">
        Знайдіть тайтл і поставте йому статус — він зʼявиться тут.
      </p>
      <Link
        to="/search"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:text-accent-dark"
      >
        <Search size={14} />
        Перейти до пошуку
      </Link>
    </div>
  );
}
