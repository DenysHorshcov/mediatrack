import type { SearchItemType } from "@/types/search";

export type TitleProvider = "tmdb" | "rawg";

export type Title = {
  id: string;
  provider: TitleProvider;
  media_type: SearchItemType;
  external_id: string;
  title: string;
  original_title: string | null;
  description: string | null;
  description_language: "uk" | "en" | null;
  poster_url: string | null;
  year: number | null;
  genres: string[];
  seasons_count: number | null;
};
