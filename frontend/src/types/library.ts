import type { SearchItemType } from "@/types/search";
import type { TitleProvider } from "@/types/title";

export type LibraryStatus =
  | "planned"
  | "in_progress"
  | "completed"
  | "on_hold"
  | "dropped";

export type LibraryTitle = {
  id: string;
  provider: TitleProvider;
  media_type: SearchItemType;
  external_id: string;
  title: string;
  poster_url: string | null;
  year: number | null;
  status: LibraryStatus;
  rating: number | null;
  current_season: number | null;
  current_episode: number | null;
  review: string | null;
  review_updated_at: string | null;
};
