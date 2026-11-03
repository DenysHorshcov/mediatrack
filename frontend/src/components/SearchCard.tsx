import { Film, Image as ImageIcon, Tv } from "lucide-react";
import { Link } from "react-router-dom";
import type { SearchItem } from "@/types/search";

function TypeBadge({ type }: { type: SearchItem["type"] }) {
  const label = type === "movie" ? "Фільм" : "Серіал";
  const Icon = type === "movie" ? Film : Tv;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted">
      <Icon size={12} />
      {label}
    </span>
  );
}

export function SearchCard({ item }: { item: SearchItem }) {
  return (
    <Link
      to={`/title/tmdb/${item.type}/${item.id}`}
      className="group flex flex-col rounded-field border border-line bg-bg transition hover:border-accent hover:shadow-sm"
    >
      <div className="aspect-[2/3] overflow-hidden rounded-t-field bg-poster">
        {item.poster ? (
          <img
            src={item.poster}
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
          <TypeBadge type={item.type} />
        </div>
      </div>
    </Link>
  );
}
