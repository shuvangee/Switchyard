import Link from "next/link";

export function Nav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand">
          Switchyard
        </Link>
        <Link href="/">Overview</Link>
        <Link href="/playground">Playground</Link>
        <Link href="/requests">Requests</Link>
        <Link href="/models">Models</Link>
        <Link href="/benchmarks">Benchmarks</Link>
        <Link href="/experiments">Experiments</Link>
        <Link href="/compare">Compare</Link>
        <Link href="/analytics">Analytics</Link>
      </div>
    </nav>
  );
}
