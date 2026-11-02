import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  variant?: "primary" | "ghost";
};

export function Button({
  children,
  variant = "primary",
  className,
  ...rest
}: Props) {
  const base =
    "h-[46px] rounded-field px-5 font-medium transition disabled:cursor-not-allowed disabled:opacity-60";
  const variants = {
    primary: "bg-accent text-white hover:bg-accent-dark",
    ghost: "border border-field bg-bg text-text hover:bg-sidebar",
  };

  return (
    <button
      className={[base, variants[variant], className ?? ""].join(" ")}
      {...rest}
    >
      {children}
    </button>
  );
}
