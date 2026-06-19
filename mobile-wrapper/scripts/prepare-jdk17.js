const fs = require('fs');
const path = require('path');

const files = [
  path.join(__dirname, '..', 'android', 'app', 'capacitor.build.gradle'),
  path.join(__dirname, '..', 'node_modules', '@capacitor', 'android', 'capacitor', 'build.gradle'),
  path.join(__dirname, '..', 'node_modules', '@capacitor', 'app', 'android', 'build.gradle'),
  path.join(__dirname, '..', 'node_modules', '@capacitor', 'share', 'android', 'build.gradle'),
  path.join(__dirname, '..', 'node_modules', '@capacitor', 'filesystem', 'android', 'build.gradle')
];

for (const filePath of files) {
  if (!fs.existsSync(filePath)) {
    continue;
  }

  const original = fs.readFileSync(filePath, 'utf8');
  const updated = original
    .replaceAll('JavaVersion.VERSION_21', 'JavaVersion.VERSION_17')
    .replaceAll('jvmToolchain(21)', 'jvmToolchain(17)');

  if (updated !== original) {
    fs.writeFileSync(filePath, updated, 'utf8');
  }
}

console.log('Java compatibility prepared for JDK 17.');