'use strict';

const fs = require('fs');
const path = require('path');
const ui = require('./ui');

/** MCP server entries to install. */
const MCP_SERVERS = {
  'video-research': {
    command: 'uvx',
    args: ['video-research-mcp'],
    env: { GEMINI_API_KEY: '${GEMINI_API_KEY}' },
  },
  playwright: {
    command: 'npx',
    args: ['@playwright/mcp@latest', '--headless', '--caps=vision,pdf'],
  },
};

/**
 * Return the path to the MCP config file.
 * Global: ~/.claude/.mcp.json
 * Local:  ./.mcp.json (project root, not inside .claude/)
 */
function getConfigPath(mode) {
  if (mode === 'global') {
    const home = process.env.HOME || process.env.USERPROFILE;
    if (!home) {
      throw new Error(
        'Cannot determine home directory: HOME and USERPROFILE are both unset',
      );
    }
    return path.join(home, '.claude', '.mcp.json');
  }
  return path.join(process.cwd(), '.mcp.json');
}

/** Read and parse a JSON config file. Returns null if not found. Throws on malformed JSON. */
function readConfig(configPath) {
  try {
    const raw = fs.readFileSync(configPath, 'utf8');
    return JSON.parse(raw);
  } catch (err) {
    if (err.code === 'ENOENT') return null;
    if (err instanceof SyntaxError) {
      ui.error(`Malformed JSON in ${configPath}`);
      ui.info('Fix the file manually or delete it to start fresh');
      throw err;
    }
    throw err;
  }
}

/** Merge MCP_SERVERS into the config file. Creates the file if it doesn't exist. */
function mergeConfig(configPath) {
  const existing = readConfig(configPath) || {};
  existing.mcpServers = existing.mcpServers || {};

  for (const [name, config] of Object.entries(MCP_SERVERS)) {
    existing.mcpServers[name] = config;
  }

  fs.mkdirSync(path.dirname(configPath), { recursive: true });
  fs.writeFileSync(configPath, JSON.stringify(existing, null, 2) + '\n');
  return existing;
}

/** Remove MCP_SERVERS entries from the config file. Returns true if any were removed. */
function removeFromConfig(configPath) {
  const existing = readConfig(configPath);
  if (!existing?.mcpServers) return false;

  let removed = false;
  for (const name of Object.keys(MCP_SERVERS)) {
    if (existing.mcpServers[name]) {
      delete existing.mcpServers[name];
      removed = true;
    }
  }

  if (removed) {
    fs.writeFileSync(configPath, JSON.stringify(existing, null, 2) + '\n');
  }
  return removed;
}

module.exports = { MCP_SERVERS, getConfigPath, readConfig, mergeConfig, removeFromConfig };
