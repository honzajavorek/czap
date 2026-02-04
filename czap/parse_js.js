#!/usr/bin/env node
/**
 * Safely parse JavaScript object literal to JSON
 * 
 * This script reads a JavaScript object literal from stdin and outputs
 * valid JSON to stdout. It uses Node.js's vm module with a timeout to
 * safely evaluate the JavaScript code without full eval() risks.
 */

const vm = require('vm');
const readline = require('readline');

// Read all input from stdin
let input = '';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', (line) => {
  input += line + '\n';
});

rl.on('close', () => {
  try {
    // Create a sandboxed context with no access to Node.js APIs
    const sandbox = {};
    const context = vm.createContext(sandbox);
    
    // Wrap the input in parentheses to make it an expression
    // This allows us to evaluate object literals like {members: [...]}
    const code = `(${input})`;
    
    // Execute the code in the sandboxed context with a timeout
    const result = vm.runInContext(code, context, {
      timeout: 10000, // 10 second timeout
      displayErrors: true
    });
    
    // Convert the result to JSON and output it
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error('Error parsing JavaScript:', error.message);
    process.exit(1);
  }
});
