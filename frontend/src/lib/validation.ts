export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const USERNAME_MIN = 3;
export const USERNAME_MAX = 50;
export const PROFILE_USERNAME_MAX = 30;
export const PASSWORD_MIN = 8;
export const AVATAR_URL_MAX = 2048;

export function validateEmail(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return "Введіть email";
  if (!EMAIL_RE.test(trimmed)) return "Некоректний email";
  return undefined;
}

export function validateUsername(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return "Введіть нікнейм";
  if (trimmed.length < USERNAME_MIN)
    return `Нікнейм має бути не коротшим за ${USERNAME_MIN} символи`;
  if (value.length > USERNAME_MAX)
    return `Нікнейм не може бути довшим за ${USERNAME_MAX} символів`;
  return undefined;
}

export function validatePassword(value: string): string | undefined {
  if (!value) return "Введіть пароль";
  if (value.length < PASSWORD_MIN)
    return `Пароль має бути не коротшим за ${PASSWORD_MIN} символів`;
  return undefined;
}

export function validatePasswordConfirm(
  password: string,
  confirm: string,
): string | undefined {
  if (password !== confirm) return "Паролі не збігаються";
  return undefined;
}

export type LoginFields = {
  email?: string;
  password?: string;
  form?: string;
};

export function validateLoginForm(input: {
  email: string;
  password: string;
}): LoginFields {
  const errors: LoginFields = {};
  const email = validateEmail(input.email);
  if (email) errors.email = email;
  // for login we only require that password is non-empty — length rule is for
  // registration (don't lock out users who registered under an older policy)
  if (!input.password) errors.password = "Введіть пароль";
  return errors;
}

export type RegisterFields = {
  email?: string;
  username?: string;
  password?: string;
  passwordConfirm?: string;
  form?: string;
};

export function validateRegisterForm(input: {
  email: string;
  username: string;
  password: string;
  passwordConfirm: string;
}): RegisterFields {
  const errors: RegisterFields = {};
  const email = validateEmail(input.email);
  if (email) errors.email = email;
  const username = validateUsername(input.username);
  if (username) errors.username = username;
  const password = validatePassword(input.password);
  if (password) errors.password = password;
  const confirm = validatePasswordConfirm(input.password, input.passwordConfirm);
  if (confirm) errors.passwordConfirm = confirm;
  return errors;
}

export function validateProfileNickname(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return "Введіть нікнейм";
  if (trimmed.length < USERNAME_MIN)
    return `Нікнейм має бути не коротшим за ${USERNAME_MIN} символи`;
  if (trimmed.length > PROFILE_USERNAME_MAX)
    return `Нікнейм не може бути довшим за ${PROFILE_USERNAME_MAX} символів`;
  return undefined;
}

export function validateAvatarUrl(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  if (trimmed.length > AVATAR_URL_MAX)
    return `Посилання не може бути довшим за ${AVATAR_URL_MAX} символів`;
  try {
    const url = new URL(trimmed);
    if (url.protocol !== "http:" && url.protocol !== "https:")
      return "Посилання має починатися з http або https";
  } catch {
    return "Некоректне посилання";
  }
  return undefined;
}

export type ProfileFields = {
  username?: string;
  avatar_url?: string;
  form?: string;
};

export function validateProfileForm(input: {
  username: string;
  avatar_url: string;
}): ProfileFields {
  const errors: ProfileFields = {};
  const username = validateProfileNickname(input.username);
  if (username) errors.username = username;
  const avatar = validateAvatarUrl(input.avatar_url);
  if (avatar) errors.avatar_url = avatar;
  return errors;
}
