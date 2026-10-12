// Regression check for the bug that got v0.1.1 rejected.
//
// The bundle invokes the tool by the id it resolves at runtime; that id must
// be allowed by the manifest ACL. `anna-app apps publish` rewrites every
// `bundled:<handle>` ref to the server-minted tool_id before the manifest is
// stored, so this test replays that substitution and then runs the real
// production ACL gate (mountBundle).
//
// Run: cd repo && node acltest.mjs
import { mountBundle } from "file:///C:/Users/alireza%20fazeli/AppData/Roaming/npm/node_modules/@anna-ai/cli/dist/test/index.js";
import { substituteBundledRefs } from "file:///C:/Users/alireza%20fazeli/AppData/Roaming/npm/node_modules/@anna-ai/cli/dist/bundled-executas-DvdaUh2i.js";
import { readFileSync } from "node:fs";

const raw = JSON.parse(readFileSync("manifest.json", "utf-8"));
const sidecar = readFileSync("bundle/anna-tool-ids.js", "utf-8");
const resolved = JSON.parse(/window\.__ANNA_TOOL_IDS__\s*=\s*(\{[\s\S]*\});/.exec(sidecar)[1]);
const appJs = readFileSync("bundle/app.js", "utf-8");
const html = readFileSync("bundle/index.html", "utf-8");

const minted = resolved["invoice-sanity-check"];
const executa = JSON.parse(readFileSync("executas/invoice-sanity-check/executa.json", "utf-8"));
const dist = executa.distribution;
const activeProfile = dist?.profiles?.[dist?.active];
const checks = [
  ["executa declares a distribution block (not dev-only)", Boolean(dist)],
  ["active distribution profile is installable (not local)", Boolean(activeProfile) && activeProfile.type !== "local"],
  [
    "binary profile ships an https URL for every declared platform",
    activeProfile?.type === "binary" &&
      Object.values(activeProfile.binary_urls || {}).every((a) => /^https:\/\//.test(a.url || "")),
  ],
  ["binary executable_name matches the minted tool id", activeProfile?.executable_name === executa.tool_id],
  ["sidecar maps handle to a minted tool id", /^tool-/.test(minted || "")],
  ["app.js resolves id from window.__ANNA_TOOL_IDS__", appJs.includes("__ANNA_TOOL_IDS__")],
  ["index.html loads anna-tool-ids.js", html.includes("anna-tool-ids.js")],
  ["app.js does not hardcode a dev tool id as the primary id", !/const TOOL_ID\s*=\s*\"tool-dev-/.test(appJs)],
];

const manifest = substituteBundledRefs(raw, resolved);
console.log("publish-time required_executas:", JSON.stringify(manifest.required_executas));
console.log("publish-time host_api.tools:", JSON.stringify(manifest.ui.host_api.tools));

const h = await mountBundle({
  manifest,
  mocks: { "tools.invoke": (args) => ({ success: true, data: { echo: args } }) },
});
console.log("ACL tools:", [...h.acl.allowedTools], "wildcard:", h.acl.toolsWildcard);

let failed = false;
try {
  const r = await h.runtime.tools.invoke({ tool_id: minted, method: "check_invoice", args: { invoice_number: "INV-1" } });
  console.log("invoke result:", JSON.stringify(r));
} catch (e) {
  console.log("INVOKE ERROR:", e.code, e.message);
  failed = true;
}
await h.wait(10);

for (const [label, ok] of checks) {
  console.log((ok ? "PASS" : "FAIL") + " - " + label);
  if (!ok) failed = true;
}
console.log(failed ? "\nRESULT: FAILED" : "\nRESULT: PASSED");
process.exit(failed ? 1 : 0);
