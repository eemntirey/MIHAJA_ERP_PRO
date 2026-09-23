const path = require('path');

module.exports = {
  testDir: path.join(__dirname, 'e2e'),
  timeout: 60000,
  workers: 1,
  reporter: [['list']],
  use: {
    headless: true,
  },
};