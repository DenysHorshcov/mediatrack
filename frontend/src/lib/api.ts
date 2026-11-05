import type { LoginInput, ProfileUpdate, RegisterInput, User } from "@/types/auth";
import type { SearchFilter, SearchItem } from "@/types/search";

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
};
