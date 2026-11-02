export type User = {
  id: string;
  email: string;
  username: string;
  avatar_url: string | null;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type RegisterInput = {
  email: string;
  username: string;
  password: string;
};

