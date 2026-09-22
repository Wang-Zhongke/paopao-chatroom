import { retrieve } from "../lib/rag/retrieve";
async function main() {
  const query = process.argv.slice(2).join(" ").trim();
  if (!query) {
    console.error('Usage: pnpm rag:debug -- "query"');
    process.exitCode = 1;
  } else {
    const result = await retrieve(query.replace(/^--\s*/, ""), [], {
      log: false,
    });
    console.log(
      JSON.stringify(
        {
          query,
          ...result.trace,
          evidence: result.evidence.map((h) => ({
            id: h.unit.id,
            type: h.unit.type,
            title: h.unit.title,
            score: h.score,
            source: h.unit.source,
            preview: h.unit.content.slice(0, 900),
          })),
        },
        null,
        2,
      ),
    );
  }
}
main().catch((e) => {
  console.error(e.message);
  process.exitCode = 1;
});
