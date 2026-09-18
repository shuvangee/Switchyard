import Link from "next/link";

export function Nav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="brand">
          Switchyard
        </Link>
        <Link href="/playground">Playground</Link>
        <Link href="/benchmarks">Benchmarks</Link>
        <Link href="/experiments">Experiments</Link>
        <Link href="/models">Models</Link>
        <Link href="/requests">Requests</Link>
      </div>
    </nav>
  );
}
