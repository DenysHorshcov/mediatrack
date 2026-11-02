import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";

type Props = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  leftIcon?: ReactNode;
  rightSlot?: ReactNode;
};

export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, error, leftIcon, rightSlot, id, className, ...rest },
  ref,
) {
  const inputId = id ?? rest.name;
  const describedBy = error ? `${inputId}-error` : undefined;

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-text">
        {label}
      </label>
      <div className="relative">
        {leftIcon && (
          <span
            className={[
              "pointer-events-none absolute inset-y-0 left-3 flex items-center",
              error ? "text-error" : "text-muted",
            ].join(" ")}
          >
            {leftIcon}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={describedBy}
          className={[
            "h-[46px] w-full rounded-field border text-text outline-none transition",
            leftIcon ? "pl-10" : "pl-3",
            rightSlot ? "pr-10" : "pr-3",
            "placeholder:text-muted/60",
            error
              ? "border-error bg-error-bg focus:border-error"
              : "border-field bg-bg focus:border-accent",
            className ?? "",
          ].join(" ")}
          {...rest}
        />
        {rightSlot && (
          <span className="absolute inset-y-0 right-2 flex items-center">
            {rightSlot}
          </span>
        )}
      </div>
      {error && (
        <p id={describedBy} className="text-sm text-error">
          {error}
        </p>
      )}
    </div>
  );
});
