import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type Variant = "primary" | "secondary" | "ghost" | "onDark";

const styles: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-dark",
  secondary: "bg-mist text-ink border border-line hover:bg-brand-soft",
  ghost: "bg-transparent text-brand hover:bg-brand-soft",
  onDark: "bg-white text-brand hover:bg-mist",
};

type Props = {
  children: ReactNode;
  to?: string;
  onClick?: () => void;
  variant?: Variant;
  type?: "button" | "submit";
  className?: string;
};

export function Button({ children, to, onClick, variant = "primary", type = "button", className = "" }: Props) {
  const classNames = `inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold transition-colors ${styles[variant]} ${className}`;
  if (to) {
    return (
      <Link to={to} className={classNames}>
        {children}
      </Link>
    );
  }
  return (
    <button type={type} onClick={onClick} className={classNames}>
      {children}
    </button>
  );
}
