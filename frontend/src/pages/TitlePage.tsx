import { useEffect, useState } from "react";
import {
  ArrowLeft,
  Calendar,
  Film,
  Gamepad2,
  Image as ImageIcon,
  Layers,
  Star,
  Tv,
} from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "@/lib/api";
import { seasonsLabel } from "@/lib/plural";
import type { SearchItemType } from "@/types/search";
import type { Title, TitleProvider } from "@/types/title";

const TYPE_META: Record<SearchItemType, { label: string; icon: typeof Film }> = {
  movie: { label: "Фільм", icon: Film },
  series: { label: "Серіал", icon: Tv },
  game: { label: "Гра", icon: Gamepad2 },
};

const VALID_PROVIDERS: TitleProvider[] = ["tmdb", "rawg"];
const VALID_TYPES: SearchItemType[] = ["movie", "series", "game"];

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; title: Title }
  | { kind: "not-found" }
  | { kind: "error"; message: string };

export default function TitlePage() {
  const params = useParams<{ provider: string; mediaType: string; externalId: string }>();
  const navigate = useNavigate();
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  const provider = params.provider as TitleProvider | undefined;
  const mediaType = params.mediaType as SearchItemType | undefined;
  const externalId = params.externalId;

  useEffect(() => {
    if (
      !provider ||
      !mediaType ||
      !externalId ||
      !VALID_PROVIDERS.includes(provider) ||
      !VALID_TYPES.includes(mediaType)
    ) {
      setState({ kind: "not-found" });
      return;
    }
    let cancelled = false;
    setState({ kind: "loading" });
    api
      .getTitle(provider, mediaType, externalId)
      .then((response) => {
        if (!cancelled) setState({ kind: "ready", title: response.title });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setState({ kind: "not-found" });
        } else {
          setState({
            kind: "error",
            message:
              err instanceof ApiError ? err.message : "Не вдалося завантажити тайтл",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [provider, mediaType, externalId]);

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-8 py-10">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-muted transition hover:text-accent-dark"
      >
        <ArrowLeft size={16} />
        Назад
      </button>

      {state.kind === "loading" && <TitleSkeleton />}
      {state.kind === "not-found" && <NotFound />}
      {state.kind === "error" && <ErrorView message={state.message} />}
      {state.kind === "ready" && <TitleView title={state.title} />}
    </div>
  );
}

function TitleView({ title }: { title: Title }) {
  const meta = TYPE_META[title.media_type];
  const TypeIcon = meta.icon;
  const dataSource = title.provider === "tmdb" ? "TMDB" : "RAWG";

  return (
    <article className="grid gap-8 md:grid-cols-[minmax(0,260px)_1fr]">
      <div className="aspect-[2/3] overflow-hidden rounded-field border border-line bg-poster">
        {title.poster_url ? (
          <img
            src={title.poster_url}
            alt={title.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted">
            <ImageIcon size={48} strokeWidth={1.4} />
          </div>
        )}
      </div>

      <div className="space-y-5">
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold text-text">{title.title}</h1>
          {title.original_title && title.original_title !== title.title && (
            <p className="text-sm text-muted">{title.original_title}</p>
          )}
        </div>

        <ul className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted">
          <li className="inline-flex items-center gap-1.5">
            <TypeIcon size={14} />
            {meta.label}
          </li>
          {title.year !== null && (
            <li className="inline-flex items-center gap-1.5">
              <Calendar size={14} />
              {title.year}
            </li>
          )}
          {title.media_type === "series" && title.seasons_count !== null && (
            <li className="inline-flex items-center gap-1.5">
              <Layers size={14} />
              {seasonsLabel(title.seasons_count)}
            </li>
          )}
        </ul>

        {title.genres.length > 0 && (
          <ul className="flex flex-wrap gap-2">
            {title.genres.map((genre) => (
              <li
                key={genre}
                className="rounded-full border border-line bg-panel px-3 py-1 text-xs text-muted"
              >
                {genre}
              </li>
            ))}
          </ul>
        )}

        {title.description && (
          <div className="space-y-1">
            <p className="whitespace-pre-line leading-relaxed text-text">
              {title.description}
            </p>
            {title.description_language === "en" && (
              <p className="text-xs text-muted">Опис англійською — українського поки немає.</p>
            )}
          </div>
        )}

        <ActionsPlaceholder />

        <p className="text-xs text-muted">Дані: {dataSource}</p>
      </div>
    </article>
  );
}

function ActionsPlaceholder() {
  return (
    <div className="space-y-3 rounded-field border border-dashed border-line bg-panel p-4">
      <div className="flex items-center gap-2 text-sm font-medium text-muted">
        <Star size={16} />
        Статус, оцінка й відгук
      </div>
      <p className="text-sm text-muted">
        Кнопки «У списках», «Оцінити» та «Написати відгук» зʼявляться у наступних спринтах.
      </p>
    </div>
  );
}

function TitleSkeleton() {
  return (
    <div className="grid gap-8 md:grid-cols-[minmax(0,260px)_1fr]">
      <div className="aspect-[2/3] animate-pulse rounded-field bg-poster" />
      <div className="space-y-4">
        <div className="h-8 w-2/3 animate-pulse rounded-field bg-poster" />
        <div className="h-4 w-1/3 animate-pulse rounded-field bg-poster" />
        <div className="space-y-2">
          <div className="h-3 w-full animate-pulse rounded-field bg-poster" />
          <div className="h-3 w-full animate-pulse rounded-field bg-poster" />
          <div className="h-3 w-5/6 animate-pulse rounded-field bg-poster" />
        </div>
      </div>
    </div>
  );
}

function NotFound() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-field border border-dashed border-line bg-panel px-6 py-12 text-center">
      <p className="text-lg font-semibold text-text">Тайтл не знайдено</p>
      <p className="max-w-md text-sm text-muted">
        Можливо, посилання некоректне або цього тайтлу вже немає у TMDB чи RAWG.
      </p>
      <Link to="/search" className="text-sm font-medium text-accent hover:text-accent-dark">
        Перейти до пошуку
      </Link>
    </div>
  );
}

function ErrorView({ message }: { message: string }) {
  return (
    <p role="alert" className="rounded-field bg-error-bg px-4 py-3 text-sm text-error">
      {message}
    </p>
  );
}
