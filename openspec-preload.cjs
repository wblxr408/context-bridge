// Use Node's strict JavaScript realpath implementation when managed Windows
// denies the native final-path handle. Both implementations resolve symlinks.
const fs = require('node:fs');
const native = fs.realpathSync.native;
fs.realpathSync.native = function(path, options) {
  try { return native(path, options); }
  catch (error) {
    if (!['EPERM', 'EACCES'].includes(error.code)) throw error;
    return fs.realpathSync(path, options);
  }
};
