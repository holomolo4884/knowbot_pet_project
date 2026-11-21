import { createParser, feed } from "../lib/sse-parser.ts";

function assert(cond, msg) {
  if (!cond) throw new Error("ASSERT: " + msg);
}

// Test 1: single complete event
{
  const p = createParser();
  const evs = feed(p, 'event: delta\ndata: {"text":"hi"}\n\n');
  assert(evs.length === 1, "one event");
  assert(evs[0].type === "delta", "type");
  assert(evs[0].text === "hi", "text");
}

// Test 2: multiple events in one chunk
{
  const p = createParser();
  const evs = feed(
    p,
    'event: delta\ndata: {"text":"a"}\n\nevent: delta\ndata: {"text":"b"}\n\n',
  );
  assert(evs.length === 2, "two events");
  assert(evs[0].text === "a" && evs[1].text === "b", "correct order");
}

// Test 3: split across chunks
{
  const p = createParser();
  const e1 = feed(p, 'event: delta\ndata: {"te');
  assert(e1.length === 0, "incomplete → empty");
  const e2 = feed(p, 'xt":"ok"}\n\n');
  assert(e2.length === 1 && e2[0].text === "ok", "recovered");
}

// Test 4: trailing without final \n\n
{
  const p = createParser();
  const e1 = feed(p, 'event: done\ndata: {}');
  assert(e1.length === 0, "no double newline");
  const e2 = feed(p, "\n\n");
  assert(e2.length === 1 && e2[0].type === "done", "flushed on trailing newlines");
}

// Test 5: bad JSON gracefully skipped
{
  const p = createParser();
  const evs = feed(p, 'event: delta\ndata: {broken}\n\n');
  assert(evs.length === 0, "bad JSON → null");
}

console.log("All SSE parser tests passed ✓");