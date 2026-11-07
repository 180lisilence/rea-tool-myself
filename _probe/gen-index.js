// 从 rea --help 提取命令索引，输出 JSON 到 stdout
const { execFile } = require('child_process');
const NODE = 'C:\\Users\\19513\\.workbuddy\\binaries\\node\\versions\\22.22.2-3\\node.exe';
const MJS = 'C:\\Users\\19513\\AppData\\Roaming\\npm\\node_modules\\rea-agents\\scripts\\rea.mjs';

execFile(NODE, [MJS, '--help'], { maxBuffer: 20 * 1024 * 1024 }, (err, stdout, stderr) => {
  const text = (stdout || '') + (stderr || '');
  const lines = text.split(/\r?\n/);
  const cmds = [];
  let inC = false;
  for (const line of lines) {
    if (/^\s*Commands:\s*$/.test(line)) { inC = true; continue; }
    if (inC && /^\s*$/.test(line)) { inC = false; continue; }
    if (!inC) continue;
    const m = line.match(/^ {2}([a-z0-9][a-z0-9-]*)\s{2,}(.*)$/);
    if (m) cmds.push({ name: m[1], summary: m[2].trim() });
  }
  process.stdout.write(JSON.stringify(cmds, null, 1));
});
