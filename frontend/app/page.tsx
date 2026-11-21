import { SystemStatus } from "@/components/system-status";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-8 space-y-6">
      <header>
        <h1 className="text-3xl font-bold">KnowBot</h1>
        <p className="text-muted-foreground">
          AI-ассистент по внутренней базе знаний компании
        </p>
      </header>

      <SystemStatus />

      <p className="text-sm text-muted-foreground">
        Чат появится на подэтапе 5.4
      </p>
    </main>
  );
}