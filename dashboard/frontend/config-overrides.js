const { override } = require('customize-cra');

module.exports = function override(config) {
  if (config.jest) {
    config.jest.transformIgnorePatterns = [
      'node_modules/(?!(axios|react-router-dom|@testing-library/react|@testing-library/user-event)/)',
    ];
  }
  return config;
};