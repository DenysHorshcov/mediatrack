export type Stats = {
  total: number;
  by_type: {
    movie: number;
    series: number;
    game: number;
  };
  by_status: {
    planned: number;
    in_progress: number;
    completed: number;
    on_hold: number;
    dropped: number;
  };
  average_rating: number | null;
  completed_this_year: number;
};
