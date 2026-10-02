import type { FormEvent } from "react";
import { Icon } from "./Icon";

export function SearchField({
  id,
  value,
  onChange,
  onSubmit,
  placeholder,
  label,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder: string;
  label: string;
}) {
  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onSubmit?.();
  }

  return (
    <form onSubmit={handleSubmit} className="relative" role="search">
      <label htmlFor={id} className="sr-only">
        {label}
      </label>
      <Icon name="search" className="pointer-events-none absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-muted" />
      <input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        enterKeyHint="search"
        className="min-h-12 w-full rounded-2xl border border-line bg-canvas pr-4 pl-11 text-base text-ink placeholder:text-muted"
      />
    </form>
  );
}
