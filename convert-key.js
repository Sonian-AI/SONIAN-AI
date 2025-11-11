const bs58 = require('bs58');
const seed = 'hPgk1zc18igJAFurUyFced83SRUorCTE4AXKMb4iW2eV23Lw93peLqJ65Z4wujgrDH6rYm42zy3pbHYRNZHaBvP';
const array = Array.from(bs58.decode(seed));
console.log(JSON.stringify(array));