module.exports = class PunkRecordsPlugin {
  constructor(app, manifest) {
    this.app = app;
    this.manifest = manifest;
  }

  async onload() {
    console.log('Loading PunkRecords plugin');
    // Add ribbon icon, commands, etc.
  }

  async onunload() {
    console.log('Unloading PunkRecords plugin');
  }
}
