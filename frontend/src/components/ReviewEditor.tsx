import { Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";

const MAX_REVIEW_LENGTH = 2000;

type Props = {
  titleId: string;
  review: string | null;
  reviewUpdatedAt: string | null;
  onChange: (next: { review: string | null; reviewUpdatedAt: string | null }) => void;
};

type Mode = "idle" | "editing";

function formatUpdated(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString("uk-UA", { dateStyle: "medium", timeStyle: "short" });
}

export function ReviewEditor({ titleId, review, reviewUpdatedAt, onChange }: Props) {
  const [mode, setMode] = useState<Mode>(review === null ? "editing" : "idle");
  const [draft, setDraft] = useState(review ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = draft.trim();
  const canSave = trimmed.length > 0 && trimmed.length <= MAX_REVIEW_LENGTH && trimmed !== review;
  const remaining = MAX_REVIEW_LENGTH - draft.length;
  const updatedLabel = formatUpdated(reviewUpdatedAt);

  function startEdit() {
    setDraft(review ?? "");
    setError(null);
    setMode("editing");
  }

  function cancelEdit() {
    setDraft(review ?? "");
    setError(null);
    setMode(review === null ? "editing" : "idle");
  }

  async function save() {
    if (!canSave) return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.setLibraryReview(titleId, trimmed);
      onChange({
        review: response.entry.review,
        reviewUpdatedAt: response.entry.review_updated_at,
      });
      setMode("idle");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти відгук");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (review === null) return;
    setSaving(true);
    setError(null);
    try {
      await api.setLibraryReview(titleId, null);
      onChange({ review: null, reviewUpdatedAt: null });
      setDraft("");
      setMode("editing");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося видалити відгук");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3 rounded-field border border-line bg-panel p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-text">Мій відгук</p>
          <p className="text-xs text-muted">
            Короткий текст для себе — інші поки не бачать. До {MAX_REVIEW_LENGTH} символів.
          </p>
        </div>
        {updatedLabel && mode === "idle" && (
          <span className="shrink-0 text-xs text-muted">Оновлено: {updatedLabel}</span>
        )}
      </div>

      {mode === "idle" && review !== null ? (
        <>
          <p className="whitespace-pre-wrap rounded-field border border-line bg-bg px-3 py-2.5 text-sm text-text">
            {review}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={startEdit}
              className="inline-flex h-9 items-center gap-1.5 rounded-field border border-line bg-bg px-3 text-sm font-medium text-text transition hover:border-accent hover:text-accent-dark"
            >
              <Pencil size={14} />
              Редагувати
            </button>
            <button
              type="button"
              onClick={() => void remove()}
              disabled={saving}
              className="inline-flex h-9 items-center gap-1.5 rounded-field border border-line bg-bg px-3 text-sm text-muted transition hover:border-error hover:text-error disabled:opacity-60"
            >
              <Trash2 size={14} />
              Видалити
            </button>
          </div>
        </>
      ) : (
        <>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value.slice(0, MAX_REVIEW_LENGTH))}
            maxLength={MAX_REVIEW_LENGTH}
            rows={5}
            placeholder="Що запам'яталося? Що сподобалось чи ні?"
            disabled={saving}
            className="w-full resize-y rounded-field border border-field bg-bg px-3 py-2 text-sm text-text placeholder:text-muted focus:border-accent focus:outline-none disabled:opacity-60"
          />
          <div className="flex items-center justify-between gap-3">
            <span
              className={[
                "text-xs",
                remaining < 100 ? "text-error" : "text-muted",
              ].join(" ")}
            >
              Залишилось {remaining} символів
            </span>
            <div className="flex items-center gap-2">
              {review !== null && (
                <button
                  type="button"
                  onClick={cancelEdit}
                  disabled={saving}
                  className="inline-flex h-9 items-center gap-1.5 rounded-field border border-line bg-bg px-3 text-sm text-muted transition hover:text-text disabled:opacity-60"
                >
                  <X size={14} />
                  Скасувати
                </button>
              )}
              <button
                type="button"
                onClick={() => void save()}
                disabled={!canSave || saving}
                className="inline-flex h-9 items-center rounded-field bg-accent px-3 text-sm font-medium text-white transition hover:bg-accent-dark disabled:opacity-60"
              >
                {saving ? "Зберігаємо…" : review === null ? "Зберегти" : "Оновити"}
              </button>
            </div>
          </div>
        </>
      )}

      {error && (
        <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
          {error}
        </p>
      )}
    </div>
  );
}
