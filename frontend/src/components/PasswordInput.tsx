import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff, Lock } from "lucide-react";
import { Input } from "@/components/Input";

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  label: string;
  error?: string;
};

export function PasswordInput({ label, error, ...rest }: Props) {
  const [visible, setVisible] = useState(false);

  return (
    <Input
      {...rest}
      label={label}
      error={error}
      type={visible ? "text" : "password"}
      leftIcon={<Lock size={18} />}
      rightSlot={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Сховати пароль" : "Показати пароль"}
          aria-pressed={visible}
          tabIndex={-1}
          className="flex h-8 w-8 items-center justify-center rounded-field text-muted hover:bg-sidebar hover:text-text"
        >
          {visible ? <EyeOff size={18} /> : <Eye size={18} />}
        </button>
      }
    />
  );
}
