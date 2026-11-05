import { useEffect, useState } from "react";
import { Search, SearchX } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { Input } from "@/components/Input";
import { SearchCard } from "@/components/SearchCard";
import { SearchFilterTabs } from "@/components/SearchFilterTabs";
import { api, ApiError } from "@/lib/api";
import type { SearchFilter, SearchItem } from "@/types/search";

const DEBOUNCE_MS = 300;
const VALID_FILTERS: SearchFilter[] = ["all", "movie", "series", "game"];

function readFilter(raw: string | null): SearchFilter {
  return VALID_FILTERS.includes(raw as SearchFilter) ? (raw as SearchFilter) : "all";
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const urlQuery = (params.get("q") ?? "").trim();
  const filter = readFilter(params.get("type"));

  const [input, setInput] = useState(params.get("q") ?? "");
  const [results, setResults] = useState<SearchItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Push input -> URL after debounce
  useEffect(() => {
    const trimmed = input.trim();
    const t = window.setTimeout(() => {
      if (trimmed === urlQuery) return;
      const next = new URLSearchParams(params);
      if (trimmed) next.set("q", trimmed);
      else next.delete("q");
      setParams(next, { replace: true });
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input]);

  // Fetch when URL query or filter changes
  useEffect(() => {
    if (!urlQuery) {
      setResults(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .search(urlQuery, filter)
      .then((response) => {
        if (!cancelled) setResults(response.results);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не вдалося завантажити результати");
        setResults(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [urlQuery, filter]);

  function handleFilterChange(next: SearchFilter) {
    const nextParams = new URLSearchParams(params);
    if (next === "all") nextParams.delete("type");
    else nextParams.set("type", next);
    setParams(nextParams, { replace: true });
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-8 py-10">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-text">Пошук</h1>
        <p className="text-sm text-muted">
          Шукайте фільми, серіали та ігри. Назви українською беремо з TMDB, ігри — з RAWG (англійською).
        </p>
      </div>

      <Input
        label="Запит"
        name="q"
        type="search"
        placeholder="Наприклад: Матриця"
        autoFocus
        leftIcon={<Search size={18} />}
        value={input}
        onChange={(event) => setInput(event.target.value)}
      />

      <SearchFilterTabs value={filter} onChange={handleFilterChange} />

      <SearchResults
        query={urlQuery}
        loading={loading}
        error={error}
        results={results}
      />
    </div>
  );
}

type ResultsProps = {
  query: string;
  loading: boolean;
  error: string | null;
  results: SearchItem[] | null;
};

function SearchResults({ query, loading, error, results }: ResultsProps) {
  if (!query) {
    return (
      <EmptyState
        icon={<Search size={32} strokeWidth={1.6} />}
        title="Введіть запит, щоб почати"
        description="Шукаємо у TMDB (фільми, серіали) і RAWG (ігри). Фільтр згори — щоб звузити."
      />
    );
  }
  if (loading && results === null) {
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
  if (error) {
    return (
      <p role="alert" className="rounded-field bg-error-bg px-4 py-3 text-sm text-error">
        {error}
      </p>
    );
  }
  if (results && results.length === 0) {
    return (
      <EmptyState
        icon={<SearchX size={32} strokeWidth={1.6} />}
        title="Нічого не знайдено"
        description={`За запитом «${query}» результатів немає. Спробуйте інакше або поміняйте фільтр.`}
      />
    );
  }
  if (results && results.length > 0) {
    return (
      <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
        {results.map((item) => (
          <li key={`${item.type}-${item.id}`}>
            <SearchCard item={item} />
          </li>
        ))}
      </ul>
    );
  }
  return null;
}

function EmptyState({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-field border border-dashed border-line bg-panel px-6 py-10 text-center">
      <span className="text-muted">{icon}</span>
      <p className="text-base font-medium text-text">{title}</p>
      <p className="max-w-md text-sm text-muted">{description}</p>
    </div>
  );
}
