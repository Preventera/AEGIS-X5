const fs = require('fs');
let c = fs.readFileSync('aegis-x5-deploy/index.html', 'utf8');
// Fix the apostrophe in CSS content property that breaks HTML parsing
c = c.replace(".int-card-link .int-card::after{content:'↗'", ".int-card-link .int-card::after{content:\"↗\"");
fs.writeFileSync('aegis-x5-deploy/index.html', c, 'utf8');
console.log('Fixed:', c.includes('content:"↗"'));
