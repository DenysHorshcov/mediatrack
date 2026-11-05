export type SearchItemType = "movie" | "series" | "game";

export type SearchFilter = "all" | SearchItemType;

export type SearchItem = {
  id: string;
  type: SearchItemType;
  title: string;
  year: number | null;
  poster: string | null;
};
