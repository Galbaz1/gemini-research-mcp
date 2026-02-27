'use strict';

const RESET = '\x1b[0m';
const GREEN = '\x1b[32m';
const YELLOW = '\x1b[33m';
const RED = '\x1b[31m';
const CYAN = '\x1b[36m';
const BOLD = '\x1b[1m';
const DIM = '\x1b[2m';

/** Print a success message (green checkmark) to stderr. */
function success(msg) {
  process.stderr.write(`${GREEN}\u2713${RESET} ${msg}\n`);
}

/** Print a warning message (yellow triangle) to stderr. */
function warn(msg) {
  process.stderr.write(`${YELLOW}\u26A0${RESET} ${msg}\n`);
}

/** Print an error message (red X) to stderr. */
function error(msg) {
  process.stderr.write(`${RED}\u2717${RESET} ${msg}\n`);
}

/** Print a dim info line to stderr. */
function info(msg) {
  process.stderr.write(`${DIM}  ${msg}${RESET}\n`);
}

/** Print a section header with horizontal rules to stderr. */
function header(title) {
  const line = '\u2500'.repeat(50);
  process.stderr.write(`\n${BOLD}${CYAN}${line}${RESET}\n`);
  process.stderr.write(`${BOLD}${CYAN}  ${title}${RESET}\n`);
  process.stderr.write(`${BOLD}${CYAN}${line}${RESET}\n\n`);
}

/** Print an indented step to stderr. */
function step(msg) {
  process.stderr.write(`  ${msg}\n`);
}

/** Print a blank line to stderr. */
function blank() {
  process.stderr.write('\n');
}

module.exports = { success, warn, error, info, header, step, blank };
