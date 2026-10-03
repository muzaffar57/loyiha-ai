import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

const control = "mt-1 w-full min-w-0 rounded-2xl border border-line bg-white px-3 py-3 text-ink";

export function FieldLabel({ children }: { children: ReactNode }) {
  return <span className="text-sm font-medium text-ink">{children}</span>;
}

export function TextField({ label, ...props }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block min-w-0">
      <FieldLabel>{label}</FieldLabel>
      <input {...props} className={control} />
    </label>
  );
}

export function AreaField({ label, ...props }: { label: string } & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block min-w-0">
      <FieldLabel>{label}</FieldLabel>
      <textarea {...props} className={`${control} min-h-28`} />
    </label>
  );
}

export function SelectField({ label, children, ...props }: { label: string } & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <label className="block min-w-0">
      <FieldLabel>{label}</FieldLabel>
      <select {...props} className={control}>
        {children}
      </select>
    </label>
  );
}

export function CheckField({ label, ...props }: { label: string } & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex min-h-12 items-center gap-3 text-sm text-ink">
      <input {...props} type="checkbox" className="size-5 accent-brand" />
      {label}
    </label>
  );
}

export function AdminButton({
  children,
  tone = "primary",
  type = "button",
  disabled,
  onClick,
}: {
  children: ReactNode;
  tone?: "primary" | "secondary" | "danger";
  type?: "button" | "submit";
  disabled?: boolean;
  onClick?: () => void;
}) {
  const tones = {
    primary: "bg-brand text-white hover:bg-brand-dark",
    secondary: "border border-line bg-white text-ink hover:bg-mist",
    danger: "bg-white text-danger border border-line hover:bg-mist",
  };
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex min-h-12 items-center justify-center rounded-full px-5 text-sm font-semibold disabled:opacity-50 ${tones[tone]}`}
    >
      {children}
    </button>
  );
}

export function Notice({ tone, children }: { tone: "ok" | "error"; children: ReactNode }) {
  const className = tone === "ok" ? "bg-brand-soft text-brand-dark" : "bg-white text-danger border border-line";
  return <p className={`rounded-2xl px-4 py-3 text-sm ${className}`}>{children}</p>;
}
