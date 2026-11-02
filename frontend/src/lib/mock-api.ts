import { ApiError } from "@/lib/api";
import type { LoginInput, RegisterInput, User } from "@/types/auth";

const STORAGE_KEY = "mediatrack:mock-session";

const mockUsers: Array<User & { password: string }> = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    email: "demo@mediatrack.ua",
    username: "demo",
    avatar_url: null,
    password: "demo1234",
  },
];

function saveSession(user: User) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

function clearSession() {
  sessionStorage.removeItem(STORAGE_KEY);
}

function readSession(): User | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  return raw ? (JSON.parse(raw) as User) : null;
}

function delay(ms = 250) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const mockApi = {
  async register(input: RegisterInput): Promise<{ user: User }> {
    await delay();
    const exists = mockUsers.some(
      (u) =>
        u.email.toLowerCase() === input.email.toLowerCase() ||
        u.username.toLowerCase() === input.username.toLowerCase(),
    );
    if (exists) {
      throw new ApiError(409, "Користувач з таким email або нікнеймом вже існує");
    }
    const user: User = {
      id: crypto.randomUUID(),
      email: input.email,
      username: input.username,
      avatar_url: null,
    };
    mockUsers.push({ ...user, password: input.password });
    saveSession(user);
    return { user };
  },

  async login(input: LoginInput): Promise<{ user: User }> {
    await delay();
    const found = mockUsers.find(
      (u) =>
        u.email.toLowerCase() === input.email.toLowerCase() &&
        u.password === input.password,
    );
    if (!found) {
      throw new ApiError(401, "Неправильний email або пароль");
    }
    const user: User = {
      id: found.id,
      email: found.email,
      username: found.username,
      avatar_url: found.avatar_url,
    };
    saveSession(user);
    return { user };
  },

  async logout(): Promise<void> {
    await delay(100);
    clearSession();
  },

  async me(): Promise<{ user: User }> {
    await delay(100);
    const user = readSession();
    if (!user) {
      throw new ApiError(401, "Не авторизовано");
    }
    return { user };
  },
};
