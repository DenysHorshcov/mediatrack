import { Trash2 } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { LIBRARY_STATUSES, statusIcon, statusLabel } from "@/lib/library";
import type { LibraryStatus } from "@/types/library";
import type { SearchItemType } from "@/types/search";

type Props = {
  titleId: string;
  mediaType: SearchItemType;
  current: LibraryStatus | null;
  onChange: (next: LibraryStatus | null) => void;
};

export function StatusSelector({ titleId, mediaType, current, onChange }: Props) {
  const [pending, setPending] = useState<LibraryStatus | "remove" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function selectStatus(status: LibraryStatus) {
    if (status === current) return;
    setPending(status);
    setError(null);
    try {
      await api.setLibraryStatus(titleId, status);
      onChange(status);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти");
    } finally {
      setPending(null);
    }
  }

  async function removeFromList() {
    setPending("remove");
    setError(null);
    try {
      await api.removeFromLibrary(titleId);
      onChange(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося прибрати");
    } finally {
      setPending(null);
    }
  }

  return (
    <div className="space-y-3 rounded-field border border-line bg-panel p-4">
      <div>
        <p className="text-sm font-medium text-text">Мій статус</p>
        <p className="text-xs text-muted">
          Додайте тайтл у свій список, щоб бачити його в «Мої списки».
        </p>
      </div>

      <ul className="flex flex-wrap gap-2" role="radiogroup" aria-label="Статус">
        {LIBRARY_STATUSES.map((status) => {
          const Icon = statusIcon(status);
          const isActive = status === current;
          const isPending = pending === status;
          return (
            <li key={status}>
              <button
                type="button"
                role="radio"
                aria-checked={isActive}
                disabled={pending !== null}
                onClick={() => void selectStatus(status)}
                className={[
                  "inline-flex h-9 items-center gap-2 rounded-field border px-3 text-sm font-medium transition disabled:opacity-60",
                  isActive
                    ? "border-accent bg-accent-soft text-accent-dark"
                    : "border-line bg-bg text-muted hover:border-accent hover:text-accent-dark",
                ].join(" ")}
              >
                <Icon size={14} />
                {statusLabel(status, mediaType)}
                {isPending && <span className="text-xs">…</span>}
              </button>
            </li>
          );
        })}
      </ul>

      {current !== null && (
        <button
          type="button"
          onClick={() => void removeFromList()}
          disabled={pending !== null}
          className="inline-flex items-center gap-1.5 text-sm text-error transition hover:text-error/80 disabled:opacity-60"
        >
          <Trash2 size={14} />
          {pending === "remove" ? "Прибираємо…" : "Прибрати зі списку"}
        </button>
      )}

      {error && (
        <p role="alert" className="rounded-field bg-error-bg px-3 py-2 text-sm text-error">
          {error}
        </p>
      )}
    </div>
  );
}
