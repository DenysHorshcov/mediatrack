import { describe, expect, it } from "vitest";
import {
  validateAvatarUrl,
  validateEmail,
  validateLoginForm,
  validatePassword,
  validatePasswordConfirm,
  validateProfileForm,
  validateProfileNickname,
  validateRegisterForm,
  validateUsername,
} from "./validation";

describe("validateEmail", () => {
  it("rejects empty", () => {
    expect(validateEmail("")).toBe("Введіть email");
    expect(validateEmail("   ")).toBe("Введіть email");
  });

  it("rejects malformed", () => {
    expect(validateEmail("foo")).toBe("Некоректний email");
    expect(validateEmail("foo@")).toBe("Некоректний email");
    expect(validateEmail("foo@bar")).toBe("Некоректний email");
    expect(validateEmail("foo @bar.com")).toBe("Некоректний email");
  });

  it("accepts valid email", () => {
    expect(validateEmail("user@example.com")).toBeUndefined();
    expect(validateEmail("  user@example.com  ")).toBeUndefined();
  });
});

describe("validateUsername", () => {
  it("rejects empty or whitespace-only", () => {
    expect(validateUsername("")).toBe("Введіть нікнейм");
    expect(validateUsername("   ")).toBe("Введіть нікнейм");
  });

  it("rejects too short", () => {
    expect(validateUsername("ab")).toMatch(/коротшим/);
  });

  it("rejects too long", () => {
    expect(validateUsername("a".repeat(51))).toMatch(/довшим/);
  });

  it("accepts valid", () => {
    expect(validateUsername("demo")).toBeUndefined();
    expect(validateUsername("a".repeat(50))).toBeUndefined();
  });
});

describe("validatePassword", () => {
  it("rejects empty", () => {
    expect(validatePassword("")).toBe("Введіть пароль");
  });

  it("rejects too short", () => {
    expect(validatePassword("abc123")).toMatch(/коротшим/);
  });

  it("accepts 8+ chars", () => {
    expect(validatePassword("abcdefgh")).toBeUndefined();
  });
});

describe("validatePasswordConfirm", () => {
  it("rejects mismatch", () => {
    expect(validatePasswordConfirm("abc", "abcd")).toBe("Паролі не збігаються");
  });

  it("accepts match", () => {
    expect(validatePasswordConfirm("abc", "abc")).toBeUndefined();
  });
});

describe("validateLoginForm", () => {
  it("returns all errors for empty input", () => {
    const result = validateLoginForm({ email: "", password: "" });
    expect(result).toEqual({
      email: "Введіть email",
      password: "Введіть пароль",
    });
  });

  it("does not enforce password length on login", () => {
    const result = validateLoginForm({
      email: "user@example.com",
      password: "x",
    });
    expect(result).toEqual({});
  });

  it("returns empty when all valid", () => {
    expect(
      validateLoginForm({ email: "user@example.com", password: "any" }),
    ).toEqual({});
  });
});

describe("validateRegisterForm", () => {
  it("returns all errors for empty input", () => {
    const result = validateRegisterForm({
      email: "",
      username: "",
      password: "",
      passwordConfirm: "",
    });
    expect(result.email).toBeDefined();
    expect(result.username).toBeDefined();
    expect(result.password).toBeDefined();
    expect(result.passwordConfirm).toBeUndefined();
  });

  it("flags mismatched password confirmation", () => {
    const result = validateRegisterForm({
      email: "user@example.com",
      username: "demo",
      password: "abcdefgh",
      passwordConfirm: "abcdefg",
    });
    expect(result.passwordConfirm).toBe("Паролі не збігаються");
  });

  it("returns empty when all valid", () => {
    expect(
      validateRegisterForm({
        email: "user@example.com",
        username: "demo",
        password: "abcdefgh",
        passwordConfirm: "abcdefgh",
      }),
    ).toEqual({});
  });
});

describe("validateProfileNickname", () => {
  it("rejects empty", () => {
    expect(validateProfileNickname("")).toBe("Введіть нікнейм");
    expect(validateProfileNickname("   ")).toBe("Введіть нікнейм");
  });

  it("rejects too short", () => {
    expect(validateProfileNickname("ab")).toMatch(/коротшим/);
  });

  it("rejects too long (over 30)", () => {
    expect(validateProfileNickname("a".repeat(31))).toMatch(/довшим/);
  });

  it("accepts 3..30", () => {
    expect(validateProfileNickname("abc")).toBeUndefined();
    expect(validateProfileNickname("a".repeat(30))).toBeUndefined();
  });
});

describe("validateAvatarUrl", () => {
  it("accepts empty (clears avatar)", () => {
    expect(validateAvatarUrl("")).toBeUndefined();
    expect(validateAvatarUrl("   ")).toBeUndefined();
  });

  it("rejects malformed", () => {
    expect(validateAvatarUrl("not a url")).toBe("Некоректне посилання");
  });

  it("rejects non-http protocols", () => {
    expect(validateAvatarUrl("ftp://example.com/a.png")).toMatch(/http/);
  });

  it("accepts http and https", () => {
    expect(validateAvatarUrl("https://example.com/a.png")).toBeUndefined();
    expect(validateAvatarUrl("http://example.com/a.png")).toBeUndefined();
  });
});

describe("validateProfileForm", () => {
  it("returns errors for invalid input", () => {
    const result = validateProfileForm({ username: "", avatar_url: "oops" });
    expect(result.username).toBeDefined();
    expect(result.avatar_url).toBeDefined();
  });

  it("returns empty for valid input with avatar", () => {
    expect(
      validateProfileForm({ username: "demo", avatar_url: "https://example.com/a.png" }),
    ).toEqual({});
  });

  it("returns empty for valid input with empty avatar", () => {
    expect(validateProfileForm({ username: "demo", avatar_url: "" })).toEqual({});
  });
});
