import { useEffect, useState } from "react";
import { CheckCheck, Minus, Plus, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Season } from "@/types/season";
import type { TitleProvider } from "@/types/title";

type Props = {
  titleId: string;
  provider: TitleProvider;
  externalId: string;
  currentSeason: number | null;
  currentEpisode: number | null;
  onChange: (season: number | null, episode: number | null) => void;
  onLastEpisode: () => Promise<void> | void;
};

function _episodesWord(count: number): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  if (mod100 >= 11 && mod100 <= 14) return "епізодів";
  if (mod10 === 1) return "епізод";
  if (mod10 >= 2 && mod10 <= 4) return "епізоди";
  return "епізодів";
}


export function ProgressSelector({
  titleId,
  provider,
  externalId,
  currentSeason,
  currentEpisode,
  onChange,
  onLastEpisode,
}: Props) {
  const [seasons, setSeasons] = useState<Season[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [askComplete, setAskComplete] = useState(false);

  useEffect(() => {
    if (provider !== "tmdb") return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getSeasons(provider, "series", externalId)
      .then((response) => {
        if (!cancelled) setSeasons(response.seasons);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Не вдалося завантажити сезони");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [provider, externalId]);

  const season = currentSeason ?? seasons?.[0]?.season_number ?? 1;
  const episode = currentEpisode ?? 1;
  const seasonInfo = seasons?.find((s) => s.season_number === season);
  const maxEpisode = seasonInfo?.episode_count ?? null;
  const isLastSeason =
    seasons !== null && seasons[seasons.length - 1]?.season_number === season;
  const isLastEpisode = maxEpisode !== null && episode === maxEpisode;
  const atAbsoluteEnd = isLastSeason && isLastEpisode;

  async function save(nextSeason: number, nextEpisode: number) {
    setSaving(true);
    setError(null);
    try {
      await api.setLibraryProgress(titleId, {
        season: nextSeason,
        episode: nextEpisode,
      });
      onChange(nextSeason, nextEpisode);
      const season = seasons?.find((s) => s.season_number === nextSeason);
      const last = seasons?.[seasons.length - 1];
      if (
        season &&
        last &&
        season.season_number === last.season_number &&
        nextEpisode === season.episode_count
      ) {
        setAskComplete(true);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти прогрес");
    } finally {
      setSaving(false);
    }
  }

  async function clearProgress() {
    setSaving(true);
    setError(null);
    try {
      await api.setLibraryProgress(titleId, { season: null, episode: null });
      onChange(null, null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося прибрати прогрес");
    } finally {
      setSaving(false);
    }
  }

  function selectSeason(next: number) {
    void save(next, 1);
  }

  function selectEpisode(next: number) {
    void save(season, next);
  }

  function bumpEpisode(delta: number) {
    const next = episode + delta;
    if (next < 1) return;
    if (maxEpisode !== null && next > maxEpisode) return;
    void save(season, next);
  }

  async function confirmCompleted() {
    setAskComplete(false);
    try {
      await onLastEpisode();
    } catch {
      // ignore — parent handles errors through its own UI
    }
  }

  if (provider !== "tmdb") return null;

  return (
    <div className="space-y-3 rounded-field border border-line bg-panel p-4">
      <div>
        <p className="text-sm font-medium text-text">Прогрес серій</p>
        <p className="text-xs text-muted">Відмічайте сезон і епізод, на яких ви зупинились.</p>
      </div>

      {loading && seasons === null && (
        <p className="text-sm text-muted">Завантажуємо сезони…</p>
      )}

      {seasons && seasons.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto]">
          <label className="flex flex-col gap-1 text-xs text-muted">
            Сезон
            <select
              value={season}
              disabled={saving}
              onChange={(e) => selectSeason(Number(e.target.value))}
              className="h-9 rounded-field border border-field bg-bg px-2 text-sm text-text"
            >
              {seasons.map((s) => (
                <option key={s.season_number} value={s.season_number}>
                  {s.name || `Сезон ${s.season_number}`} ({s.episode_count} {_episodesWord(s.episode_count)})
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs text-muted">
            Епізод
            <select
              value={episode}
              disabled={saving || maxEpisode === null}
              onChange={(e) => selectEpisode(Number(e.target.value))}
              className="h-9 rounded-field border border-field bg-bg px-2 text-sm text-text"
            >
              {Array.from({ length: maxEpisode ?? 0 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  Епізод {n}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-end gap-1">
            <button
              type="button"
              onClick={() => bumpEpisode(-1)}
              disabled={saving || episode <= 1}
              aria-label="−1 епізод"
              className="inline-flex h-9 w-9 items-center justify-center rounded-field border border-line text-muted transition hover:border-accent hover:text-accent-dark disabled:opacity-60"
            >
              <Minus size={14} />
            </button>
            <button
              type="button"
              onClick={() => bumpEpisode(1)}
              disabled={saving || (maxEpisode !== null && episode >= maxEpisode) || atAbsoluteEnd}
              aria-label="+1 епізод"
              className="inline-flex h-9 w-9 items-center justify-center rounded-field border border-accent bg-accent-soft text-accent-dark transition hover:bg-accent hover:text-white disabled:opacity-60"
            >
              <Plus size={14} />
            </button>
            {currentSeason !== null && (
              <button
                type="button"
                onClick={() => void clearProgress()}
                disabled={saving}
                aria-label="Прибрати прогрес"
                title="Прибрати прогрес"
                className="inline-flex h-9 w-9 items-center justify-center rounded-field border border-line bg-bg text-muted transition hover:border-error hover:text-error disabled:opacity-60"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {askComplete && (
        <div className="space-y-2 rounded-field border border-accent bg-accent-soft/60 p-3">
          <p className="text-sm font-medium text-accent-dark">
            <CheckCheck size={16} className="inline mr-1" />
            Ви на останньому епізоді останнього сезону. Поставити «Завершено»?
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => void confirmCompleted()}
              className="inline-flex h-9 items-center rounded-field bg-accent px-3 text-sm font-medium text-white hover:bg-accent-dark"
            >
              Поставити «Завершено»
            </button>
            <button
              type="button"
              onClick={() => setAskComplete(false)}
              className="inline-flex h-9 items-center rounded-field border border-line bg-bg px-3 text-sm font-medium text-muted hover:text-accent-dark"
            >
              Ні, дякую
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
