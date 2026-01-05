const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const OUTPUT_DIR = path.join(__dirname, '..', 'screenshots', 'ux_audit');
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

const BASE_URL = 'http://localhost:5174';

async function runAudit() {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900 });

    console.log('Starting UX Audit...');

    // 1. Login
    console.log('Navigating to Login...');
    await page.goto(BASE_URL + '/login', { waitUntil: 'networkidle0' });

    if (await page.$('#email')) {
        console.log('Logging in...');
        await page.type('#email', 'admin@example.com');
        await page.type('#password', 'user123');
        await Promise.all([
            page.click('button[type="submit"]'),
            page.waitForNavigation({ waitUntil: 'networkidle0' })
        ]);
        console.log('Logged in successfully.');
    } else {
        console.log('Already logged in or no login form found.');
    }

    // Define routes to audit
    const routes = [
        { name: 'Dashboard', path: '/dashboard', selector: 'h1' },
        { name: 'Models List', path: '/models', selector: 'table' },
        { name: 'Validation Workflow', path: '/validation-workflow', selector: 'table' },
    ];

    for (const route of routes) {
        console.log(`Auditing ${route.name}...`);
        await page.goto(`${BASE_URL}${route.path}`, { waitUntil: 'networkidle0' });

        try {
            await page.waitForSelector(route.selector, { timeout: 5000 });
        } catch (e) {
            console.log(`Timeout waiting for selector ${route.selector} on ${route.name}`);
        }

        // A. Visual Density Check (Screenshot)
        const screenshotPath = path.join(OUTPUT_DIR, `${route.name.replace(/\s+/g, '_')}.png`);
        await page.screenshot({ path: screenshotPath });
        console.log(`Screenshot saved to ${screenshotPath}`);

        // C. Interaction Trace (Logic)
        if (route.name === 'Models List') {
            // Check for rows
            const rows = await page.$$('tbody tr');
            console.log(`Found ${rows.length} models in the list.`);

            if (rows.length > 0) {
                console.log('Clicking first model row for interaction trace...');
                // Assuming the row or a link inside it is clickable. 
                // Let's try clicking the first link in the first row if available, or the row itself.
                const firstLink = await rows[0].$('a');
                const clickTarget = firstLink || rows[0];

                const start = Date.now();
                await Promise.all([
                    clickTarget.click(),
                    page.waitForNavigation({ waitUntil: 'networkidle0' }).catch(e => console.log('Navigation timeout or no nav'))
                ]);
                const duration = Date.now() - start;
                console.log(`Interaction took ${duration}ms`);

                await page.screenshot({ path: path.join(OUTPUT_DIR, 'Model_Details_Interaction.png') });
                console.log('Saved interaction screenshot.');
            }
        }
    }

    await browser.close();
    console.log('Audit complete.');
}

runAudit().catch(console.error);
