import type { LoginInput, ProfileUpdate, RegisterInput, User } from "@/types/auth";
import type { LibraryStatus, LibraryTitle } from "@/types/library";
import type { SearchFilter, SearchItem, SearchItemType } from "@/types/search";
import type { Season } from "@/types/season";
import type { Stats } from "@/types/stats";
import type { Title, TitleProvider } from "@/types/title";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  status: number;
  fieldErrors?: Record<string, string>;

  constructor(status: number, message: string, fieldErrors?: Record<string, string>) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      response.status,
      typeof data?.detail === "string" ? data.detail : "Сталася помилка",
      data?.fields,
    );
  }

  return data as T;
}

export const api = {
  register: (input: RegisterInput) =>
    request<{ user: User }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  login: (input: LoginInput) =>
    request<{ user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<{ user: User }>("/auth/me"),
  getProfile: () => request<{ user: User }>("/users/me"),
  updateProfile: (input: ProfileUpdate) =>
    request<{ user: User }>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  search: (query: string, filter: SearchFilter = "all") => {
    const params = new URLSearchParams({ q: query });
    if (filter !== "all") params.set("type", filter);
    return request<{ results: SearchItem[] }>(`/search?${params.toString()}`);
  },
  getTitle: (provider: TitleProvider, mediaType: string, externalId: string) =>
    request<{ title: Title }>(
      `/titles/${encodeURIComponent(provider)}/${encodeURIComponent(mediaType)}/${encodeURIComponent(externalId)}`,
    ),
  getLibraryEntry: (titleId: string) =>
    request<{ entry: LibraryTitle }>(`/me/titles/${encodeURIComponent(titleId)}`),
  setLibraryStatus: (titleId: string, status: LibraryStatus) =>
    request<{ entry: LibraryTitle }>(`/me/titles/${encodeURIComponent(titleId)}`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    }),
  setLibraryRating: (titleId: string, rating: number | null) =>
    request<{ entry: LibraryTitle }>(`/me/titles/${encodeURIComponent(titleId)}`, {
      method: "PATCH",
      body: JSON.stringify({ rating }),
    }),
  setLibraryProgress: (
    titleId: string,
    progress: { season: number | null; episode: number | null },
  ) =>
    request<{ entry: LibraryTitle }>(`/me/titles/${encodeURIComponent(titleId)}`, {
      method: "PATCH",
      body: JSON.stringify(progress),
    }),
  getSeasons: (provider: TitleProvider, mediaType: string, externalId: string) =>
    request<{ seasons: Season[] }>(
      `/titles/${encodeURIComponent(provider)}/${encodeURIComponent(mediaType)}/${encodeURIComponent(externalId)}/seasons`,
    ),
  removeFromLibrary: (titleId: string) =>
    request<void>(`/me/titles/${encodeURIComponent(titleId)}`, { method: "DELETE" }),
  getStats: () => request<Stats>("/me/stats"),
  listLibrary: (filters: { status?: LibraryStatus; type?: SearchItemType } = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.type) params.set("type", filters.type);
    const qs = params.toString();
    return request<{ items: LibraryTitle[] }>(`/me/titles${qs ? `?${qs}` : ""}`);
  },
};
