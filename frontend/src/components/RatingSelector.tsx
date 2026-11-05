import { Star, X } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";

type Props = {
  titleId: string;
  rating: number | null;
  onChange: (next: number | null) => void;
};

const STARS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

export function RatingSelector({ titleId, rating, onChange }: Props) {
  const [hovered, setHovered] = useState<number | null>(null);
  const [pending, setPending] = useState<number | "clear" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const highlighted = hovered ?? rating ?? 0;

  async function setRating(next: number) {
    if (next === rating) return;
    setPending(next);
    setError(null);
    try {
      await api.setLibraryRating(titleId, next);
      onChange(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти");
    } finally {
      setPending(null);
    }
  }

  async function clearRating() {
    if (rating === null) return;
    setPending("clear");
    setError(null);
    try {
      await api.setLibraryRating(titleId, null);
      onChange(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося прибрати");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-3 rounded-field border border-line bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-text">Моя оцінка</p>
          <p className="text-xs text-muted">Клацніть по зірці від 1 до 10, щоб оцінити.</p>
        </div>
        {rating !== null && (
          <span className="rounded-field bg-accent-soft px-2 py-1 text-sm font-semibold text-accent-dark">
            {rating}
          </span>
        )}
      </div>

      <div
        className="flex flex-wrap items-center gap-1"
        role="radiogroup"
        aria-label="Оцінка"
        onMouseLeave={() => setHovered(null)}
      >
        {STARS.map((value) => {
          const isFilled = value <= highlighted;
          const isPending = pending === value;
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={rating === value}
              aria-label={`${value} з 10`}
              disabled={pending !== null}
              onMouseEnter={() => setHovered(value)}
              onFocus={() => setHovered(value)}
              onBlur={() => setHovered(null)}
              onClick={() => void setRating(value)}
              className={[
                "inline-flex h-8 w-8 items-center justify-center rounded-field transition disabled:opacity-60",
                isFilled
                  ? "text-accent-dark"
                  : "text-muted hover:text-accent-dark",
                isPending ? "animate-pulse" : "",
              ].join(" ")}
            >
              <Star
                size={20}
                strokeWidth={1.6}
                fill={isFilled ? "currentColor" : "none"}
              />
            </button>
          );
        })}
        {rating !== null && (
          <button
            type="button"
            onClick={() => void clearRating()}
            disabled={pending !== null}
            aria-label="Прибрати оцінку"
            title="Прибрати оцінку"
            className="ml-1 inline-flex h-8 w-8 items-center justify-center rounded-field border border-line bg-bg text-muted transition hover:border-error hover:text-error disabled:opacity-60"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {error && (
        <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
          {error}
        </p>
      )}
    </div>
  );
}
