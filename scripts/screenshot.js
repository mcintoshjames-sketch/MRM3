#!/usr/bin/env node
/**
 * Screenshot utility for QMIS application
 * Saves screenshots to NAS for documentation and testing
 *
 * Usage:
 *   node scripts/screenshot.js <url> [output-filename] [width] [height]
 *   node scripts/screenshot.js <url> --full-page [output-filename]
 *
 * Examples:
 *   node scripts/screenshot.js http://localhost:5174 login.png
 *   node scripts/screenshot.js http://localhost:5174/models models-list.png 1920 1080
 *   node scripts/screenshot.js http://localhost:5174/dashboard --full-page dashboard-full.png
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

// Default output directory - NAS mount point
const DEFAULT_OUTPUT_DIR = '/Volumes/Content/MCPScreenShots';

// Fallback if NAS not mounted
const FALLBACK_OUTPUT_DIR = path.join(__dirname, '..', 'screenshots');

function getOutputDir() {
    if (fs.existsSync(DEFAULT_OUTPUT_DIR)) {
        return DEFAULT_OUTPUT_DIR;
    }
    // Create fallback directory if needed
    if (!fs.existsSync(FALLBACK_OUTPUT_DIR)) {
        fs.mkdirSync(FALLBACK_OUTPUT_DIR, { recursive: true });
    }
    console.warn(`Warning: NAS not mounted at ${DEFAULT_OUTPUT_DIR}, using ${FALLBACK_OUTPUT_DIR}`);
    return FALLBACK_OUTPUT_DIR;
}

function generateFilename(url) {
    // Extract page name from URL path
    const urlObj = new URL(url);
    let pageName = urlObj.pathname.replace(/\//g, '-').replace(/^-/, '') || 'home';
    if (pageName === '') pageName = 'home';

    // Add timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    return `qmis-${pageName}-${timestamp}.png`;
}

async function takeScreenshot(url, outputPath, options = {}) {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();

    await page.setViewport({
        width: options.width || 1400,
        height: options.height || 900
    });

    console.log(`Navigating to: ${url}`);
    await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });

    // Optional: wait for a specific selector
    if (options.waitFor) {
        console.log(`Waiting for selector: ${options.waitFor}`);
        await page.waitForSelector(options.waitFor, { timeout: 10000 });
    }

    // Small delay to ensure rendering is complete
    await new Promise(resolve => setTimeout(resolve, 500));

    await page.screenshot({
        path: outputPath,
        fullPage: options.fullPage || false
    });

    console.log(`Screenshot saved to: ${outputPath}`);
    await browser.close();

    return outputPath;
}

// CLI usage
const args = process.argv.slice(2);

if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    console.log(`
QMIS Screenshot Utility
=======================

Usage:
  node scripts/screenshot.js <url> [output-filename] [width] [height]
  node scripts/screenshot.js <url> --full-page [output-filename]

Arguments:
  url              The URL to capture (required)
  output-filename  Output filename (optional, auto-generated if not provided)
  width            Viewport width in pixels (default: 1400)
  height           Viewport height in pixels (default: 900)

Options:
  --full-page      Capture the full scrollable page
  --help, -h       Show this help message

Output Location:
  Primary:  ${DEFAULT_OUTPUT_DIR}
  Fallback: ${FALLBACK_OUTPUT_DIR}

Examples:
  # Basic screenshot with auto-generated filename
  node scripts/screenshot.js http://localhost:5174

  # Named screenshot
  node scripts/screenshot.js http://localhost:5174 login.png

  # Custom dimensions
  node scripts/screenshot.js http://localhost:5174/models models.png 1920 1080

  # Full page capture
  node scripts/screenshot.js http://localhost:5174/dashboard --full-page

Common Pages:
  http://localhost:5174              - Login page
  http://localhost:5174/dashboard    - Admin dashboard
  http://localhost:5174/models       - Models list
  http://localhost:5174/models/1     - Model details
  http://localhost:5174/validations  - Validations list
  http://localhost:5174/vendors      - Vendors list
  http://localhost:5174/users        - Users list
  http://localhost:5174/taxonomy     - Taxonomy management
  http://localhost:5174/audit        - Audit logs
`);
    process.exit(0);
}

const url = args[0];
const fullPage = args.includes('--full-page');
const filteredArgs = args.filter(a => a !== '--full-page');

let outputFilename = filteredArgs[1];
const width = parseInt(filteredArgs[2]) || 1400;
const height = parseInt(filteredArgs[3]) || 900;

// Generate filename if not provided
if (!outputFilename) {
    outputFilename = generateFilename(url);
}

// Ensure .png extension
if (!outputFilename.endsWith('.png')) {
    outputFilename += '.png';
}

// Build full output path
const outputDir = getOutputDir();
const outputPath = path.isAbsolute(outputFilename)
    ? outputFilename
    : path.join(outputDir, outputFilename);

takeScreenshot(url, outputPath, { width, height, fullPage })
    .catch(err => {
        console.error('Screenshot failed:', err.message);
        process.exit(1);
    });
