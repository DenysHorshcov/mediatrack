import { Film, Gamepad2, LayoutGrid, Tv } from "lucide-react";
import type { ReactNode } from "react";
import type { SearchFilter } from "@/types/search";

const FILTERS: Array<{ value: SearchFilter; label: string; icon: ReactNode }> = [
  { value: "all", label: "Усе", icon: <LayoutGrid size={16} /> },
  { value: "movie", label: "Фільми", icon: <Film size={16} /> },
  { value: "series", label: "Серіали", icon: <Tv size={16} /> },
  { value: "game", label: "Ігри", icon: <Gamepad2 size={16} /> },
];

type Props = {
  value: SearchFilter;
  onChange: (next: SearchFilter) => void;
};

export function SearchFilterTabs({ value, onChange }: Props) {
  return (
    <div
      role="tablist"
      aria-label="Тип результатів"
      className="inline-flex flex-wrap gap-1 rounded-field border border-line bg-panel p-1"
    >
      {FILTERS.map((filter) => {
        const isActive = filter.value === value;
        return (
          <button
            key={filter.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(filter.value)}
            className={[
              "inline-flex h-9 items-center gap-2 rounded-field px-3 text-sm font-medium transition",
              isActive
                ? "bg-accent-soft text-accent-dark"
                : "text-muted hover:bg-row hover:text-accent-dark",
            ].join(" ")}
          >
            {filter.icon}
            {filter.label}
          </button>
        );
      })}
    </div>
  );
}
