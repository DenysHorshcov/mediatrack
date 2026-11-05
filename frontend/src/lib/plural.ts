type Forms = { one: string; few: string; many: string };

export function pluralUa(n: number, forms: Forms): string {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (mod10 === 1 && mod100 !== 11) return forms.one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms.few;
  return forms.many;
}

export function seasonsLabel(n: number): string {
  return `${n} ${pluralUa(n, { one: "сезон", few: "сезони", many: "сезонів" })}`;
}
