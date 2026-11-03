export type SearchItem = {
  id: string;
  type: "movie" | "series";
  title: string;
  year: number | null;
  poster: string | null;
};
