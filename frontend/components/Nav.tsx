import Link from "next/link";

export function Nav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand">
          Switchyard
        </Link>
        <Link href="/benchmarks">Benchmarks</Link>
        <Link href="/experiments">Experiments</Link>
      </div>
    </nav>
  );
}
