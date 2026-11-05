import { Film, Gamepad2, Image as ImageIcon, Tv } from "lucide-react";
import { Link } from "react-router-dom";
import type { LibraryTitle } from "@/types/library";
import type { SearchItemType } from "@/types/search";

const TYPE_META: Record<
  SearchItemType,
  { label: string; icon: typeof Film }
> = {
  movie: { label: "Фільм", icon: Film },
  series: { label: "Серіал", icon: Tv },
  game: { label: "Гра", icon: Gamepad2 },
};

export function LibraryCard({ item }: { item: LibraryTitle }) {
  const { label, icon: Icon } = TYPE_META[item.media_type];
  return (
    <Link
      to={`/title/${item.provider}/${item.media_type}/${item.external_id}`}
      className="group flex flex-col rounded-field border border-line bg-bg transition hover:border-accent hover:shadow-sm"
    >
      <div className="aspect-[2/3] overflow-hidden rounded-t-field bg-poster">
        {item.poster_url ? (
          <img
            src={item.poster_url}
            alt={item.title}
            loading="lazy"
            className="h-full w-full object-cover transition group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-muted">
            <ImageIcon size={28} strokeWidth={1.5} />
          </div>
        )}
      </div>
      <div className="flex flex-col gap-1 px-3 py-2.5">
        <p className="line-clamp-2 text-sm font-medium text-text group-hover:text-accent-dark">
          {item.title}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted">
          <span>{item.year ?? "—"}</span>
          <span aria-hidden>·</span>
          <span className="inline-flex items-center gap-1">
            <Icon size={12} />
            {label}
          </span>
        </div>
      </div>
    </Link>
  );
}
