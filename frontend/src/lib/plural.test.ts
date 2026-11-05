import { describe, expect, it } from "vitest";
import { pluralUa, seasonsLabel } from "./plural";

const forms = { one: "сезон", few: "сезони", many: "сезонів" };

describe("pluralUa", () => {
  it("picks one for 1", () => {
    expect(pluralUa(1, forms)).toBe("сезон");
    expect(pluralUa(21, forms)).toBe("сезон");
    expect(pluralUa(101, forms)).toBe("сезон");
  });

  it("picks few for 2-4", () => {
    expect(pluralUa(2, forms)).toBe("сезони");
    expect(pluralUa(3, forms)).toBe("сезони");
    expect(pluralUa(4, forms)).toBe("сезони");
    expect(pluralUa(22, forms)).toBe("сезони");
  });

  it("picks many for 0, 5-20", () => {
    expect(pluralUa(0, forms)).toBe("сезонів");
    expect(pluralUa(5, forms)).toBe("сезонів");
    expect(pluralUa(11, forms)).toBe("сезонів");
    expect(pluralUa(14, forms)).toBe("сезонів");
    expect(pluralUa(25, forms)).toBe("сезонів");
  });
});

describe("seasonsLabel", () => {
  it("formats correctly", () => {
    expect(seasonsLabel(1)).toBe("1 сезон");
    expect(seasonsLabel(3)).toBe("3 сезони");
    expect(seasonsLabel(7)).toBe("7 сезонів");
  });
});
