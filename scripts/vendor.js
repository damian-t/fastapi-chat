const fs = require("fs");
const path = require("path");

const rootDir = path.resolve(__dirname, "..");
const vendorDir = path.join(rootDir, "app", "static", "vendor");

if (!fs.existsSync(vendorDir)) {
  fs.mkdirSync(vendorDir, { recursive: true });
}

const copyFiles = [
  {
    from: path.join(rootDir, "node_modules", "marked", "lib", "marked.umd.js"),
    to: path.join(vendorDir, "marked.min.js"),
  },
  {
    from: path.join(rootDir, "node_modules", "dompurify", "dist", "purify.min.js"),
    to: path.join(vendorDir, "purify.min.js"),
  },
  {
    from: path.join(rootDir, "node_modules", "mermaid", "dist", "mermaid.min.js"),
    to: path.join(vendorDir, "mermaid.min.js"),
  },
];

for (const { from, to } of copyFiles) {
  if (fs.existsSync(from)) {
    fs.copyFileSync(from, to);
    console.log(`Copied ${path.relative(rootDir, from)} -> ${path.relative(rootDir, to)}`);
  } else {
    console.error(`Source file not found: ${from}`);
    process.exit(1);
  }
}
console.log("Vendor assets updated successfully.");
